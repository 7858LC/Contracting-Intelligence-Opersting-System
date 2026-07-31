"""Bid/No-Bid Engine API — Module 2."""

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from cios.core.dependencies import DB, Auth
from cios.models.bid_decision import BidDecision
from cios.models.opportunity import Opportunity

router = APIRouter()


class BidDecisionCreate(BaseModel):
    opportunity_id: uuid.UUID
    go_no_go_threshold: float = 65.0
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


def _serialize(d: BidDecision, opportunity_title: str | None) -> dict[str, Any]:
    """Maps this model's internal column names to the frontend's contract
    (components/modules/bid-decision/bid-decision-view.tsx) — those names
    (recommendation, composite_score, capability_match_score, risks,
    recommendation_rationale) diverged from the frontend after a rename that
    never got a matching migration or frontend update; restoring the API
    shape here avoids re-litigating which side is "right"."""
    return {
        "id": str(d.id),
        "opportunity_id": str(d.opportunity_id),
        "opportunity_title": opportunity_title,
        "decision": d.human_decision or d.recommendation,
        "overall_score": d.composite_score,
        "strategic_fit_score": d.strategic_fit_score,
        "win_probability_score": d.win_probability_score,
        "past_performance_score": d.past_performance_score,
        "capability_score": d.capability_match_score,
        "competitive_position_score": d.competitive_position_score,
        "cost_of_bid_score": d.cost_of_bid_score,
        "risk_score": d.risk_score,
        "relationship_score": d.relationship_score,
        "go_no_go_threshold": d.go_no_go_threshold,
        "rationale": d.recommendation_rationale,
        "risk_factors": d.risks,
        "created_at": d.created_at.isoformat() if d.created_at else None,
        "analyzed_at": d.analyzed_at.isoformat() if d.analyzed_at else None,
    }


@router.get("", response_model=dict[str, Any])
async def list_bid_decisions(db: DB, user: Auth) -> dict[str, Any]:
    result = await db.execute(
        select(BidDecision, Opportunity.title)
        .outerjoin(Opportunity, Opportunity.id == BidDecision.opportunity_id)
        .where(
            BidDecision.tenant_id == user.tenant_id,
            BidDecision.is_archived == False,  # noqa: E712
        )
        .order_by(BidDecision.created_at.desc())
        .limit(100)
    )
    rows = result.all()
    return {"items": [_serialize(d, title) for d, title in rows], "total": len(rows)}


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def create_bid_decision(body: BidDecisionCreate, db: DB, user: Auth) -> dict:
    """Trigger AI bid/no-bid analysis."""
    decision = BidDecision(
        tenant_id=user.tenant_id,
        opportunity_id=body.opportunity_id,
        created_by=user.user_id,
        scoring_weights=body.scoring_weights,
        go_no_go_threshold=body.go_no_go_threshold,
    )
    db.add(decision)
    await db.flush()

    from cios.tasks.bid_analysis import run_bid_analysis

    task = run_bid_analysis.delay(str(user.tenant_id), str(user.user_id), str(decision.id))
    return {"decision_id": str(decision.id), "task_id": task.id, "status": "queued"}


@router.get("/{decision_id}")
async def get_bid_decision(decision_id: uuid.UUID, db: DB, user: Auth) -> dict:
    decision = await _get_decision(db, user.tenant_id, decision_id)
    opp = await db.execute(
        select(Opportunity.title).where(Opportunity.id == decision.opportunity_id)
    )
    return _serialize(decision, opp.scalar_one_or_none())


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


@router.delete("/{decision_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bid_decision(decision_id: uuid.UUID, db: DB, user: Auth) -> None:
    """Soft-delete — sets is_archived rather than removing the row, so this
    stays recoverable directly from the database. Excluded from
    list_bid_decisions immediately either way."""
    decision = await _get_decision(db, user.tenant_id, decision_id)
    decision.is_archived = True


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
