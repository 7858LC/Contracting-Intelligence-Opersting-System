"""Full opportunity analysis task — orchestrates CEO Agent pipeline."""

import asyncio
import uuid

from cios.tasks import celery_app

_VALID_RECOMMENDATIONS = {"BID", "NO_BID", "CONDITIONAL_BID"}


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30, soft_time_limit=600)
def run_opportunity_analysis(self, tenant_id: str, user_id: str, opportunity_id: str) -> dict:
    try:
        return asyncio.run(_run_async(tenant_id, user_id, opportunity_id))
    except Exception as exc:
        # max_retries was declared but nothing ever called self.retry() — see
        # bid_analysis.py's identical fix. A transient failure (or a JSON
        # parse failure below) used to just complete silently with every
        # score left blank instead of actually retrying.
        raise self.retry(exc=exc)


async def _run_async(tenant_id: str, user_id: str, opportunity_id: str) -> dict:
    from datetime import UTC, datetime

    from sqlalchemy import select, text

    from cios.agents.base import AgentContext
    from cios.agents.ceo_agent import CEOAgent
    from cios.core.database import async_session_factory
    from cios.models.opportunity import Opportunity
    from cios.vector.tenant_store import TenantVectorStore

    # This task deliberately uses TWO short-lived sessions with the slow work
    # sandwiched between them, rather than one session wrapping everything.
    # orchestrate_full_assessment below is minutes of pure external HTTP to
    # the Anthropic API with zero DB activity in between (see agents/base.py's
    # _call_claude — no agent on this path touches the database at all). An
    # AsyncSession autobegins a transaction on its first statement and holds
    # it open until commit, so keeping one session across that call parks the
    # Postgres connection in state='idle in transaction' for the entire
    # orchestration. Managed Postgres hosts kill those, and the Python side
    # never learns the socket died — the failure surfaces minutes later, on
    # the deferred UPDATE at the very end, as
    # "asyncpg InterfaceError: connection is closed", losing the whole
    # analysis after paying for every Claude call. That is the exact error
    # this task failed with in production, and it is reproducible against the
    # real engine by setting a server-side idle_in_transaction_session_timeout
    # and holding the session open past it. Parallelizing the Directors
    # shortened the idle window but could never close it; only not holding a
    # connection across the call does.
    async with async_session_factory() as db:
        # opportunities has FORCE ROW LEVEL SECURITY (migration 007).
        # app.current_tenant is normally set by get_current_user's SET LOCAL
        # on the request's session — this task runs outside that request
        # lifecycle on its own session, so without this the query below
        # silently returns zero rows (RLS, not a real "not found") and the
        # task exits early having written nothing. See bid_analysis.py.
        await db.execute(
            text("SELECT set_config('app.current_tenant', :tenant_id, false)"),
            {"tenant_id": tenant_id},
        )

        result = await db.execute(
            select(Opportunity).where(Opportunity.id == uuid.UUID(opportunity_id))
        )
        opp = result.scalar_one_or_none()
        if not opp:
            return {"error": "opportunity not found"}

        # Snapshot every field the orchestration needs while the row is still
        # attached, so nothing below this block touches a live session.
        opportunity_data = opp.to_dict()

    store = TenantVectorStore(tenant_id)
    try:
        knowledge_context = await store.search(
            query=f"{opportunity_data.get('title', '')} {opportunity_data.get('agency', '')}",
            top_k=15,
        )
    except Exception:
        knowledge_context = []

    context = AgentContext(
        tenant_id=uuid.UUID(tenant_id),
        user_id=uuid.UUID(user_id),
        opportunity_id=uuid.UUID(opportunity_id),
        rule_pack=opportunity_data.get("procurement_rule_pack", "us_federal_far"),
    )

    ceo = CEOAgent()
    output = await ceo.orchestrate_full_assessment(context, opportunity_data, knowledge_context)

    synthesis = output.get("synthesis", {})
    result_data = synthesis.get("result", {})

    from cios.agents.json_parsing import extract_claude_json

    # require_any_of: a response that parses as JSON but matches none of
    # the schema keys must FAIL (and retry via self.retry() in the task
    # wrapper above) rather than sail through — every .get() below would
    # return None, and the row would commit as "analyzed" with every
    # score and the recommendation silently null. See bid_analysis.py,
    # which shipped that exact all-null-but-analyzed row once already.
    # Parsing happens before the write session is opened so a parse failure
    # raises without a connection checked out.
    parsed = extract_claude_json(
        result_data.get("executive_summary", "") or "",
        context="Opportunity analysis (CEO synthesis)",
        require_any_of=frozenset(
            {
                "gate_review_recommendation",
                "award_probability",
                "confidence_score",
                "strategic_recommendation",
            }
        ),
    )

    # Same shape guard as bid_analysis.py's recommendation handling —
    # only ever accept one of the three known values; anything else
    # becomes None rather than corrupting a column the frontend treats
    # as a closed enum for color/label lookups.
    recommendation = parsed.get("gate_review_recommendation")
    if isinstance(recommendation, str):
        normalized = recommendation.strip().upper().replace(" ", "_").replace("-", "_")
        recommendation = normalized if normalized in _VALID_RECOMMENDATIONS else None
    else:
        recommendation = None

    async with async_session_factory() as db:
        # A second session is a second physical connection (NullPool on the
        # worker, see core/database.py), so app.current_tenant does NOT carry
        # over from the read session above — it has to be set again here or
        # the re-select below returns zero rows under RLS and the task
        # reports success having written nothing.
        await db.execute(
            text("SELECT set_config('app.current_tenant', :tenant_id, false)"),
            {"tenant_id": tenant_id},
        )

        # Re-fetch rather than reusing the instance from the read session:
        # that one is detached now, and assigning to a detached instance
        # would commit nothing at all.
        result = await db.execute(
            select(Opportunity).where(Opportunity.id == uuid.UUID(opportunity_id))
        )
        opp = result.scalar_one_or_none()
        if not opp:
            return {"error": "opportunity not found"}

        opp.award_probability_score = parsed.get("award_probability")
        opp.bid_no_bid_recommendation = recommendation
        opp.evidence = {"ceo_synthesis": str(result_data)[:3000]}
        opp.confidence_score = parsed.get("confidence_score")
        opp.ai_model_version = CEOAgent.model
        opp.analyzed_at = datetime.now(UTC)

        await db.commit()
        return {"opportunity_id": opportunity_id, "status": "completed"}
