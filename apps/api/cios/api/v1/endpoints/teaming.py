"""Teaming Recommendation Engine API — Module 7."""

import uuid
from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from cios.core.dependencies import DB, Auth
from cios.models.teaming import TeamingPartner, TeamingRecommendation

router = APIRouter()


class TeamingPartnerCreate(BaseModel):
    company_name: str
    cage_code: str | None = None
    naics_codes: list[str] = []
    socioeconomic_status: list[str] = []
    past_performance_rating: int | None = None
    active_agreements: bool = False
    relationship_strength: int = 3
    capabilities: list[str] = []
    poc_name: str | None = None
    poc_email: str | None = None
    notes: str | None = None


class TeamingPartnerResponse(BaseModel):
    id: uuid.UUID
    company_name: str
    cage_code: str | None
    duns_number: str | None
    sam_unique_id: str | None
    website: str | None
    naics_codes: list
    psc_codes: list
    capabilities: list
    socioeconomic_status: list
    past_performance_rating: int | None
    active_agreements: bool
    relationship_strength: int
    poc_name: str | None
    poc_email: str | None
    notes: str | None
    ai_compatibility_score: float | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TeamingPartnerListResponse(BaseModel):
    partners: list[TeamingPartnerResponse]


class TeamingRecommendationResponse(BaseModel):
    id: uuid.UUID
    opportunity_id: uuid.UUID
    prime_or_sub: str
    rationale: str | None
    team_structure: dict
    capability_gaps_addressed: list
    recommended_partners: list
    risk_assessment: dict | None
    win_probability_impact: float | None
    risks: list
    status: str
    evidence: dict | None
    confidence_score: float | None
    ai_model_version: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TeamingRecommendationListResponse(BaseModel):
    recommendations: list[TeamingRecommendationResponse]


class RecommendQueuedResponse(BaseModel):
    task_id: str
    status: str


@router.get("/partners", response_model=TeamingPartnerListResponse)
async def list_partners(db: DB, user: Auth) -> dict:
    result = await db.execute(
        select(TeamingPartner)
        .where(TeamingPartner.tenant_id == user.tenant_id)
        .order_by(TeamingPartner.relationship_strength.desc(), TeamingPartner.company_name)
    )
    return {"partners": result.scalars().all()}


@router.post("/partners", response_model=TeamingPartnerResponse)
async def add_partner(body: TeamingPartnerCreate, db: DB, user: Auth) -> TeamingPartner:
    partner = TeamingPartner(tenant_id=user.tenant_id, **body.model_dump())
    db.add(partner)
    await db.flush()
    return partner


@router.post("/recommend", response_model=RecommendQueuedResponse)
async def get_teaming_recommendations(body: dict, db: DB, user: Auth) -> dict:
    """AI-powered teaming strategy recommendation for an opportunity."""
    from cios.tasks.teaming import run_teaming_analysis

    task = run_teaming_analysis.delay(
        str(user.tenant_id),
        str(user.user_id),
        body.get("opportunity_id"),
    )
    return {"task_id": task.id, "status": "queued"}


@router.get("/recommendations", response_model=TeamingRecommendationListResponse)
async def list_recommendations(db: DB, user: Auth) -> dict:
    result = await db.execute(
        select(TeamingRecommendation)
        .where(TeamingRecommendation.tenant_id == user.tenant_id)
        .order_by(TeamingRecommendation.created_at.desc())
    )
    return {"recommendations": result.scalars().all()}
