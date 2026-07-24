"""Capability & Gap Analysis API — Modules 5 & 15."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from cios.core.dependencies import DB, Auth
from cios.models.capability import Capability, CapabilityGap

router = APIRouter()


class CapabilityCreate(BaseModel):
    name: str
    category: str
    description: str | None = None
    proficiency_level: int | None = None
    proficiency_score: float | None = None
    maturity_level: str | None = None
    is_certified: bool = False
    certifications: list[str] = []
    naics_codes: list[str] = []
    tools_and_technologies: list[str] = []


@router.get("")
async def list_capabilities(
    db: DB,
    user: Auth,
    category: str | None = None,
) -> dict:
    q = select(Capability).where(Capability.tenant_id == user.tenant_id)
    if category:
        q = q.where(Capability.category == category)
    q = q.order_by(Capability.category, Capability.name)
    result = await db.execute(q)
    return {"capabilities": [i.to_dict() for i in result.scalars().all()]}


@router.post("")
async def create_capability(body: CapabilityCreate, db: DB, user: Auth) -> dict:
    cap = Capability(tenant_id=user.tenant_id, **body.model_dump())
    db.add(cap)
    await db.flush()
    return cap.to_dict()


@router.delete("/{capability_id}")
async def delete_capability(capability_id: str, db: DB, user: Auth) -> dict:
    result = await db.execute(
        select(Capability).where(
            Capability.id == capability_id,
            Capability.tenant_id == user.tenant_id,
        )
    )
    cap = result.scalar_one_or_none()
    if not cap:
        raise HTTPException(status_code=404, detail="Capability not found")
    await db.delete(cap)
    return {"deleted": True}


@router.post("/analyze-gaps")
async def analyze_capability_gaps(body: dict, db: DB, user: Auth) -> dict:
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
        select(CapabilityGap)
        .where(CapabilityGap.tenant_id == user.tenant_id)
        .order_by(CapabilityGap.severity, CapabilityGap.created_at.desc())
    )
    return {"gaps": [i.to_dict() for i in result.scalars().all()]}
