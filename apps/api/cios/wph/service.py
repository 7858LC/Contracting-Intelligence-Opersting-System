"""Winning Profile Hypothesis™ persistence service.

Bridges the pure evidence-fusion engine (``cios.wph.engine``) and the ORM. Maps
DB rows to engine dataclasses, runs a pipeline stage, and persists the results —
keeping API endpoints and Celery tasks thin. All queries are tenant-scoped; RLS
provides defense in depth.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

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

from .constants import PipelineStatus
from .engine import WinningProfileEngine
from .schemas import ContractorProfile, EvidenceDoc, WinningProfile


def _to_evidence_doc(doc: WPHEvidenceDocument) -> EvidenceDoc:
    return EvidenceDoc(
        document_type=doc.document_type,
        title=doc.title,
        content=doc.content or "",
        source_ref=doc.source_ref or doc.title,
        document_id=str(doc.id),
    )


def _to_contractor_profile(c: WPHContractor) -> ContractorProfile:
    caps: dict[str, float] = {}
    cap_names: list[str] = []
    for item in c.capabilities or []:
        if isinstance(item, dict) and "name" in item:
            name = str(item["name"])
            cap_names.append(name)
            if item.get("level") is not None:
                try:
                    caps[name.lower()] = float(item["level"])
                except (TypeError, ValueError):
                    pass
    capability_text = " ".join(
        [
            c.description or "",
            " ".join(cap_names),
            " ".join(str(x) for x in (c.certifications or [])),
            " ".join(str(x) for x in (c.clearances or [])),
        ]
    )
    return ContractorProfile(
        name=c.name,
        description=c.description or "",
        is_self=bool(c.is_self),
        is_incumbent=bool(c.is_incumbent),
        business_size=c.business_size,
        certifications=list(c.certifications or []),
        set_asides=list(c.set_asides or []),
        clearances=list(c.clearances or []),
        capabilities=caps,
        capability_text=capability_text,
        past_performance=list(c.past_performance or []),
    )


class WPHService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.engine = WinningProfileEngine()

    # ── Signal extraction ────────────────────────────────────────────────────────

    async def extract_signals(
        self, solicitation: WPHSolicitation, tenant_id: uuid.UUID
    ) -> list[WPHSignal]:
        docs_rows = (
            (
                await self.db.execute(
                    select(WPHEvidenceDocument).where(
                        WPHEvidenceDocument.solicitation_id == solicitation.id,
                        WPHEvidenceDocument.tenant_id == tenant_id,
                    )
                )
            )
            .scalars()
            .all()
        )

        # Replace prior signals — extraction is deterministic and idempotent.
        await self.db.execute(
            WPHSignal.__table__.delete().where(
                WPHSignal.solicitation_id == solicitation.id,
                WPHSignal.tenant_id == tenant_id,
            )
        )

        docs = [_to_evidence_doc(d) for d in docs_rows]
        extracted = self.engine.extract_signals(docs)

        rows: list[WPHSignal] = []
        for sig in extracted:
            row = WPHSignal(
                tenant_id=tenant_id,
                solicitation_id=solicitation.id,
                document_id=uuid.UUID(sig.document_id) if sig.document_id else None,
                category=sig.category,
                evidence_text=sig.evidence_text,
                interpretation=sig.interpretation,
                strength=sig.strength,
                confidence=sig.confidence,
                source_document_type=sig.source_document_type,
                source_ref=sig.source_ref,
                keywords=sig.keywords,
                raw={},
            )
            self.db.add(row)
            rows.append(row)

        for d in docs_rows:
            d.is_extracted = True
        solicitation.signal_count = len(rows)
        solicitation.pipeline_status = PipelineStatus.SIGNALS_EXTRACTED.value
        await self.db.commit()
        return rows

    # ── Profile generation ───────────────────────────────────────────────────────

    async def generate_profile(
        self,
        solicitation: WPHSolicitation,
        tenant_id: uuid.UUID,
        model_used: str | None = None,
        narrative: str | None = None,
    ) -> WPHProfile:
        signal_rows = (
            (
                await self.db.execute(
                    select(WPHSignal).where(
                        WPHSignal.solicitation_id == solicitation.id,
                        WPHSignal.tenant_id == tenant_id,
                    )
                )
            )
            .scalars()
            .all()
        )

        from .schemas import ExtractedSignal

        eng_signals = [
            ExtractedSignal(
                category=s.category,
                evidence_text=s.evidence_text,
                interpretation=s.interpretation or "",
                strength=s.strength,
                confidence=s.confidence,
                source_document_type=s.source_document_type or "other",
                source_ref=s.source_ref,
                keywords=list(s.keywords or []),
                document_id=str(s.document_id) if s.document_id else None,
            )
            for s in signal_rows
        ]
        profile = self.engine.build_profile(eng_signals)

        # Supersede any prior current profile; bump version.
        await self.db.execute(
            update(WPHProfile)
            .where(
                WPHProfile.solicitation_id == solicitation.id,
                WPHProfile.tenant_id == tenant_id,
                WPHProfile.is_current.is_(True),
            )
            .values(is_current=False)
        )
        prior = (
            await self.db.execute(
                select(WPHProfile.version)
                .where(
                    WPHProfile.solicitation_id == solicitation.id,
                    WPHProfile.tenant_id == tenant_id,
                )
                .order_by(WPHProfile.version.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        version = (prior or 0) + 1

        row = WPHProfile(
            tenant_id=tenant_id,
            solicitation_id=solicitation.id,
            version=version,
            is_current=True,
            summary=profile.summary,
            narrative=narrative,
            overall_confidence=profile.overall_confidence,
            evidence_strength=profile.evidence_strength,
            attribute_count=len(profile.attributes),
            unknown_factors=profile.unknown_factors,
            status="generated",
            model_used=model_used,
            confidence_score=profile.overall_confidence / 100.0,
            ai_model_version=model_used,
        )
        self.db.add(row)
        await self.db.flush()

        for attr in profile.attributes:
            self.db.add(
                WPHProfileAttribute(
                    tenant_id=tenant_id,
                    profile_id=row.id,
                    name=attr.name,
                    category=attr.category,
                    description=attr.description,
                    importance_weight=attr.importance_weight,
                    evidence_confidence=attr.evidence_confidence,
                    confidence_level=attr.confidence_level,
                    required_level=attr.required_level,
                    supporting_evidence=attr.supporting_evidence,
                    evidence_source_refs=attr.evidence_source_refs,
                    signal_ids=[],
                    reasoning=attr.reasoning,
                    unknown_factors=attr.unknown_factors,
                )
            )

        solicitation.pipeline_status = PipelineStatus.PROFILE_GENERATED.value
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def load_profile_dataclass(
        self, profile_row: WPHProfile, tenant_id: uuid.UUID
    ) -> WinningProfile:
        from .schemas import InferredAttribute

        attr_rows = (
            (
                await self.db.execute(
                    select(WPHProfileAttribute)
                    .where(
                        WPHProfileAttribute.profile_id == profile_row.id,
                        WPHProfileAttribute.tenant_id == tenant_id,
                    )
                    .order_by(WPHProfileAttribute.importance_weight.desc())
                )
            )
            .scalars()
            .all()
        )
        attributes = [
            InferredAttribute(
                key="",
                name=a.name,
                category=a.category,
                description=a.description or "",
                importance_weight=a.importance_weight,
                evidence_confidence=a.evidence_confidence,
                confidence_level=a.confidence_level,
                required_level=a.required_level,
                supporting_evidence=list(a.supporting_evidence or []),
                evidence_source_refs=list(a.evidence_source_refs or []),
                reasoning=a.reasoning or "",
                unknown_factors=list(a.unknown_factors or []),
                signal_categories=[],
            )
            for a in attr_rows
        ]
        # Re-map attribute keys from the library by name for contractor matching.
        from .taxonomy import ATTRIBUTE_LIBRARY

        by_name = {x.name: x.key for x in ATTRIBUTE_LIBRARY}
        for a in attributes:
            a.key = by_name.get(a.name, a.name.lower().replace(" ", "_"))
        return WinningProfile(
            summary=profile_row.summary or "",
            overall_confidence=profile_row.overall_confidence,
            evidence_strength=profile_row.evidence_strength,
            attributes=attributes,
            unknown_factors=list(profile_row.unknown_factors or []),
        )

    # ── Alignment + ranking ──────────────────────────────────────────────────────

    async def align_contractors(
        self,
        solicitation: WPHSolicitation,
        profile_row: WPHProfile,
        tenant_id: uuid.UUID,
        contractor_ids: list[uuid.UUID] | None = None,
    ) -> list[WPHAlignment]:
        q = select(WPHContractor).where(WPHContractor.tenant_id == tenant_id)
        if contractor_ids:
            q = q.where(WPHContractor.id.in_(contractor_ids))
        contractor_rows = (await self.db.execute(q)).scalars().all()
        if not contractor_rows:
            return []

        profile = await self.load_profile_dataclass(profile_row, tenant_id)
        id_by_name = {c.name: c.id for c in contractor_rows}
        contractors = [_to_contractor_profile(c) for c in contractor_rows]
        ranked = self.engine.align_and_rank(profile, contractors)

        # Replace prior alignments for this profile.
        await self.db.execute(
            WPHAlignment.__table__.delete().where(
                WPHAlignment.profile_id == profile_row.id,
                WPHAlignment.tenant_id == tenant_id,
            )
        )

        rows: list[WPHAlignment] = []
        for al in ranked:
            row = WPHAlignment(
                tenant_id=tenant_id,
                solicitation_id=solicitation.id,
                profile_id=profile_row.id,
                contractor_id=id_by_name[al.contractor_name],
                contractor_name=al.contractor_name,
                overall_alignment_score=al.overall_alignment_score,
                rank=al.rank,
                attribute_alignments=[a.to_dict() for a in al.attribute_alignments],
                gaps=[g.to_dict() for g in al.gaps],
                gap_closures=[c.to_dict() for c in al.gap_closures],
                strengths=al.strengths,
                weaknesses=al.weaknesses,
                summary=al.summary,
                confidence_score=al.overall_alignment_score / 100.0,
            )
            self.db.add(row)
            rows.append(row)

        solicitation.pipeline_status = PipelineStatus.ALIGNMENT_SCORED.value
        await self.db.commit()
        return rows

    # ── Executive assessment ─────────────────────────────────────────────────────

    async def assess(
        self,
        solicitation: WPHSolicitation,
        profile_row: WPHProfile,
        tenant_id: uuid.UUID,
        target_contractor_id: uuid.UUID | None = None,
        model_used: str | None = None,
        narrative: str | None = None,
    ) -> WPHAssessment | None:
        profile = await self.load_profile_dataclass(profile_row, tenant_id)

        align_rows = (
            (
                await self.db.execute(
                    select(WPHAlignment)
                    .where(
                        WPHAlignment.profile_id == profile_row.id,
                        WPHAlignment.tenant_id == tenant_id,
                    )
                    .order_by(WPHAlignment.rank.asc())
                )
            )
            .scalars()
            .all()
        )
        if not align_rows:
            return None

        # Rebuild engine dataclasses from persisted alignment rows.
        from .schemas import (
            AttributeAlignment,
            CapabilityGap,
            ContractorAlignment,
            GapClosure,
        )

        ranked: list[ContractorAlignment] = []
        for r in align_rows:
            # Persisted JSONB dicts mirror the dataclass fields exactly (see *.to_dict),
            # so they can be re-hydrated directly.
            ranked.append(
                ContractorAlignment(
                    contractor_name=r.contractor_name,
                    overall_alignment_score=r.overall_alignment_score,
                    rank=r.rank,
                    attribute_alignments=[
                        AttributeAlignment(**a) for a in (r.attribute_alignments or [])
                    ],
                    gaps=[CapabilityGap(**g) for g in (r.gaps or [])],
                    gap_closures=[GapClosure(**c) for c in (r.gap_closures or [])],
                    strengths=list(r.strengths or []),
                    weaknesses=list(r.weaknesses or []),
                    summary=r.summary or "",
                )
            )

        target = None
        target_name = None
        if target_contractor_id:
            tc = await self.db.get(WPHContractor, target_contractor_id)
            if tc:
                target_name = tc.name
                target = next((a for a in ranked if a.contractor_name == tc.name), None)
        if target is None:
            self_row = (
                await self.db.execute(
                    select(WPHContractor)
                    .where(WPHContractor.tenant_id == tenant_id, WPHContractor.is_self.is_(True))
                    .limit(1)
                )
            ).scalar_one_or_none()
            if self_row:
                target = next((a for a in ranked if a.contractor_name == self_row.name), None)
                target_name = self_row.name if target else target_name
        if target is None:
            target = ranked[0]
            target_name = target.contractor_name

        assessment = self.engine.assess(profile, target, ranked)

        # Resolve target contractor id.
        tid = target_contractor_id
        if tid is None:
            match = (
                await self.db.execute(
                    select(WPHContractor.id)
                    .where(
                        WPHContractor.tenant_id == tenant_id,
                        WPHContractor.name == target.contractor_name,
                    )
                    .limit(1)
                )
            ).scalar_one_or_none()
            tid = match

        row = WPHAssessment(
            tenant_id=tenant_id,
            solicitation_id=solicitation.id,
            profile_id=profile_row.id,
            target_contractor_id=tid,
            target_contractor_name=target.contractor_name,
            pdq_score=assessment.pdq_score,
            win_positioning_score=assessment.win_positioning_score,
            competitive_rank=assessment.competitive_rank,
            candidate_pool_size=assessment.candidate_pool_size,
            recommendation=assessment.recommendation,
            executive_summary=assessment.executive_summary,
            narrative=narrative,
            key_findings=assessment.key_findings,
            decision_factors=assessment.decision_factors,
            critical_gaps=assessment.critical_gaps,
            recommended_actions=assessment.recommended_actions,
            risks=assessment.risks,
            assumptions=assessment.assumptions,
            status="completed",
            model_used=model_used,
            confidence_score=assessment.pdq_score / 100.0,
            ai_model_version=model_used,
        )
        self.db.add(row)
        solicitation.pipeline_status = PipelineStatus.ASSESSED.value
        await self.db.commit()
        await self.db.refresh(row)
        return row
