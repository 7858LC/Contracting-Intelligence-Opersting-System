"""Past Performance Intelligence API — Module 6."""

import uuid
from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from cios.core.dependencies import DB, Auth
from cios.models.past_performance import PastPerformance

router = APIRouter()


class PastPerformanceCreate(BaseModel):
    contract_title: str
    customer_name: str
    customer_agency: str | None = None
    contract_number: str | None = None
    contract_type: str | None = None
    contract_value: float | None = None
    period_start: str | None = None
    period_end: str | None = None
    scope_of_work: str | None = None
    key_accomplishments: list[str] = []
    outcomes: list[dict] = []
    cpars_rating: str | None = None
    prime_or_sub: str = "prime"
    naics_codes: list[str] = []
    poc_name: str | None = None
    poc_email: str | None = None


class PastPerformanceResponse(BaseModel):
    id: uuid.UUID
    contract_number: str | None
    contract_title: str
    customer_name: str
    customer_agency: str | None
    contract_type: str | None
    contract_value: float | None
    currency: str
    period_start: str | None
    period_end: str | None
    scope_of_work: str | None
    key_accomplishments: list
    challenges_overcome: list
    outcomes: list
    metrics: list
    relevance_score: float | None
    relevance_factors: list
    naics_codes: list
    psc_codes: list
    cpars_rating: str | None
    quality_rating: float | None
    schedule_rating: float | None
    cost_rating: float | None
    management_rating: float | None
    poc_name: str | None
    poc_email: str | None
    poc_phone: str | None
    prime_or_sub: str
    teaming_partners: list
    is_verified: bool
    is_confidential: bool
    evidence: dict | None
    confidence_score: float | None
    ai_model_version: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PastPerformanceListResponse(BaseModel):
    items: list[PastPerformanceResponse]


class RelevanceQueuedResponse(BaseModel):
    task_id: str
    status: str


@router.get("", response_model=PastPerformanceListResponse)
async def list_past_performance(db: DB, user: Auth) -> dict:
    result = await db.execute(
        select(PastPerformance)
        .where(PastPerformance.tenant_id == user.tenant_id)
        .order_by(
            PastPerformance.relevance_score.desc().nullslast(), PastPerformance.created_at.desc()
        )
    )
    return {"items": result.scalars().all()}


@router.post("", response_model=PastPerformanceResponse)
async def create_past_performance(
    body: PastPerformanceCreate, db: DB, user: Auth
) -> PastPerformance:
    pp = PastPerformance(tenant_id=user.tenant_id, **body.model_dump())
    db.add(pp)
    await db.flush()
    await db.refresh(pp)
    from cios.tasks.ingestion import vectorize_past_performance

    vectorize_past_performance.delay(str(user.tenant_id), str(pp.id))
    return pp


@router.get("/{pp_id}/relevance", response_model=RelevanceQueuedResponse)
async def assess_relevance(pp_id: uuid.UUID, opportunity_id: uuid.UUID, db: DB, user: Auth) -> dict:
    """AI-score past performance relevance for a specific opportunity."""
    from cios.tasks.scoring import score_pp_relevance

    task = score_pp_relevance.delay(str(user.tenant_id), str(pp_id), str(opportunity_id))
    return {"task_id": task.id, "status": "queued"}
