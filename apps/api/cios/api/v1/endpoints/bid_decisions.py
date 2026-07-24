"""Bid/No-Bid Engine API — Module 2."""

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from cios.core.dependencies import DB, Auth
from cios.models.bid_decision import BidDecision

router = APIRouter()


class BidDecisionCreate(BaseModel):
    opportunity_id: uuid.UUID
    scoring_weights: dict[str, float] = {
        "strategic_fit": 0.20,
        "win_probability": 0.20,
        "past_performance": 0.15,
        "capability_match": 0.15,
        "competitive_position": 0.10,
        "cost_of_bid": 0.10,
        "risk": 0.05,
        "relationship": 0.05,
    }


class HumanDecisionUpdate(BaseModel):
    human_decision: str
    human_rationale: str


@router.get("", response_model=dict[str, Any])
async def list_bid_decisions(db: DB, user: Auth) -> dict[str, Any]:
    result = await db.execute(
        select(BidDecision)
        .where(BidDecision.tenant_id == user.tenant_id)
        .order_by(BidDecision.created_at.desc())
        .limit(100)
    )
    items = result.scalars().all()
    return {"items": [i.to_dict() for i in items], "total": len(items)}


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def create_bid_decision(body: BidDecisionCreate, db: DB, user: Auth) -> dict:
    """Trigger AI bid/no-bid analysis."""
    decision = BidDecision(
        tenant_id=user.tenant_id,
        opportunity_id=body.opportunity_id,
        created_by=user.user_id,
        scoring_weights=body.scoring_weights,
    )
    db.add(decision)
    await db.flush()

    from cios.tasks.bid_analysis import run_bid_analysis

    task = run_bid_analysis.delay(str(user.tenant_id), str(user.user_id), str(decision.id))
    return {"decision_id": str(decision.id), "task_id": task.id, "status": "queued"}


@router.get("/{decision_id}")
async def get_bid_decision(decision_id: uuid.UUID, db: DB, user: Auth) -> dict:
    decision = await _get_decision(db, user.tenant_id, decision_id)
    return decision.to_dict()


@router.patch("/{decision_id}/human-decision")
async def record_human_decision(
    decision_id: uuid.UUID, body: HumanDecisionUpdate, db: DB, user: Auth
) -> dict:
    """Record the human decision override (audit trail)."""
    decision = await _get_decision(db, user.tenant_id, decision_id)
    decision.human_decision = body.human_decision
    decision.human_rationale = body.human_rationale
    decision.decided_by = user.user_id
    return {"status": "recorded", "decision_id": str(decision.id)}


async def _get_decision(db: Any, tenant_id: uuid.UUID, decision_id: uuid.UUID) -> BidDecision:
    result = await db.execute(
        select(BidDecision).where(
            BidDecision.id == decision_id,
            BidDecision.tenant_id == tenant_id,
        )
    )
    d = result.scalar_one_or_none()
    if not d:
        raise HTTPException(status_code=404, detail="Bid decision not found")
    return d
