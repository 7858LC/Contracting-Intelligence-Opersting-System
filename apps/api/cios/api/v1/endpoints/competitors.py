"""Competitive Intelligence API — Module 8."""
from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from cios.core.dependencies import Auth, DB
from cios.models.competitor import Competitor

router = APIRouter()


class CompetitorCreate(BaseModel):
    company_name: str
    cage_code: str | None = None
    naics_codes: list[str] = []
    known_strengths: list[str] = []
    known_weaknesses: list[str] = []
    threat_level: str = "medium"
    pricing_tendency: str | None = None


@router.get("")
async def list_competitors(db: DB, user: Auth) -> dict:
    result = await db.execute(
        select(Competitor).where(Competitor.tenant_id == user.tenant_id)
        .order_by(Competitor.threat_level, Competitor.company_name)
    )
    return {"competitors": [c.to_dict() for c in result.scalars().all()]}


@router.post("")
async def add_competitor(body: CompetitorCreate, db: DB, user: Auth) -> dict:
    comp = Competitor(tenant_id=user.tenant_id, **body.model_dump())
    db.add(comp)
    await db.flush()
    return comp.to_dict()


@router.post("/analyze")
async def analyze_competitive_landscape(body: dict, db: DB, user: Auth) -> dict:
    """AI competitive landscape analysis for an opportunity."""
    from cios.tasks.competitive_intel import run_competitive_analysis
    task = run_competitive_analysis.delay(
        str(user.tenant_id), str(user.user_id), body.get("opportunity_id")
    )
    return {"task_id": task.id, "status": "queued"}
