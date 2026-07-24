"""Competitive Intelligence API — Module 8."""

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


class CompetitorIntelCreate(BaseModel):
    intel_type: str
    content: str
    source: str | None = None
    source_url: str | None = None


@router.get("")
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
    return {"competitors": [c.to_dict() for c in result.scalars().all()]}


@router.post("")
async def add_competitor(body: CompetitorCreate, db: DB, user: Auth) -> dict:
    comp = Competitor(tenant_id=user.tenant_id, **body.model_dump())
    db.add(comp)
    await db.flush()
    return comp.to_dict()


@router.post("/{competitor_id}/intel")
async def add_competitor_intel(
    competitor_id: str,
    body: CompetitorIntelCreate,
    db: DB,
    user: Auth,
) -> dict:
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
    return intel.to_dict()


@router.post("/analyze")
async def analyze_competitive_landscape(body: dict, db: DB, user: Auth) -> dict:
    from cios.tasks.competitive_intel import run_competitive_analysis

    task = run_competitive_analysis.delay(
        str(user.tenant_id), str(user.user_id), body.get("opportunity_id")
    )
    return {"task_id": task.id, "status": "queued"}
