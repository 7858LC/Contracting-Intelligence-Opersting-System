"""Competitive Intelligence API — Module 8."""

import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from cios.core.dependencies import DB, Auth
from cios.models.competitor import Competitor, CompetitorIntelligence

router = APIRouter()


class CompetitorCreate(BaseModel):
    company_name: str
    cage_code: str | None = None
    naics_codes: list[str] = []
    known_strengths: list[str] = []
    known_weaknesses: list[str] = []
    threat_level: str = "medium"
    pricing_tendency: str | None = None
    annual_contract_volume: float | None = None
    win_rate_estimate: float | None = None
    socioeconomic_statuses: list[str] = []
    active_clearances: list[str] = []
    certifications: list[str] = []
    notes: str | None = None
    tags: list[str] = []


class CompetitorResponse(BaseModel):
    id: uuid.UUID
    company_name: str
    cage_code: str | None
    duns_number: str | None
    naics_codes: list
    capabilities_summary: str | None
    known_strengths: list
    known_weaknesses: list
    win_rate_estimate: float | None
    annual_contract_volume: float | None
    past_awards: list
    agency_relationships: list
    pricing_tendency: str | None
    threat_level: str
    socioeconomic_statuses: list
    active_clearances: list
    certifications: list
    notes: str | None
    tags: list
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CompetitorListResponse(BaseModel):
    competitors: list[CompetitorResponse]


class CompetitorIntelCreate(BaseModel):
    intel_type: str
    content: str
    source: str | None = None
    source_url: str | None = None


class CompetitorIntelResponse(BaseModel):
    id: uuid.UUID
    competitor_id: uuid.UUID
    opportunity_id: uuid.UUID | None
    intel_type: str
    content: str
    source: str | None
    source_url: str | None
    relevance_score: float | None
    is_verified: bool | None
    evidence: dict | None
    confidence_score: float | None
    ai_model_version: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AnalyzeCompetitiveLandscapeRequest(BaseModel):
    opportunity_id: str


class AnalyzeQueuedResponse(BaseModel):
    task_id: str
    status: str


@router.get("", response_model=CompetitorListResponse)
async def list_competitors(
    db: DB,
    user: Auth,
    threat_level: str | None = None,
) -> dict:
    q = select(Competitor).where(Competitor.tenant_id == user.tenant_id)
    if threat_level:
        q = q.where(Competitor.threat_level == threat_level)
    q = q.order_by(Competitor.threat_level, Competitor.company_name)
    result = await db.execute(q)
    return {"competitors": result.scalars().all()}


@router.post("", response_model=CompetitorResponse)
async def add_competitor(body: CompetitorCreate, db: DB, user: Auth) -> Competitor:
    comp = Competitor(tenant_id=user.tenant_id, **body.model_dump())
    db.add(comp)
    await db.flush()
    return comp


@router.post("/{competitor_id}/intel", response_model=CompetitorIntelResponse)
async def add_competitor_intel(
    competitor_id: str,
    body: CompetitorIntelCreate,
    db: DB,
    user: Auth,
) -> CompetitorIntelligence:
    result = await db.execute(
        select(Competitor).where(
            Competitor.id == competitor_id,
            Competitor.tenant_id == user.tenant_id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Competitor not found")
    intel = CompetitorIntelligence(
        tenant_id=user.tenant_id,
        competitor_id=competitor_id,
        **body.model_dump(),
    )
    db.add(intel)
    await db.flush()
    return intel


@router.post("/analyze", response_model=AnalyzeQueuedResponse)
async def analyze_competitive_landscape(
    body: AnalyzeCompetitiveLandscapeRequest, db: DB, user: Auth
) -> dict:
    from cios.tasks.competitive_intel import run_competitive_analysis

    task = run_competitive_analysis.delay(
        str(user.tenant_id), str(user.user_id), body.opportunity_id
    )
    return {"task_id": task.id, "status": "queued"}
