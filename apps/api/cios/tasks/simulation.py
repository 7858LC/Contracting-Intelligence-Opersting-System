"""Award simulation Celery task."""

import asyncio
import json
import re
import uuid
from datetime import UTC, datetime

import structlog

from cios.tasks import celery_app

log = structlog.get_logger(__name__)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=60, soft_time_limit=300)
def run_award_simulation(
    self,
    tenant_id: str,
    user_id: str,
    simulation_id: str,
    proposal_content: dict,
) -> dict:
    try:
        return asyncio.run(
            _run_simulation_async(tenant_id, user_id, simulation_id, proposal_content)
        )
    except Exception as exc:
        # Without this, max_retries was dead configuration: a single transient
        # failure (Claude timeout/rate limit, a malformed-JSON response) would
        # permanently fail the simulation with no retry, unlike e.g.
        # cios/tasks/research.py's equivalent task. _run_simulation_async's own
        # except block already marks the row "failed" with an error_message
        # before re-raising, so a retry re-enters cleanly from "failed".
        raise self.retry(exc=exc)


def _parse_claude_json(raw: str) -> dict:
    """Extract JSON from Claude's response, stripping markdown fences if present.

    Raises ValueError if no valid JSON object can be extracted. Previously
    this returned {"raw": text[:5000]} on failure, which downstream code
    read with .get(...) — every field silently came back None/empty, the
    simulation was marked "completed", and the actual raw Claude output was
    discarded entirely (never stored anywhere). Raising instead routes a
    parse failure through the same "failed" + error_message + retry path as
    any other simulation failure, and preserves what Claude actually said.
    """
    text = raw.strip()
    # Strip ```json ... ``` or ``` ... ``` fences
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        # Last resort: find first { ... } block
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                return json.loads(match.group(0))
            except (json.JSONDecodeError, ValueError):
                pass
    raise ValueError(
        f"Claude response was not valid JSON — simulation cannot be scored. "
        f"First 500 chars of raw response: {text[:500]!r}"
    )


async def _run_simulation_async(
    tenant_id: str,
    user_id: str,
    simulation_id: str,
    proposal_content: dict,
) -> dict:
    from sqlalchemy import select, text

    from cios.agents.award_simulator_agent import AwardSimulatorAgent
    from cios.agents.base import AgentContext
    from cios.core.database import async_session_factory
    from cios.models.award_simulation import AwardSimulation
    from cios.vector.tenant_store import TenantVectorStore

    # Three short-lived sessions, never one spanning the whole task — see
    # tasks/analysis.py for the full rationale and reproduction. Short
    # version: agent.run() below is a real Claude call, often minutes; an
    # AsyncSession holds its transaction open from its first statement until
    # commit, so wrapping that call in one session parks the Postgres
    # connection idle-in-transaction for the whole wait, which managed hosts
    # kill — surfacing as "connection is closed" on whatever commit comes
    # next, with no DB access in between to notice sooner. The old code also
    # depended on that same possibly-dead connection for its own error
    # path (`except: sim.status = "failed"; await db.commit()`), so a
    # connection death didn't just lose the result, it silently lost the
    # failure record too, since that commit would raise as well. The failure
    # path below now writes through its own fresh session.
    async with async_session_factory() as db:
        # award_simulations has FORCE ROW LEVEL SECURITY (migration 007) and
        # TenantMixin. app.current_tenant is normally set by
        # get_current_user's SET LOCAL on the request's session — this task
        # runs outside that request lifecycle on its own session, so without
        # this every query below silently returns zero rows (RLS, not a
        # real "not found") and the task exits early having written nothing.
        await db.execute(
            text("SELECT set_config('app.current_tenant', :tenant_id, false)"),
            {"tenant_id": tenant_id},
        )

        result = await db.execute(
            select(AwardSimulation).where(AwardSimulation.id == uuid.UUID(simulation_id))
        )
        sim = result.scalar_one_or_none()
        if not sim:
            log.error("simulation_not_found", id=simulation_id)
            return {"error": "simulation not found"}

        sim.status = "running"
        sim.started_at = datetime.now(UTC)

        from cios.models.opportunity import Opportunity

        opp_result = await db.execute(
            select(Opportunity).where(Opportunity.id == sim.opportunity_id)
        )
        opp = opp_result.scalar_one_or_none()
        opportunity_data = opp.to_dict() if opp else {}
        evaluation_factors = sim.evaluation_factors or []
        evaluation_methodology = sim.evaluation_methodology

        await db.commit()

    try:
        store = TenantVectorStore(tenant_id)
        try:
            knowledge_context = await store.search(
                query=opportunity_data.get("title", "procurement opportunity"),
                top_k=10,
            )
        except Exception:
            knowledge_context = []

        context = AgentContext(
            tenant_id=uuid.UUID(tenant_id),
            user_id=uuid.UUID(user_id),
            simulation_id=uuid.UUID(simulation_id),
            rule_pack=opportunity_data.get("procurement_rule_pack", "us_federal_far"),
        )

        agent = AwardSimulatorAgent()
        output = await agent.run(
            context,
            opportunity_data=opportunity_data,
            proposal_content=proposal_content,
            knowledge_context=knowledge_context,
            evaluation_factors=evaluation_factors,
            evaluation_methodology=evaluation_methodology,
        )

        raw_result = output.get("result", {})
        sim_data = raw_result.get("simulation", "{}")
        parsed = _parse_claude_json(sim_data) if isinstance(sim_data, str) else sim_data

        async with async_session_factory() as db:
            # A second session is a second physical connection (NullPool on
            # the worker, see core/database.py), so app.current_tenant does
            # NOT carry over from the read session above — it has to be set
            # again here or the re-select below returns zero rows under RLS.
            await db.execute(
                text("SELECT set_config('app.current_tenant', :tenant_id, false)"),
                {"tenant_id": tenant_id},
            )

            # Re-fetch rather than reusing the instance from the first
            # session: that one is detached now, and assigning to a
            # detached instance would commit nothing at all.
            result = await db.execute(
                select(AwardSimulation).where(AwardSimulation.id == uuid.UUID(simulation_id))
            )
            sim = result.scalar_one_or_none()
            if not sim:
                log.error("simulation_not_found_on_write", id=simulation_id)
                return {"error": "simulation not found"}

            sim.status = "completed"
            sim.completed_at = datetime.now(UTC)
            sim.technical_score = parsed.get("technical_score")
            sim.management_score = parsed.get("management_score")
            sim.past_performance_score = parsed.get("past_performance_score")
            sim.price_competitiveness_score = parsed.get("price_competitiveness_score")
            sim.compliance_score = parsed.get("compliance_score")
            sim.risk_score = parsed.get("risk_score")
            sim.overall_score = parsed.get("overall_score")
            sim.award_probability = parsed.get("award_probability")
            sim.confidence_score = parsed.get("confidence_score")
            sim.strengths = parsed.get("strengths", [])
            sim.weaknesses = parsed.get("weaknesses", [])
            sim.significant_weaknesses = parsed.get("significant_weaknesses", [])
            sim.deficiencies = parsed.get("deficiencies", [])
            sim.risks = parsed.get("risks", [])
            sim.red_team_comments = parsed.get("red_team_comments", [])
            sim.suggested_improvements = parsed.get("suggested_improvements", [])
            sim.executive_summary = parsed.get("executive_summary")
            sim.gate_review_recommendation = parsed.get("gate_review_recommendation")
            sim.rule_citations = parsed.get("rule_citations", [])
            sim.evidence = {
                "factor_ratings": parsed.get("factor_ratings", {}),
                "agent_run_id": output.get("run_id"),
                "duration_ms": output.get("duration_ms"),
            }
            sim.ai_model_version = agent.model

            await db.commit()
            log.info("simulation_complete", id=simulation_id)
            return {"simulation_id": simulation_id, "status": "completed"}

    except Exception as e:
        log.error("simulation_failed", id=simulation_id, error=str(e))
        # Deliberately a brand-new session, not the one the try block was
        # using — if that one is what died (idle-in-transaction reaped
        # mid-Claude-call), reusing it here would just raise a second time
        # and lose the failure record along with the result.
        async with async_session_factory() as db:
            await db.execute(
                text("SELECT set_config('app.current_tenant', :tenant_id, false)"),
                {"tenant_id": tenant_id},
            )
            result = await db.execute(
                select(AwardSimulation).where(AwardSimulation.id == uuid.UUID(simulation_id))
            )
            sim = result.scalar_one_or_none()
            if sim:
                sim.status = "failed"
                sim.error_message = str(e)[:1000]
                await db.commit()
        raise
