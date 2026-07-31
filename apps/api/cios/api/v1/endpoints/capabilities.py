"""Capability & Gap Analysis API — Modules 5 & 15."""

import uuid
from datetime import datetime

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


class CapabilityResponse(BaseModel):
    id: uuid.UUID
    name: str
    category: str
    description: str | None
    proficiency_level: int | None
    proficiency_score: float | None
    maturity_level: str | None
    is_certified: bool
    certifications: list
    gap_score: float | None
    gap_analysis: dict | None
    improvement_plan: str | None
    supporting_evidence: list
    naics_codes: list
    psc_codes: list
    tools_and_technologies: list
    team_members_count: int | None
    last_demonstrated: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CapabilityListResponse(BaseModel):
    capabilities: list[CapabilityResponse]


class DeletedResponse(BaseModel):
    deleted: bool


class GapAnalysisRequest(BaseModel):
    opportunity_id: str


class GapAnalysisQueuedResponse(BaseModel):
    task_id: str
    status: str


class CapabilityGapResponse(BaseModel):
    id: uuid.UUID
    opportunity_id: str | None
    gap_name: str
    category: str
    severity: str
    description: str | None
    remediation_options: list
    estimated_cost_to_close: float | None
    estimated_time_to_close_days: int | None
    teaming_recommendation: str | None
    status: str
    evidence: dict | None
    confidence_score: float | None
    ai_model_version: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CapabilityGapListResponse(BaseModel):
    gaps: list[CapabilityGapResponse]


@router.get("", response_model=CapabilityListResponse)
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
    return {"capabilities": result.scalars().all()}


@router.post("", response_model=CapabilityResponse)
async def create_capability(body: CapabilityCreate, db: DB, user: Auth) -> Capability:
    cap = Capability(tenant_id=user.tenant_id, **body.model_dump())
    db.add(cap)
    await db.flush()
    return cap


@router.delete("/{capability_id}", response_model=DeletedResponse)
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


@router.post("/analyze-gaps", response_model=GapAnalysisQueuedResponse)
async def analyze_capability_gaps(body: GapAnalysisRequest, db: DB, user: Auth) -> dict:
    from cios.tasks.gap_analysis import run_capability_gap_analysis

    task = run_capability_gap_analysis.delay(
        str(user.tenant_id), str(user.user_id), body.opportunity_id
    )
    return {"task_id": task.id, "status": "queued"}


@router.get("/gaps", response_model=CapabilityGapListResponse)
async def list_gaps(db: DB, user: Auth) -> dict:
    result = await db.execute(
        select(CapabilityGap)
        .where(CapabilityGap.tenant_id == user.tenant_id)
        .order_by(CapabilityGap.severity, CapabilityGap.created_at.desc())
    )
    return {"gaps": result.scalars().all()}
