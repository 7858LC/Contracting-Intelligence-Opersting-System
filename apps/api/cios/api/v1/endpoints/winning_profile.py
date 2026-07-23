"""Winning Profile Hypothesis™ Engine — REST API.

The pre-award intelligence workflow, surfaced end to end:

    solicitation → evidence documents → signals → Winning Profile Hypothesis™
      → contractor alignment + ranking → gaps + closures → PDQ™ assessment

Every route is tenant-scoped via the ``Auth`` dependency; PostgreSQL RLS enforces
isolation as defense in depth.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from cios.core.dependencies import DB, Auth, Pages
from cios.models.winning_profile import (
    WPHAlignment,
    WPHAssessment,
    WPHContractor,
    WPHEvidenceDocument,
    WPHProfile,
    WPHProfileAttribute,
    WPHSignal,
    WPHSolicitation,
)
from cios.wph.constants import EvidenceDocumentType, PipelineStatus
from cios.wph.service import WPHService

router = APIRouter()


# ── Pydantic schemas ─────────────────────────────────────────────────────────────


class SolicitationCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=512)
    solicitation_number: str | None = None
    agency: str | None = None
    sub_agency: str | None = None
    description: str | None = None
    naics_codes: list[str] = []
    psc_codes: list[str] = []
    set_aside_type: str | None = None
    estimated_value: float | None = None
    incumbent: str | None = None
    rule_pack: str = "us_federal_far"
    opportunity_id: uuid.UUID | None = None


class SolicitationResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    title: str
    solicitation_number: str | None
    agency: str | None
    sub_agency: str | None
    description: str | None
    naics_codes: list
    psc_codes: list
    set_aside_type: str | None
    estimated_value: float | None
    incumbent: str | None
    rule_pack: str
    pipeline_status: str
    document_count: int
    signal_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentCreate(BaseModel):
    document_type: EvidenceDocumentType
    title: str = Field(..., min_length=1, max_length=512)
    content: str = Field(..., min_length=1)
    source_url: str | None = None
    source_ref: str | None = None


class DocumentResponse(BaseModel):
    id: uuid.UUID
    solicitation_id: uuid.UUID
    document_type: str
    title: str
    source_url: str | None
    source_ref: str | None
    is_extracted: bool
    created_at: datetime

    class Config:
        from_attributes = True


class CapabilityItem(BaseModel):
    name: str
    level: float = Field(..., ge=0, le=100)
    evidence: str | None = None


class ContractorCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    description: str | None = None
    samgov_uei: str | None = Field(None, max_length=12)
    cage_code: str | None = Field(None, max_length=10)
    is_self: bool = False
    is_incumbent: bool = False
    business_size: str | None = None
    employee_count: int | None = None
    naics_codes: list[str] = []
    certifications: list[str] = []
    set_asides: list[str] = []
    clearances: list[str] = []
    capabilities: list[CapabilityItem] = []
    past_performance: list[dict] = []


class ContractorResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    samgov_uei: str | None
    cage_code: str | None
    is_self: bool
    is_incumbent: bool
    business_size: str | None
    naics_codes: list
    certifications: list
    set_asides: list
    clearances: list
    capabilities: list
    past_performance: list
    created_at: datetime

    class Config:
        from_attributes = True


class AlignRequest(BaseModel):
    contractor_ids: list[uuid.UUID] | None = None  # None → all tenant contractors


class AssessRequest(BaseModel):
    target_contractor_id: uuid.UUID | None = None  # None → self, else top-ranked


# ── Helpers ──────────────────────────────────────────────────────────────────────


async def _get_solicitation(db: Any, sol_id: uuid.UUID, tenant_id: uuid.UUID) -> WPHSolicitation:
    row = (
        await db.execute(
            select(WPHSolicitation).where(
                WPHSolicitation.id == sol_id, WPHSolicitation.tenant_id == tenant_id
            )
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Solicitation not found")
    return row


async def _current_profile(db: Any, sol_id: uuid.UUID, tenant_id: uuid.UUID) -> WPHProfile:
    row = (
        await db.execute(
            select(WPHProfile).where(
                WPHProfile.solicitation_id == sol_id,
                WPHProfile.tenant_id == tenant_id,
                WPHProfile.is_current.is_(True),
            )
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(
            status_code=409,
            detail="No Winning Profile Hypothesis yet. Generate one first.",
        )
    return row


async def _profile_payload(db: Any, profile: WPHProfile, tenant_id: uuid.UUID) -> dict:
    attrs = (
        (
            await db.execute(
                select(WPHProfileAttribute)
                .where(
                    WPHProfileAttribute.profile_id == profile.id,
                    WPHProfileAttribute.tenant_id == tenant_id,
                )
                .order_by(WPHProfileAttribute.importance_weight.desc())
            )
        )
        .scalars()
        .all()
    )
    return {
        "id": str(profile.id),
        "version": profile.version,
        "is_current": profile.is_current,
        "summary": profile.summary,
        "narrative": profile.narrative,
        "overall_confidence": profile.overall_confidence,
        "evidence_strength": profile.evidence_strength,
        "attribute_count": profile.attribute_count,
        "unknown_factors": profile.unknown_factors,
        "shaping_risk": profile.shaping_risk,
        "vehicle_contestability": profile.vehicle_contestability,
        "model_used": profile.model_used,
        "created_at": profile.created_at.isoformat() if profile.created_at else None,
        "attributes": [
            {
                "name": a.name,
                "category": a.category,
                "description": a.description,
                "importance_weight": a.importance_weight,
                "evidence_confidence": a.evidence_confidence,
                "confidence_level": a.confidence_level,
                "required_level": a.required_level,
                "supporting_evidence": a.supporting_evidence,
                "evidence_source_refs": a.evidence_source_refs,
                "reasoning": a.reasoning,
                "unknown_factors": a.unknown_factors,
            }
            for a in attrs
        ],
    }


def _alignment_payload(a: WPHAlignment) -> dict:
    return {
        "id": str(a.id),
        "contractor_id": str(a.contractor_id),
        "contractor_name": a.contractor_name,
        "overall_alignment_score": a.overall_alignment_score,
        "rank": a.rank,
        "attribute_alignments": a.attribute_alignments,
        "gaps": a.gaps,
        "gap_closures": a.gap_closures,
        "strengths": a.strengths,
        "weaknesses": a.weaknesses,
        "summary": a.summary,
    }


def _assessment_payload(a: WPHAssessment) -> dict:
    return {
        "id": str(a.id),
        "target_contractor_id": str(a.target_contractor_id) if a.target_contractor_id else None,
        "target_contractor_name": a.target_contractor_name,
        "pdq_score": a.pdq_score,
        "win_positioning_score": a.win_positioning_score,
        "competitive_rank": a.competitive_rank,
        "candidate_pool_size": a.candidate_pool_size,
        "recommendation": a.recommendation,
        "executive_summary": a.executive_summary,
        "narrative": a.narrative,
        "key_findings": a.key_findings,
        "decision_factors": a.decision_factors,
        "critical_gaps": a.critical_gaps,
        "recommended_actions": a.recommended_actions,
        "risks": a.risks,
        "assumptions": a.assumptions,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


# ── Solicitations ────────────────────────────────────────────────────────────────


@router.post(
    "/solicitations", response_model=SolicitationResponse, status_code=status.HTTP_201_CREATED
)
async def create_solicitation(payload: SolicitationCreate, user: Auth, db: DB) -> WPHSolicitation:
    sol = WPHSolicitation(
        tenant_id=user.tenant_id,
        created_by=user.user_id,
        pipeline_status=PipelineStatus.DRAFT.value,
        **payload.model_dump(),
    )
    db.add(sol)
    await db.commit()
    await db.refresh(sol)
    return sol


@router.get("/solicitations", response_model=dict)
async def list_solicitations(
    user: Auth, db: DB, pages: Pages, pipeline_status: str | None = Query(None)
) -> dict:
    q = select(WPHSolicitation).where(WPHSolicitation.tenant_id == user.tenant_id)
    if pipeline_status:
        q = q.where(WPHSolicitation.pipeline_status == pipeline_status)
    q = q.order_by(WPHSolicitation.created_at.desc())

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    rows = (await db.execute(q.offset(pages.offset).limit(pages.limit))).scalars().all()
    return {
        "items": [SolicitationResponse.model_validate(r).model_dump() for r in rows],
        "total": total,
        "page": pages.page,
        "page_size": pages.page_size,
    }


@router.get("/solicitations/{sol_id}", response_model=SolicitationResponse)
async def get_solicitation(sol_id: uuid.UUID, user: Auth, db: DB) -> WPHSolicitation:
    return await _get_solicitation(db, sol_id, user.tenant_id)


@router.delete("/solicitations/{sol_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_solicitation(sol_id: uuid.UUID, user: Auth, db: DB) -> None:
    sol = await _get_solicitation(db, sol_id, user.tenant_id)
    await db.delete(sol)
    await db.commit()


# ── Evidence documents ───────────────────────────────────────────────────────────


@router.post(
    "/solicitations/{sol_id}/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_document(
    sol_id: uuid.UUID, payload: DocumentCreate, user: Auth, db: DB
) -> WPHEvidenceDocument:
    sol = await _get_solicitation(db, sol_id, user.tenant_id)
    doc = WPHEvidenceDocument(
        tenant_id=user.tenant_id,
        solicitation_id=sol.id,
        document_type=payload.document_type.value,
        title=payload.title,
        content=payload.content,
        source_url=payload.source_url,
        source_ref=payload.source_ref,
    )
    db.add(doc)
    sol.document_count = (sol.document_count or 0) + 1
    if sol.pipeline_status == PipelineStatus.DRAFT.value:
        sol.pipeline_status = PipelineStatus.EVIDENCE_READY.value
    await db.commit()
    await db.refresh(doc)
    return doc


@router.get("/solicitations/{sol_id}/documents", response_model=list[DocumentResponse])
async def list_documents(sol_id: uuid.UUID, user: Auth, db: DB) -> list[WPHEvidenceDocument]:
    await _get_solicitation(db, sol_id, user.tenant_id)
    rows = (
        (
            await db.execute(
                select(WPHEvidenceDocument)
                .where(
                    WPHEvidenceDocument.solicitation_id == sol_id,
                    WPHEvidenceDocument.tenant_id == user.tenant_id,
                )
                .order_by(WPHEvidenceDocument.created_at.asc())
            )
        )
        .scalars()
        .all()
    )
    return list(rows)


# ── Signal extraction ────────────────────────────────────────────────────────────


@router.post("/solicitations/{sol_id}/extract-signals", response_model=dict)
async def extract_signals(sol_id: uuid.UUID, user: Auth, db: DB) -> dict:
    sol = await _get_solicitation(db, sol_id, user.tenant_id)
    signals = await WPHService(db).extract_signals(sol, user.tenant_id)
    return {"signal_count": len(signals), "pipeline_status": sol.pipeline_status}


@router.get("/solicitations/{sol_id}/signals", response_model=dict)
async def list_signals(
    sol_id: uuid.UUID, user: Auth, db: DB, category: str | None = Query(None)
) -> dict:
    await _get_solicitation(db, sol_id, user.tenant_id)
    q = select(WPHSignal).where(
        WPHSignal.solicitation_id == sol_id, WPHSignal.tenant_id == user.tenant_id
    )
    if category:
        q = q.where(WPHSignal.category == category)
    q = q.order_by(WPHSignal.strength.desc())
    rows = (await db.execute(q)).scalars().all()

    by_category: dict[str, int] = {}
    items = []
    for s in rows:
        by_category[s.category] = by_category.get(s.category, 0) + 1
        items.append(
            {
                "id": str(s.id),
                "category": s.category,
                "evidence_text": s.evidence_text,
                "interpretation": s.interpretation,
                "strength": s.strength,
                "confidence": s.confidence,
                "source_document_type": s.source_document_type,
                "source_ref": s.source_ref,
                "keywords": s.keywords,
            }
        )
    return {"total": len(items), "by_category": by_category, "items": items}


# ── Winning Profile Hypothesis™ ──────────────────────────────────────────────────


@router.post("/solicitations/{sol_id}/generate-profile", response_model=dict)
async def generate_profile(
    sol_id: uuid.UUID,
    user: Auth,
    db: DB,
    enrich: bool = Query(False, description="Add Claude narrative enrichment"),
) -> dict:
    sol = await _get_solicitation(db, sol_id, user.tenant_id)

    # Ensure signals exist (extract on demand).
    have = (
        await db.execute(
            select(func.count(WPHSignal.id)).where(
                WPHSignal.solicitation_id == sol.id, WPHSignal.tenant_id == user.tenant_id
            )
        )
    ).scalar_one()
    service = WPHService(db)
    if have == 0:
        await service.extract_signals(sol, user.tenant_id)

    profile = await service.generate_profile(sol, user.tenant_id)

    if enrich:
        from cios.agents.winning_profile_agent import enrich_profile_narrative

        pdc = await service.load_profile_dataclass(profile, user.tenant_id)
        narrative = await enrich_profile_narrative(
            pdc,
            user.tenant_id,
            {"title": sol.title, "agency": sol.agency},
        )
        if narrative:
            profile.narrative = narrative
            profile.model_used = "claude-sonnet-4-6"
            await db.commit()
            await db.refresh(profile)

    return await _profile_payload(db, profile, user.tenant_id)


@router.get("/solicitations/{sol_id}/profile", response_model=dict)
async def get_profile(sol_id: uuid.UUID, user: Auth, db: DB) -> dict:
    await _get_solicitation(db, sol_id, user.tenant_id)
    profile = await _current_profile(db, sol_id, user.tenant_id)
    return await _profile_payload(db, profile, user.tenant_id)


# ── Contractors ──────────────────────────────────────────────────────────────────


@router.post("/contractors", response_model=ContractorResponse, status_code=status.HTTP_201_CREATED)
async def create_contractor(payload: ContractorCreate, user: Auth, db: DB) -> WPHContractor:
    existing = (
        await db.execute(
            select(WPHContractor).where(
                WPHContractor.tenant_id == user.tenant_id, WPHContractor.name == payload.name
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail=f"Contractor '{payload.name}' already exists")

    data = payload.model_dump()
    data["capabilities"] = [
        c.model_dump() if hasattr(c, "model_dump") else c for c in payload.capabilities
    ]
    contractor = WPHContractor(tenant_id=user.tenant_id, **data)
    db.add(contractor)
    await db.commit()
    await db.refresh(contractor)
    return contractor


@router.get("/contractors", response_model=list[ContractorResponse])
async def list_contractors(user: Auth, db: DB) -> list[WPHContractor]:
    rows = (
        (
            await db.execute(
                select(WPHContractor)
                .where(WPHContractor.tenant_id == user.tenant_id)
                .order_by(WPHContractor.is_self.desc(), WPHContractor.name.asc())
            )
        )
        .scalars()
        .all()
    )
    return list(rows)


@router.delete("/contractors/{contractor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contractor(contractor_id: uuid.UUID, user: Auth, db: DB) -> None:
    row = (
        await db.execute(
            select(WPHContractor).where(
                WPHContractor.id == contractor_id, WPHContractor.tenant_id == user.tenant_id
            )
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Contractor not found")
    await db.delete(row)
    await db.commit()


# ── Alignment + ranking ──────────────────────────────────────────────────────────


@router.post("/solicitations/{sol_id}/align", response_model=dict)
async def align(sol_id: uuid.UUID, payload: AlignRequest, user: Auth, db: DB) -> dict:
    sol = await _get_solicitation(db, sol_id, user.tenant_id)
    profile = await _current_profile(db, sol_id, user.tenant_id)
    rows = await WPHService(db).align_contractors(
        sol, profile, user.tenant_id, payload.contractor_ids
    )
    if not rows:
        raise HTTPException(
            status_code=409, detail="No contractors to align. Add contractors first."
        )
    return {"count": len(rows), "rankings": [_alignment_payload(r) for r in rows]}


@router.get("/solicitations/{sol_id}/alignments", response_model=dict)
async def list_alignments(sol_id: uuid.UUID, user: Auth, db: DB) -> dict:
    await _get_solicitation(db, sol_id, user.tenant_id)
    profile = await _current_profile(db, sol_id, user.tenant_id)
    rows = (
        (
            await db.execute(
                select(WPHAlignment)
                .where(
                    WPHAlignment.profile_id == profile.id, WPHAlignment.tenant_id == user.tenant_id
                )
                .order_by(WPHAlignment.rank.asc())
            )
        )
        .scalars()
        .all()
    )
    return {"count": len(rows), "rankings": [_alignment_payload(r) for r in rows]}


@router.get("/solicitations/{sol_id}/alignments/{contractor_id}", response_model=dict)
async def get_alignment(sol_id: uuid.UUID, contractor_id: uuid.UUID, user: Auth, db: DB) -> dict:
    profile = await _current_profile(db, sol_id, user.tenant_id)
    row = (
        await db.execute(
            select(WPHAlignment).where(
                WPHAlignment.profile_id == profile.id,
                WPHAlignment.contractor_id == contractor_id,
                WPHAlignment.tenant_id == user.tenant_id,
            )
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Alignment not found")
    return _alignment_payload(row)


# ── Executive assessment ─────────────────────────────────────────────────────────


@router.post("/solicitations/{sol_id}/assess", response_model=dict)
async def assess(sol_id: uuid.UUID, payload: AssessRequest, user: Auth, db: DB) -> dict:
    sol = await _get_solicitation(db, sol_id, user.tenant_id)
    profile = await _current_profile(db, sol_id, user.tenant_id)
    assessment = await WPHService(db).assess(
        sol, profile, user.tenant_id, payload.target_contractor_id
    )
    if not assessment:
        raise HTTPException(
            status_code=409,
            detail="No alignments to assess. Run contractor alignment first.",
        )
    return _assessment_payload(assessment)


@router.get("/solicitations/{sol_id}/assessment", response_model=dict)
async def get_assessment(sol_id: uuid.UUID, user: Auth, db: DB) -> dict:
    await _get_solicitation(db, sol_id, user.tenant_id)
    row = (
        await db.execute(
            select(WPHAssessment)
            .where(
                WPHAssessment.solicitation_id == sol_id, WPHAssessment.tenant_id == user.tenant_id
            )
            .order_by(WPHAssessment.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="No assessment yet")
    return _assessment_payload(row)


# ── Full pipeline (vertical slice) ───────────────────────────────────────────────


@router.post("/solicitations/{sol_id}/run", response_model=dict)
async def run_pipeline(
    sol_id: uuid.UUID,
    user: Auth,
    db: DB,
    target_contractor_id: uuid.UUID | None = Query(None),
    enrich: bool = Query(False),
) -> dict:
    """Run the complete pre-award pipeline synchronously and return the full result."""
    sol = await _get_solicitation(db, sol_id, user.tenant_id)
    service = WPHService(db)

    await service.extract_signals(sol, user.tenant_id)
    profile = await service.generate_profile(sol, user.tenant_id)

    if enrich:
        from cios.agents.winning_profile_agent import enrich_profile_narrative

        pdc = await service.load_profile_dataclass(profile, user.tenant_id)
        narrative = await enrich_profile_narrative(
            pdc, user.tenant_id, {"title": sol.title, "agency": sol.agency}
        )
        if narrative:
            profile.narrative = narrative
            profile.model_used = "claude-sonnet-4-6"
            await db.commit()
            await db.refresh(profile)

    alignments = await service.align_contractors(sol, profile, user.tenant_id)
    assessment = None
    if alignments:
        assessment = await service.assess(sol, profile, user.tenant_id, target_contractor_id)

    return {
        "pipeline_status": sol.pipeline_status,
        "signal_count": sol.signal_count,
        "profile": await _profile_payload(db, profile, user.tenant_id),
        "rankings": [_alignment_payload(a) for a in alignments],
        "assessment": _assessment_payload(assessment) if assessment else None,
    }


@router.get("/solicitations/{sol_id}/intelligence", response_model=dict)
async def get_intelligence(sol_id: uuid.UUID, user: Auth, db: DB) -> dict:
    """Aggregate view: solicitation + current profile + rankings + latest assessment."""
    sol = await _get_solicitation(db, sol_id, user.tenant_id)
    out: dict[str, Any] = {
        "solicitation": SolicitationResponse.model_validate(sol).model_dump(),
        "profile": None,
        "rankings": [],
        "assessment": None,
    }
    profile = (
        await db.execute(
            select(WPHProfile).where(
                WPHProfile.solicitation_id == sol_id,
                WPHProfile.tenant_id == user.tenant_id,
                WPHProfile.is_current.is_(True),
            )
        )
    ).scalar_one_or_none()
    if profile:
        out["profile"] = await _profile_payload(db, profile, user.tenant_id)
        rows = (
            (
                await db.execute(
                    select(WPHAlignment)
                    .where(
                        WPHAlignment.profile_id == profile.id,
                        WPHAlignment.tenant_id == user.tenant_id,
                    )
                    .order_by(WPHAlignment.rank.asc())
                )
            )
            .scalars()
            .all()
        )
        out["rankings"] = [_alignment_payload(r) for r in rows]
    assessment = (
        await db.execute(
            select(WPHAssessment)
            .where(
                WPHAssessment.solicitation_id == sol_id, WPHAssessment.tenant_id == user.tenant_id
            )
            .order_by(WPHAssessment.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if assessment:
        out["assessment"] = _assessment_payload(assessment)
    return out


# ── Sample dataset seeding ───────────────────────────────────────────────────────


@router.post("/sample", response_model=dict, status_code=status.HTTP_201_CREATED)
async def seed_sample(
    user: Auth,
    db: DB,
    run: bool = Query(True, description="Run the full pipeline after seeding"),
) -> dict:
    """Seed the built-in sample solicitation + contractors and (optionally) run the
    full pipeline — a one-call demonstration of the vertical slice."""
    from cios.wph.sample_data import SAMPLE_CONTRACTORS, SAMPLE_DOCUMENTS, SAMPLE_SOLICITATION

    sol = WPHSolicitation(
        tenant_id=user.tenant_id,
        created_by=user.user_id,
        pipeline_status=PipelineStatus.EVIDENCE_READY.value,
        **SAMPLE_SOLICITATION,
    )
    db.add(sol)
    await db.flush()
    for doc in SAMPLE_DOCUMENTS:
        db.add(
            WPHEvidenceDocument(
                tenant_id=user.tenant_id,
                solicitation_id=sol.id,
                document_type=doc.document_type,
                title=doc.title,
                content=doc.content,
                source_ref=doc.source_ref,
            )
        )
    sol.document_count = len(SAMPLE_DOCUMENTS)

    for c in SAMPLE_CONTRACTORS:
        exists = (
            await db.execute(
                select(WPHContractor.id).where(
                    WPHContractor.tenant_id == user.tenant_id, WPHContractor.name == c.name
                )
            )
        ).scalar_one_or_none()
        if exists:
            continue
        # Fold capability free-text into the description so keyword matching works
        # after the round-trip through the DB (capabilities dict is empty in samples).
        description = " ".join(filter(None, [c.description, c.capability_text]))
        db.add(
            WPHContractor(
                tenant_id=user.tenant_id,
                name=c.name,
                description=description,
                is_self=c.is_self,
                is_incumbent=c.is_incumbent,
                business_size=c.business_size,
                certifications=c.certifications,
                set_asides=c.set_asides,
                clearances=c.clearances,
                capabilities=[{"name": k, "level": v} for k, v in c.capabilities.items()],
                past_performance=c.past_performance,
            )
        )
    await db.commit()

    if not run:
        await db.refresh(sol)
        return {"solicitation_id": str(sol.id), "pipeline_status": sol.pipeline_status}

    service = WPHService(db)
    await service.extract_signals(sol, user.tenant_id)
    profile = await service.generate_profile(sol, user.tenant_id)
    alignments = await service.align_contractors(sol, profile, user.tenant_id)
    assessment = None
    if alignments:
        assessment = await service.assess(sol, profile, user.tenant_id)

    return {
        "solicitation_id": str(sol.id),
        "pipeline_status": sol.pipeline_status,
        "signal_count": sol.signal_count,
        "profile": await _profile_payload(db, profile, user.tenant_id),
        "rankings": [_alignment_payload(a) for a in alignments],
        "assessment": _assessment_payload(assessment) if assessment else None,
    }
