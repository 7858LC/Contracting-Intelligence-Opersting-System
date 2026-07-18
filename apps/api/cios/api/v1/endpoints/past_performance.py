"""Past Performance Intelligence API — Module 6."""
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from cios.core.dependencies import Auth, DB
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


@router.get("")
async def list_past_performance(db: DB, user: Auth) -> dict:
    result = await db.execute(
        select(PastPerformance)
        .where(PastPerformance.tenant_id == user.tenant_id)
        .order_by(PastPerformance.relevance_score.desc().nullslast(), PastPerformance.created_at.desc())
    )
    return {"items": [i.to_dict() for i in result.scalars().all()]}


@router.post("")
async def create_past_performance(body: PastPerformanceCreate, db: DB, user: Auth) -> dict:
    pp = PastPerformance(tenant_id=user.tenant_id, **body.model_dump())
    db.add(pp)
    await db.flush()
    await db.refresh(pp)
    from cios.tasks.ingestion import vectorize_past_performance
    vectorize_past_performance.delay(str(user.tenant_id), str(pp.id))
    return pp.to_dict()


@router.get("/{pp_id}/relevance")
async def assess_relevance(pp_id: uuid.UUID, opportunity_id: uuid.UUID, db: DB, user: Auth) -> dict:
    """AI-score past performance relevance for a specific opportunity."""
    from cios.tasks.scoring import score_pp_relevance
    task = score_pp_relevance.delay(
        str(user.tenant_id), str(pp_id), str(opportunity_id)
    )
    return {"task_id": task.id, "status": "queued"}
