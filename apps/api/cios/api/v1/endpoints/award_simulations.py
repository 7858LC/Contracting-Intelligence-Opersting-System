"""Award Simulator API — Module 13, flagship feature."""
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from cios.core.dependencies import Auth, DB
from cios.models.award_simulation import AwardSimulation

router = APIRouter()


class SimulationCreate(BaseModel):
    opportunity_id: uuid.UUID
    name: str = Field(..., min_length=1, max_length=256)
    evaluation_methodology: str = "BEST_VALUE_TRADEOFF"
    evaluation_factors: list[dict] = []
    proposal_content: dict[str, str] = {}


class SimulationResponse(BaseModel):
    id: uuid.UUID
    opportunity_id: uuid.UUID
    name: str
    status: str
    evaluation_methodology: str

    # Scores
    technical_score: float | None = None
    management_score: float | None = None
    past_performance_score: float | None = None
    price_competitiveness_score: float | None = None
    compliance_score: float | None = None
    risk_score: float | None = None
    overall_score: float | None = None
    award_probability: float | None = None
    confidence_score: float | None = None

    # Findings
    strengths: list = []
    weaknesses: list = []
    significant_weaknesses: list = []
    deficiencies: list = []
    risks: list = []
    red_team_comments: list = []
    suggested_improvements: list = []

    # Narrative
    executive_summary: str | None = None
    gate_review_recommendation: str | None = None
    rule_citations: list = []

    # Evidence (includes factor_ratings)
    evidence: dict | None = None

    # Lifecycle
    created_at: Any = None
    started_at: Any = None
    completed_at: Any = None
    error_message: str | None = None

    model_config = {"from_attributes": True}


@router.get("", response_model=dict[str, Any])
async def list_simulations(db: DB, user: Auth) -> dict[str, Any]:
    result = await db.execute(
        select(AwardSimulation)
        .where(AwardSimulation.tenant_id == user.tenant_id)
        .order_by(AwardSimulation.created_at.desc())
        .limit(50)
    )
    items = result.scalars().all()
    return {"items": [SimulationResponse.model_validate(i).model_dump() for i in items]}


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def create_simulation(body: SimulationCreate, db: DB, user: Auth) -> dict[str, Any]:
    """Launch a new award simulation. Processing is async — poll status endpoint."""
    sim = AwardSimulation(
        tenant_id=user.tenant_id,
        opportunity_id=body.opportunity_id,
        name=body.name,
        evaluation_methodology=body.evaluation_methodology,
        evaluation_factors=body.evaluation_factors,
        status="queued",
    )
    db.add(sim)
    await db.flush()

    from cios.tasks.simulation import run_award_simulation
    task = run_award_simulation.delay(
        str(user.tenant_id),
        str(user.user_id),
        str(sim.id),
        body.proposal_content,
    )

    return {
        "simulation_id": str(sim.id),
        "task_id": task.id,
        "status": "queued",
        "message": "Award simulation queued. Results available via GET /award-simulations/{id}",
    }


@router.get("/{sim_id}", response_model=SimulationResponse)
async def get_simulation(sim_id: uuid.UUID, db: DB, user: Auth) -> AwardSimulation:
    result = await db.execute(
        select(AwardSimulation).where(
            AwardSimulation.id == sim_id,
            AwardSimulation.tenant_id == user.tenant_id,
        )
    )
    sim = result.scalar_one_or_none()
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return sim


@router.get("/{sim_id}/report")
async def get_simulation_report(sim_id: uuid.UUID, db: DB, user: Auth) -> dict[str, Any]:
    """Full structured report suitable for executive review."""
    result = await db.execute(
        select(AwardSimulation).where(
            AwardSimulation.id == sim_id,
            AwardSimulation.tenant_id == user.tenant_id,
        )
    )
    sim = result.scalar_one_or_none()
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
    if sim.status != "completed":
        raise HTTPException(status_code=409, detail=f"Simulation is {sim.status}")

    factor_ratings = (sim.evidence or {}).get("factor_ratings", {})

    return {
        "simulation_id": str(sim.id),
        "name": sim.name,
        "evaluation_methodology": sim.evaluation_methodology,
        "scores": {
            "technical": sim.technical_score,
            "management": sim.management_score,
            "past_performance": sim.past_performance_score,
            "price_competitiveness": sim.price_competitiveness_score,
            "compliance": sim.compliance_score,
            "risk": sim.risk_score,
            "overall": sim.overall_score,
        },
        "factor_ratings": factor_ratings,
        "award_probability": sim.award_probability,
        "confidence_score": sim.confidence_score,
        "gate_review": sim.gate_review_recommendation,
        "executive_summary": sim.executive_summary,
        "strengths": sim.strengths,
        "weaknesses": sim.weaknesses,
        "significant_weaknesses": sim.significant_weaknesses,
        "deficiencies": sim.deficiencies,
        "risks": sim.risks,
        "red_team_comments": sim.red_team_comments,
        "suggested_improvements": sim.suggested_improvements,
        "rule_citations": sim.rule_citations,
        "evidence": sim.evidence,
        "ai_model_version": sim.ai_model_version,
        "completed_at": sim.completed_at.isoformat() if sim.completed_at else None,
    }
