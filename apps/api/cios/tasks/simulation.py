"""Award simulation Celery task."""
import asyncio
import json
import uuid
from datetime import UTC, datetime

import structlog

from cios.tasks import celery_app

log = structlog.get_logger(__name__)


@celery_app.task(bind=True, max_retries=2, soft_time_limit=300)
def run_award_simulation(
    self,
    tenant_id: str,
    user_id: str,
    simulation_id: str,
    proposal_content: dict,
) -> dict:
    return asyncio.get_event_loop().run_until_complete(
        _run_simulation_async(tenant_id, user_id, simulation_id, proposal_content)
    )


async def _run_simulation_async(
    tenant_id: str,
    user_id: str,
    simulation_id: str,
    proposal_content: dict,
) -> dict:
    from cios.core.database import async_session_factory
    from cios.agents.award_simulator_agent import AwardSimulatorAgent
    from cios.agents.base import AgentContext
    from cios.models.award_simulation import AwardSimulation
    from cios.vector.tenant_store import TenantVectorStore
    from sqlalchemy import select

    async with async_session_factory() as db:
        result = await db.execute(
            select(AwardSimulation).where(AwardSimulation.id == uuid.UUID(simulation_id))
        )
        sim = result.scalar_one_or_none()
        if not sim:
            log.error("simulation_not_found", id=simulation_id)
            return {"error": "simulation not found"}

        sim.status = "running"
        sim.started_at = datetime.now(UTC)
        await db.commit()

        from cios.models.opportunity import Opportunity
        opp_result = await db.execute(
            select(Opportunity).where(Opportunity.id == sim.opportunity_id)
        )
        opp = opp_result.scalar_one_or_none()
        opportunity_data = opp.to_dict() if opp else {}

        store = TenantVectorStore(tenant_id)
        try:
            knowledge_context = await store.search(
                query=opportunity_data.get("title", ""),
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
        try:
            output = await agent.run(
                context,
                opportunity_data=opportunity_data,
                proposal_content=proposal_content,
                knowledge_context=knowledge_context,
                evaluation_factors=sim.evaluation_factors,
                evaluation_methodology=sim.evaluation_methodology,
            )

            raw_result = output.get("result", {})
            sim_data = raw_result.get("simulation", "{}")

            try:
                parsed = json.loads(sim_data) if isinstance(sim_data, str) else sim_data
            except (json.JSONDecodeError, TypeError):
                parsed = {"raw": str(sim_data)[:5000]}

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
            sim.significant_weaknesses = parsed.get("significant_weaknesses", [])
            sim.deficiencies = parsed.get("deficiencies", [])
            sim.strengths = parsed.get("strengths", [])
            sim.risks = parsed.get("risks", [])
            sim.red_team_comments = parsed.get("red_team_comments", [])
            sim.suggested_improvements = parsed.get("suggested_improvements", [])
            sim.executive_summary = parsed.get("executive_summary")
            sim.gate_review_recommendation = parsed.get("gate_review_recommendation")
            sim.rule_citations = parsed.get("rule_citations", [])
            sim.evidence = {"raw_output": str(raw_result)[:2000]}
            sim.confidence_score = parsed.get("confidence_score")
            sim.ai_model_version = agent.model

            await db.commit()
            log.info("simulation_complete", id=simulation_id)
            return {"simulation_id": simulation_id, "status": "completed"}

        except Exception as e:
            sim.status = "failed"
            sim.error_message = str(e)[:1000]
            await db.commit()
            log.error("simulation_failed", id=simulation_id, error=str(e))
            raise
