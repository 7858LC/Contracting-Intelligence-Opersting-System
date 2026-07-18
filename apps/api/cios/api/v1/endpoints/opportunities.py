"""Opportunity Intelligence API — Module 1."""
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func, or_

from cios.core.dependencies import Auth, DB, Pages
from cios.models.opportunity import Opportunity, OpportunityNote, OpportunityWatch

router = APIRouter()


class OpportunityCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=512)
    source: str = "manual"
    source_url: str | None = None
    solicitation_number: str | None = None
    agency: str | None = None
    sub_agency: str | None = None
    description: str | None = None
    jurisdiction: str = "federal"
    naics_codes: list[str] = []
    set_aside_type: str | None = None
    solicitation_type: str | None = None
    contract_type: str | None = None
    estimated_value_min: float | None = None
    estimated_value_max: float | None = None
    response_deadline: str | None = None
    evaluation_criteria: list[dict] = []
    key_requirements: list[dict] = []
    incumbent: str | None = None
    procurement_rule_pack: str = "us_federal_far"


class OpportunityUpdate(BaseModel):
    pipeline_stage: str | None = None
    status: str | None = None
    title: str | None = None
    description: str | None = None


class OpportunityResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    title: str
    agency: str | None
    solicitation_number: str | None
    jurisdiction: str
    status: str
    pipeline_stage: str
    award_probability_score: float | None
    bid_no_bid_recommendation: str | None
    proposal_readiness_score: float | None
    estimated_value_max: float | None
    response_deadline: str | None
    naics_codes: list
    set_aside_type: str | None
    incumbent: str | None
    source: str
    created_at: str

    model_config = {"from_attributes": True}


@router.get("", response_model=dict[str, Any])
async def list_opportunities(
    db: DB,
    user: Auth,
    pages: Pages,
    status: str | None = Query(None),
    pipeline_stage: str | None = Query(None),
    search: str | None = Query(None),
    jurisdiction: str | None = Query(None),
    min_value: float | None = Query(None),
    max_value: float | None = Query(None),
    sort_by: str = Query("created_at"),
    sort_dir: str = Query("desc"),
) -> dict[str, Any]:
    query = select(Opportunity).where(
        Opportunity.tenant_id == user.tenant_id,
        Opportunity.is_archived == False,  # noqa: E712
    )

    if status:
        query = query.where(Opportunity.status == status)
    if pipeline_stage:
        query = query.where(Opportunity.pipeline_stage == pipeline_stage)
    if jurisdiction:
        query = query.where(Opportunity.jurisdiction == jurisdiction)
    if min_value:
        query = query.where(Opportunity.estimated_value_max >= min_value)
    if max_value:
        query = query.where(Opportunity.estimated_value_max <= max_value)
    if search:
        query = query.where(
            or_(
                Opportunity.title.ilike(f"%{search}%"),
                Opportunity.agency.ilike(f"%{search}%"),
                Opportunity.solicitation_number.ilike(f"%{search}%"),
            )
        )

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    sort_col = getattr(Opportunity, sort_by, Opportunity.created_at)
    if sort_dir == "desc":
        query = query.order_by(sort_col.desc())
    else:
        query = query.order_by(sort_col.asc())

    query = query.offset(pages.offset).limit(pages.limit)
    items = (await db.execute(query)).scalars().all()

    return {
        "items": [OpportunityResponse.model_validate(item).model_dump() for item in items],
        "total": total,
        "page": pages.page,
        "page_size": pages.page_size,
        "pages": -(-total // pages.page_size),
    }


@router.post("", response_model=OpportunityResponse, status_code=status.HTTP_201_CREATED)
async def create_opportunity(body: OpportunityCreate, db: DB, user: Auth) -> Opportunity:
    opp = Opportunity(
        tenant_id=user.tenant_id,
        **body.model_dump(),
    )
    db.add(opp)
    await db.flush()
    await db.refresh(opp)
    return opp


@router.get("/{opportunity_id}", response_model=OpportunityResponse)
async def get_opportunity(opportunity_id: uuid.UUID, db: DB, user: Auth) -> Opportunity:
    opp = await _get_opp(db, user.tenant_id, opportunity_id)
    return opp


@router.patch("/{opportunity_id}", response_model=OpportunityResponse)
async def update_opportunity(
    opportunity_id: uuid.UUID, body: OpportunityUpdate, db: DB, user: Auth
) -> Opportunity:
    opp = await _get_opp(db, user.tenant_id, opportunity_id)
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(opp, k, v)
    await db.flush()
    await db.refresh(opp)
    return opp


@router.delete("/{opportunity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_opportunity(opportunity_id: uuid.UUID, db: DB, user: Auth) -> None:
    opp = await _get_opp(db, user.tenant_id, opportunity_id)
    opp.is_archived = True


@router.post("/{opportunity_id}/analyze", status_code=status.HTTP_202_ACCEPTED)
async def trigger_opportunity_analysis(
    opportunity_id: uuid.UUID, db: DB, user: Auth
) -> dict[str, str]:
    """Trigger full AI capture assessment for an opportunity."""
    opp = await _get_opp(db, user.tenant_id, opportunity_id)
    from cios.tasks.analysis import run_opportunity_analysis
    task = run_opportunity_analysis.delay(
        str(user.tenant_id), str(user.user_id), str(opportunity_id)
    )
    return {"task_id": task.id, "status": "queued", "opportunity_id": str(opportunity_id)}


@router.post("/{opportunity_id}/watch")
async def watch_opportunity(opportunity_id: uuid.UUID, db: DB, user: Auth) -> dict:
    opp = await _get_opp(db, user.tenant_id, opportunity_id)
    watch = OpportunityWatch(
        tenant_id=user.tenant_id,
        opportunity_id=opportunity_id,
        user_id=user.user_id,
    )
    db.add(watch)
    return {"watched": True, "opportunity_id": str(opportunity_id)}


@router.post("/{opportunity_id}/notes")
async def add_note(
    opportunity_id: uuid.UUID,
    body: dict[str, str],
    db: DB,
    user: Auth,
) -> dict:
    await _get_opp(db, user.tenant_id, opportunity_id)
    note = OpportunityNote(
        tenant_id=user.tenant_id,
        opportunity_id=opportunity_id,
        user_id=user.user_id,
        content=body.get("content", ""),
        note_type=body.get("note_type", "general"),
    )
    db.add(note)
    await db.flush()
    return {"id": str(note.id), "content": note.content}


async def _get_opp(db: Any, tenant_id: uuid.UUID, opportunity_id: uuid.UUID) -> Opportunity:
    result = await db.execute(
        select(Opportunity).where(
            Opportunity.id == opportunity_id,
            Opportunity.tenant_id == tenant_id,
        )
    )
    opp = result.scalar_one_or_none()
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return opp
