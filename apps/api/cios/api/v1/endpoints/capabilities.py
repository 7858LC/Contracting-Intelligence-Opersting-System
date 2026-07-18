"""Capability & Gap Analysis API — Modules 5 & 15."""
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from cios.core.dependencies import Auth, DB
from cios.models.capability import Capability, CapabilityGap

router = APIRouter()


class CapabilityCreate(BaseModel):
    name: str
    category: str
    description: str | None = None
    maturity_level: str | None = None
    proficiency_score: float | None = None
    naics_codes: list[str] = []
    certifications: list[str] = []
    tools_and_technologies: list[str] = []


@router.get("")
async def list_capabilities(db: DB, user: Auth) -> dict:
    result = await db.execute(
        select(Capability).where(Capability.tenant_id == user.tenant_id)
        .order_by(Capability.category, Capability.name)
    )
    return {"capabilities": [i.to_dict() for i in result.scalars().all()]}


@router.post("")
async def create_capability(body: CapabilityCreate, db: DB, user: Auth) -> dict:
    cap = Capability(tenant_id=user.tenant_id, **body.model_dump())
    db.add(cap)
    await db.flush()
    return cap.to_dict()


@router.post("/analyze-gaps")
async def analyze_capability_gaps(
    body: dict, db: DB, user: Auth
) -> dict:
    """AI-powered gap analysis for a specific opportunity."""
    opportunity_id = body.get("opportunity_id")
    if not opportunity_id:
        raise HTTPException(status_code=400, detail="opportunity_id required")

    from cios.tasks.gap_analysis import run_capability_gap_analysis
    task = run_capability_gap_analysis.delay(
        str(user.tenant_id), str(user.user_id), str(opportunity_id)
    )
    return {"task_id": task.id, "status": "queued"}


@router.get("/gaps")
async def list_gaps(db: DB, user: Auth) -> dict:
    result = await db.execute(
        select(CapabilityGap).where(CapabilityGap.tenant_id == user.tenant_id)
        .order_by(CapabilityGap.severity, CapabilityGap.created_at.desc())
    )
    return {"gaps": [i.to_dict() for i in result.scalars().all()]}
