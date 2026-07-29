"""Winning Profile Hypothesis™ Engine — REST API.

The pre-award intelligence workflow, surfaced end to end:

    solicitation → evidence documents → signals → Winning Profile Hypothesis™
      → contractor alignment + ranking → gaps + closures → PDQ™ assessment

Every route is tenant-scoped via the ``Auth`` dependency; PostgreSQL RLS enforces
isolation as defense in depth.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select

from cios.core.dependencies import DB, Auth, Pages
from cios.models.winning_profile import (
    WPHAlignment,
    WPHAssessment,
    WPHCapturePackage,
    WPHContractor,
    WPHEvidenceDocument,
    WPHProfile,
    WPHProfileAttribute,
    WPHSignal,
    WPHSolicitation,
)
from cios.wph.constants import CapturePackageStatus, EvidenceDocumentType, PipelineStatus
from cios.wph.service import WPHService
from cios.wph.taxonomy import TAXONOMY_REGISTRY

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
    is_task_order: bool = False
    base_vehicle_name: str | None = None
    base_vehicle_contract_number: str | None = None

    @field_validator("rule_pack")
    @classmethod
    def _known_rule_pack(cls, v: str) -> str:
        if v not in TAXONOMY_REGISTRY:
            raise ValueError(
                f"Unknown rule pack '{v}'. Registered rule packs: "
                f"{', '.join(sorted(TAXONOMY_REGISTRY))}."
            )
        return v


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
    is_task_order: bool
    base_vehicle_name: str | None
    base_vehicle_contract_number: str | None
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


# ── Response schemas ─────────────────────────────────────────────────────────────
#
# These mirror the dict payloads the helper functions below already build
# (str(uuid) / .isoformat() conversions and all) — response_model validates
# the existing dicts against these rather than requiring any change to how
# the payloads are constructed. Every field here was previously invisible to
# the OpenAPI schema (response_model=dict), which is what let the frontend's
# hand-written types drift from reality undetected — see the confirmed drift
# on CapturePackageResponse below (frontend was missing 5 real fields and
# had over-narrowed status to a 2-value literal).


class SolicitationListResponse(BaseModel):
    items: list[SolicitationResponse]
    total: int
    page: int
    page_size: int


class ExtractSignalsResponse(BaseModel):
    signal_count: int
    pipeline_status: str


class SignalResponse(BaseModel):
    id: str
    category: str
    evidence_text: str | None
    interpretation: str | None
    strength: float | None
    confidence: float | None
    source_document_type: str | None
    source_ref: str | None
    keywords: list


class SignalListResponse(BaseModel):
    total: int
    by_category: dict[str, int]
    items: list[SignalResponse]


# The recurring [{text, source}] shape documented on InferredAttribute,
# ShapingRiskFlag, VehicleContestabilityFlag, and TaskOrderFairOpportunityFlag
# in cios/wph/schemas.py — one real shape, reused everywhere it's used.
class EvidenceItem(BaseModel):
    text: str
    source: str


class ProfileAttributeResponse(BaseModel):
    name: str
    category: str | None
    description: str | None
    importance_weight: float | None
    evidence_confidence: float | None
    confidence_level: str | None
    required_level: float | None
    supporting_evidence: list[EvidenceItem]
    evidence_source_refs: list[str]
    reasoning: str | None = None
    unknown_factors: list[str] | None = None


# Mirrors cios/wph/schemas.py's ShapingRiskFlag/VehicleContestabilityFlag/
# TaskOrderFairOpportunityFlag .to_dict() output exactly — these are real
# structured dataclasses, not freeform JSON, despite living in a JSONB column.
class ShapingRiskResponse(BaseModel):
    risk_level: str
    signal_count: int
    supporting_evidence: list[EvidenceItem]
    source_refs: list[str]
    narrative: str


class VehicleContestabilityResponse(BaseModel):
    contestability: str
    open_signal_count: int
    narrow_signal_count: int
    open_evidence: list[EvidenceItem]
    narrow_evidence: list[EvidenceItem]
    source_refs: list[str]
    narrative: str


class TaskOrderFairOpportunityResponse(BaseModel):
    fair_opportunity_status: str
    competed_signal_count: int
    directed_signal_count: int
    competed_evidence: list[EvidenceItem]
    directed_evidence: list[EvidenceItem]
    source_refs: list[str]
    narrative: str


class ProfileResponse(BaseModel):
    id: str
    version: int
    is_current: bool
    summary: str | None
    narrative: str | None
    overall_confidence: float | None
    evidence_strength: float | None
    attribute_count: int | None
    unknown_factors: list[str]
    shaping_risk: ShapingRiskResponse
    vehicle_contestability: VehicleContestabilityResponse
    task_order_fair_opportunity: TaskOrderFairOpportunityResponse
    model_used: str | None
    created_at: str | None
    attributes: list[ProfileAttributeResponse]


# Mirrors AttributeAlignment/CapabilityGap/GapClosure .to_dict() in
# cios/wph/schemas.py.
class AttributeAlignmentItem(BaseModel):
    attribute_key: str
    attribute_name: str
    category: str
    importance_weight: float
    required_level: float
    contractor_level: float
    alignment: float
    contribution: float
    evidence: str
    reasoning: str


class CapabilityGapItem(BaseModel):
    attribute_key: str
    attribute_name: str
    category: str
    severity: str
    importance_weight: float
    required_level: float
    contractor_level: float
    gap_size: float
    impact: str


class GapClosureItem(BaseModel):
    gap_attribute_key: str
    gap_attribute_name: str
    recommendation: str
    action_type: str
    effort: str
    timeline_months: int
    feasibility: str
    cost_band: str
    closes_gap_to: float


# Assessment.recommended_actions reuses GapClosure.to_dict() (see
# GapClosureItem above) but PDQEngine._actions() also inserts one synthetic
# item for the MONITOR recommendation that has no source gap to attribute to
# — hence gap_attribute_key/name/closes_gap_to are optional here, unlike on
# GapClosureItem itself.
class RecommendedActionItem(BaseModel):
    gap_attribute_key: str | None = None
    gap_attribute_name: str | None = None
    recommendation: str
    action_type: str
    effort: str
    timeline_months: int
    feasibility: str
    cost_band: str
    closes_gap_to: float | None = None


class DecisionFactorItem(BaseModel):
    factor: str
    value: str


class RiskItem(BaseModel):
    risk: str
    severity: str
    mitigation: str


class AlignmentResponse(BaseModel):
    id: str
    contractor_id: str
    contractor_name: str | None
    overall_alignment_score: float | None
    rank: int | None
    attribute_alignments: list[AttributeAlignmentItem]
    gaps: list[CapabilityGapItem]
    gap_closures: list[GapClosureItem]
    strengths: list[str]
    weaknesses: list[str]
    summary: str | None


class AlignRunResponse(BaseModel):
    count: int
    rankings: list[AlignmentResponse]


class AssessmentResponse(BaseModel):
    id: str
    target_contractor_id: str | None
    target_contractor_name: str | None
    pdq_score: float | None
    win_positioning_score: float | None
    competitive_rank: int | None
    candidate_pool_size: int | None
    recommendation: str | None
    executive_summary: str | None
    narrative: str | None
    key_findings: list[str]
    decision_factors: list[DecisionFactorItem]
    critical_gaps: list[CapabilityGapItem]
    recommended_actions: list[RecommendedActionItem]
    risks: list[RiskItem]
    assumptions: list[str]
    created_at: str | None


class PipelineRunResponse(BaseModel):
    pipeline_status: str
    signal_count: int
    profile: ProfileResponse
    rankings: list[AlignmentResponse]
    assessment: AssessmentResponse | None


class IntelligenceResponse(BaseModel):
    solicitation: SolicitationResponse
    profile: ProfileResponse | None
    rankings: list[AlignmentResponse]
    assessment: AssessmentResponse | None


class EvidenceSummary(BaseModel):
    document_count: int
    signal_count: int


class CapturePackageContent(BaseModel):
    solicitation: SolicitationResponse
    profile: ProfileResponse
    contractor_rankings: list[AlignmentResponse]
    target_assessment: AssessmentResponse | None
    evidence_summary: EvidenceSummary


class CapturePackageResponse(BaseModel):
    id: str
    solicitation_id: str
    version: int
    is_current: bool
    status: CapturePackageStatus
    content: CapturePackageContent
    reviewed_by: str | None
    reviewed_at: str | None
    review_notes: str | None
    knowledge_vault_document_id: str | None
    created_at: str | None


class CapturePackageListResponse(BaseModel):
    items: list[CapturePackageResponse]


class PublishToVaultResponse(BaseModel):
    capture_package_id: str
    knowledge_vault_document_id: str
    task_id: str
    status: str


class SeedSampleResponse(BaseModel):
    solicitation_id: str
    pipeline_status: str
    signal_count: int | None = None
    profile: ProfileResponse | None = None
    rankings: list[AlignmentResponse] | None = None
    assessment: AssessmentResponse | None = None


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
        "task_order_fair_opportunity": profile.task_order_fair_opportunity,
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


@router.get("/solicitations", response_model=SolicitationListResponse)
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


@router.post("/solicitations/{sol_id}/extract-signals", response_model=ExtractSignalsResponse)
async def extract_signals(sol_id: uuid.UUID, user: Auth, db: DB) -> dict:
    sol = await _get_solicitation(db, sol_id, user.tenant_id)
    signals = await WPHService(db).extract_signals(sol, user.tenant_id)
    return {"signal_count": len(signals), "pipeline_status": sol.pipeline_status}


@router.get("/solicitations/{sol_id}/signals", response_model=SignalListResponse)
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


@router.post("/solicitations/{sol_id}/generate-profile", response_model=ProfileResponse)
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

        pdc = await service.load_profile_dataclass(profile, user.tenant_id, sol.rule_pack)
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


@router.get("/solicitations/{sol_id}/profile", response_model=ProfileResponse)
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


@router.post("/solicitations/{sol_id}/align", response_model=AlignRunResponse)
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


@router.get("/solicitations/{sol_id}/alignments", response_model=AlignRunResponse)
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


@router.get("/solicitations/{sol_id}/alignments/{contractor_id}", response_model=AlignmentResponse)
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


@router.post("/solicitations/{sol_id}/assess", response_model=AssessmentResponse)
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


@router.get("/solicitations/{sol_id}/assessment", response_model=AssessmentResponse)
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


@router.post("/solicitations/{sol_id}/run", response_model=PipelineRunResponse)
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

        pdc = await service.load_profile_dataclass(profile, user.tenant_id, sol.rule_pack)
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


@router.get("/solicitations/{sol_id}/intelligence", response_model=IntelligenceResponse)
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


# ── Capture Manager Package ───────────────────────────────────────────────────────


class ApprovePackageRequest(BaseModel):
    review_notes: str | None = None


def _capture_package_payload(p: WPHCapturePackage) -> dict:
    return {
        "id": str(p.id),
        "solicitation_id": str(p.solicitation_id),
        "version": p.version,
        "is_current": p.is_current,
        "status": p.status,
        "content": p.content,
        "reviewed_by": str(p.reviewed_by) if p.reviewed_by else None,
        "reviewed_at": p.reviewed_at.isoformat() if p.reviewed_at else None,
        "review_notes": p.review_notes,
        "knowledge_vault_document_id": (
            str(p.knowledge_vault_document_id) if p.knowledge_vault_document_id else None
        ),
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


async def _compile_capture_package_content(
    db: Any,
    sol: WPHSolicitation,
    profile: WPHProfile,
    tenant_id: uuid.UUID,
    target_contractor_id: uuid.UUID | None,
) -> tuple[dict[str, Any], WPHAssessment | None]:
    """Compile the profile, every ranked contractor, and the target
    contractor's assessment into one executive-facing brief. Deliberately no
    new AI call here — this only reads already-computed, already-evidence-
    checked results rather than re-narrating them (which would add
    fabrication risk without adding information)."""
    rankings = (
        (
            await db.execute(
                select(WPHAlignment)
                .where(WPHAlignment.profile_id == profile.id, WPHAlignment.tenant_id == tenant_id)
                .order_by(WPHAlignment.rank.asc())
            )
        )
        .scalars()
        .all()
    )

    assess_q = select(WPHAssessment).where(
        WPHAssessment.solicitation_id == sol.id, WPHAssessment.tenant_id == tenant_id
    )
    if target_contractor_id:
        assess_q = assess_q.where(WPHAssessment.target_contractor_id == target_contractor_id)
    assessment = (
        await db.execute(assess_q.order_by(WPHAssessment.created_at.desc()).limit(1))
    ).scalar_one_or_none()

    doc_count = (
        await db.execute(
            select(func.count(WPHEvidenceDocument.id)).where(
                WPHEvidenceDocument.solicitation_id == sol.id,
                WPHEvidenceDocument.tenant_id == tenant_id,
            )
        )
    ).scalar_one()
    signal_count = (
        await db.execute(
            select(func.count(WPHSignal.id)).where(
                WPHSignal.solicitation_id == sol.id, WPHSignal.tenant_id == tenant_id
            )
        )
    ).scalar_one()

    content = {
        "solicitation": SolicitationResponse.model_validate(sol).model_dump(mode="json"),
        "profile": await _profile_payload(db, profile, tenant_id),
        "contractor_rankings": [_alignment_payload(a) for a in rankings],
        "target_assessment": _assessment_payload(assessment) if assessment else None,
        "evidence_summary": {"document_count": doc_count, "signal_count": signal_count},
    }
    return content, assessment


def _render_capture_package_text(content: dict[str, Any]) -> str:
    """Flatten the compiled capture package into readable plain text for
    Knowledge Vault ingestion/vectorization."""
    sol = content.get("solicitation") or {}
    profile = content.get("profile") or {}
    assessment = content.get("target_assessment") or {}
    rankings = content.get("contractor_rankings") or []
    evidence = content.get("evidence_summary") or {}

    lines = [
        f"CAPTURE PACKAGE — {sol.get('title', 'Untitled')}",
        f"Solicitation Number: {sol.get('solicitation_number', 'N/A')}",
        f"Agency: {sol.get('agency', 'N/A')}",
        "",
        "== WINNING PROFILE SUMMARY ==",
        profile.get("summary") or "",
        "",
        "== TARGET CONTRACTOR ASSESSMENT ==",
        f"Recommendation: {assessment.get('recommendation', 'N/A')}",
        f"PDQ Score: {assessment.get('pdq_score', 'N/A')}",
        assessment.get("executive_summary") or "",
        "",
        "== CONTRACTOR RANKINGS ==",
    ]
    for r in rankings:
        lines.append(
            f"#{r.get('rank')} {r.get('contractor_name')} — {r.get('overall_alignment_score')}"
        )
    lines += [
        "",
        "== EVIDENCE PACKAGE ==",
        f"Documents: {evidence.get('document_count', 0)}, "
        f"Signals: {evidence.get('signal_count', 0)}",
    ]
    return "\n".join(lines)


@router.post("/solicitations/{sol_id}/capture-package", response_model=CapturePackageResponse)
async def generate_capture_package(
    sol_id: uuid.UUID,
    user: Auth,
    db: DB,
    target_contractor_id: uuid.UUID | None = Query(None),
) -> dict:
    """Build (or rebuild) the capture package as a new draft version. Requires
    a current profile and at least one assessment — run the pipeline first."""
    sol = await _get_solicitation(db, sol_id, user.tenant_id)
    profile = await _current_profile(db, sol_id, user.tenant_id)

    content, assessment = await _compile_capture_package_content(
        db, sol, profile, user.tenant_id, target_contractor_id
    )
    if assessment is None:
        raise HTTPException(
            status_code=409,
            detail="No assessment yet. Run alignment + assessment (or the full pipeline) first.",
        )

    prior = (
        await db.execute(
            select(WPHCapturePackage).where(
                WPHCapturePackage.solicitation_id == sol_id,
                WPHCapturePackage.tenant_id == user.tenant_id,
                WPHCapturePackage.is_current.is_(True),
            )
        )
    ).scalar_one_or_none()
    if prior:
        prior.is_current = False
    next_version = (prior.version + 1) if prior else 1

    package = WPHCapturePackage(
        tenant_id=user.tenant_id,
        solicitation_id=sol_id,
        profile_id=profile.id,
        assessment_id=assessment.id,
        version=next_version,
        is_current=True,
        status=CapturePackageStatus.DRAFT.value,
        content=content,
    )
    db.add(package)
    await db.commit()
    await db.refresh(package)
    return _capture_package_payload(package)


@router.get("/solicitations/{sol_id}/capture-package", response_model=CapturePackageResponse)
async def get_capture_package(sol_id: uuid.UUID, user: Auth, db: DB) -> dict:
    await _get_solicitation(db, sol_id, user.tenant_id)
    package = (
        await db.execute(
            select(WPHCapturePackage).where(
                WPHCapturePackage.solicitation_id == sol_id,
                WPHCapturePackage.tenant_id == user.tenant_id,
                WPHCapturePackage.is_current.is_(True),
            )
        )
    ).scalar_one_or_none()
    if not package:
        raise HTTPException(status_code=404, detail="No capture package yet. Generate one first.")
    return _capture_package_payload(package)


@router.get(
    "/solicitations/{sol_id}/capture-package/history", response_model=CapturePackageListResponse
)
async def list_capture_package_versions(sol_id: uuid.UUID, user: Auth, db: DB) -> dict:
    await _get_solicitation(db, sol_id, user.tenant_id)
    rows = (
        (
            await db.execute(
                select(WPHCapturePackage)
                .where(
                    WPHCapturePackage.solicitation_id == sol_id,
                    WPHCapturePackage.tenant_id == user.tenant_id,
                )
                .order_by(WPHCapturePackage.version.desc())
            )
        )
        .scalars()
        .all()
    )
    return {"items": [_capture_package_payload(p) for p in rows]}


@router.post(
    "/solicitations/{sol_id}/capture-package/approve", response_model=CapturePackageResponse
)
async def approve_capture_package(
    sol_id: uuid.UUID, payload: ApprovePackageRequest, user: Auth, db: DB
) -> dict:
    await _get_solicitation(db, sol_id, user.tenant_id)
    package = (
        await db.execute(
            select(WPHCapturePackage).where(
                WPHCapturePackage.solicitation_id == sol_id,
                WPHCapturePackage.tenant_id == user.tenant_id,
                WPHCapturePackage.is_current.is_(True),
            )
        )
    ).scalar_one_or_none()
    if not package:
        raise HTTPException(status_code=404, detail="No capture package yet. Generate one first.")

    package.status = CapturePackageStatus.APPROVED.value
    package.reviewed_by = user.user_id
    package.reviewed_at = datetime.now(UTC)
    package.review_notes = payload.review_notes
    await db.commit()
    await db.refresh(package)
    return _capture_package_payload(package)


@router.post(
    "/solicitations/{sol_id}/capture-package/publish-to-vault",
    response_model=PublishToVaultResponse,
)
async def publish_capture_package_to_vault(sol_id: uuid.UUID, user: Auth, db: DB) -> dict:
    """Copies an approved package into Knowledge Vault as a searchable
    document — a separate, explicit action from approval, not automatic."""
    await _get_solicitation(db, sol_id, user.tenant_id)
    package = (
        await db.execute(
            select(WPHCapturePackage).where(
                WPHCapturePackage.solicitation_id == sol_id,
                WPHCapturePackage.tenant_id == user.tenant_id,
                WPHCapturePackage.is_current.is_(True),
            )
        )
    ).scalar_one_or_none()
    if not package:
        raise HTTPException(status_code=404, detail="No capture package yet. Generate one first.")
    if package.status != CapturePackageStatus.APPROVED.value:
        raise HTTPException(
            status_code=409, detail="Capture package must be approved before publishing."
        )

    from cios.models.knowledge_vault import KnowledgeDocument
    from cios.tasks.ingestion import ingest_document

    sol_title = (package.content.get("solicitation") or {}).get("title", "Untitled")
    text = _render_capture_package_text(package.content)

    doc = KnowledgeDocument(
        tenant_id=user.tenant_id,
        title=f"Capture Package — {sol_title}",
        document_type="capture_package",
        description="Executive capture manager package (published from Winning Profile).",
        file_name=f"capture-package-{sol_id}.txt",
        file_size_bytes=len(text.encode()),
        mime_type="text/plain",
        uploaded_by=user.user_id,
        vectorization_status="pending",
        tags=["capture-package", "winning-profile"],
    )
    db.add(doc)
    await db.flush()

    task = ingest_document.delay(str(user.tenant_id), str(doc.id), text.encode(), "text/plain")

    package.knowledge_vault_document_id = doc.id
    await db.commit()

    return {
        "capture_package_id": str(package.id),
        "knowledge_vault_document_id": str(doc.id),
        "task_id": task.id,
        "status": "queued",
    }


# ── Sample dataset seeding ───────────────────────────────────────────────────────


@router.post("/sample", response_model=SeedSampleResponse, status_code=status.HTTP_201_CREATED)
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
