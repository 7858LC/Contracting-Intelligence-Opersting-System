"""Teaming Recommendation Engine API — Module 7."""

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


@router.get("/partners")
async def list_partners(db: DB, user: Auth) -> dict:
    result = await db.execute(
        select(TeamingPartner)
        .where(TeamingPartner.tenant_id == user.tenant_id)
        .order_by(TeamingPartner.relationship_strength.desc(), TeamingPartner.company_name)
    )
    return {"partners": [p.to_dict() for p in result.scalars().all()]}


@router.post("/partners")
async def add_partner(body: TeamingPartnerCreate, db: DB, user: Auth) -> dict:
    partner = TeamingPartner(tenant_id=user.tenant_id, **body.model_dump())
    db.add(partner)
    await db.flush()
    return partner.to_dict()


@router.post("/recommend")
async def get_teaming_recommendations(body: dict, db: DB, user: Auth) -> dict:
    """AI-powered teaming strategy recommendation for an opportunity."""
    from cios.tasks.teaming import run_teaming_analysis

    task = run_teaming_analysis.delay(
        str(user.tenant_id),
        str(user.user_id),
        body.get("opportunity_id"),
    )
    return {"task_id": task.id, "status": "queued"}


@router.get("/recommendations")
async def list_recommendations(db: DB, user: Auth) -> dict:
    result = await db.execute(
        select(TeamingRecommendation)
        .where(TeamingRecommendation.tenant_id == user.tenant_id)
        .order_by(TeamingRecommendation.created_at.desc())
    )
    return {"recommendations": [r.to_dict() for r in result.scalars().all()]}
