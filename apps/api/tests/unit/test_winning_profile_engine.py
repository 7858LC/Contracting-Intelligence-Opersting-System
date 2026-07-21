"""Tests for the Winning Profile Hypothesis™ evidence-fusion engine.

Pure-domain tests — no database or network required. They verify the engine is
explainable, deterministic, and behaves correctly across the full vertical slice.
"""

from __future__ import annotations

import pytest

from cios.wph import (
    ContractorProfile,
    EvidenceDoc,
    WinningProfileEngine,
)
from cios.wph.constants import PursuitRecommendation, SignalCategory
from cios.wph.extraction import SignalExtractor
from cios.wph.inference import AttributeInferenceEngine
from cios.wph.sample_data import SAMPLE_CONTRACTORS, SAMPLE_DOCUMENTS


@pytest.fixture
def engine() -> WinningProfileEngine:
    return WinningProfileEngine()


# ── Signal extraction ────────────────────────────────────────────────────────────


def test_extraction_classifies_security_signal():
    doc = EvidenceDoc(
        document_type="performance_work_statement",
        title="PWS",
        content="All personnel must hold an active Secret clearance and maintain CMMC Level 2.",
    )
    signals = SignalExtractor().extract_from_document(doc)
    categories = {s.category for s in signals}
    assert SignalCategory.SECURITY_REQUIREMENT.value in categories
    sec = next(s for s in signals if s.category == SignalCategory.SECURITY_REQUIREMENT.value)
    # Evidence is preserved verbatim and traceable to its source.
    assert "clearance" in sec.evidence_text.lower()
    assert sec.source_document_type == "performance_work_statement"
    assert sec.strength > 0 and sec.confidence > 0


def test_extraction_is_deterministic():
    ext = SignalExtractor()
    first = ext.extract(SAMPLE_DOCUMENTS)
    second = ext.extract(SAMPLE_DOCUMENTS)
    assert [s.category for s in first] == [s.category for s in second]
    assert [s.evidence_text for s in first] == [s.evidence_text for s in second]


def test_high_value_documents_carry_more_weight():
    text = "Past performance is significantly more important than price."
    section_m = SignalExtractor().extract_from_document(
        EvidenceDoc(document_type="section_m", title="M", content=text)
    )
    attachment = SignalExtractor().extract_from_document(
        EvidenceDoc(document_type="attachment", title="A", content=text)
    )
    pp = SignalCategory.PAST_PERFORMANCE_EMPHASIS.value
    m_pp = next(s for s in section_m if s.category == pp)
    a_pp = next(s for s in attachment if s.category == pp)
    assert m_pp.strength > a_pp.strength


def test_empty_document_yields_no_signals():
    assert (
        SignalExtractor().extract_from_document(
            EvidenceDoc(document_type="other", title="x", content="")
        )
        == []
    )


# ── Attribute inference / weighting ──────────────────────────────────────────────


def test_importance_weights_normalize_to_100():
    signals = SignalExtractor().extract(SAMPLE_DOCUMENTS)
    profile = AttributeInferenceEngine().build_profile(signals)
    total = sum(a.importance_weight for a in profile.attributes)
    assert profile.attributes, "expected inferred attributes"
    assert total == pytest.approx(100.0, abs=0.5)


def test_attributes_sorted_by_importance_descending():
    signals = SignalExtractor().extract(SAMPLE_DOCUMENTS)
    profile = AttributeInferenceEngine().build_profile(signals)
    weights = [a.importance_weight for a in profile.attributes]
    assert weights == sorted(weights, reverse=True)


def test_every_attribute_is_traceable_to_evidence():
    signals = SignalExtractor().extract(SAMPLE_DOCUMENTS)
    profile = AttributeInferenceEngine().build_profile(signals)
    for attr in profile.attributes:
        assert attr.supporting_evidence, f"{attr.name} has no supporting evidence"
        assert attr.evidence_source_refs
        assert attr.reasoning
        assert 0 <= attr.evidence_confidence <= 100
        assert attr.confidence_level in ("high", "medium", "low")


def test_transition_and_past_performance_are_top_drivers():
    """Section M ranks past performance highly and Q&A calls transition a 'dominant
    discriminator' — both should surface as leading attributes."""
    signals = SignalExtractor().extract(SAMPLE_DOCUMENTS)
    profile = AttributeInferenceEngine().build_profile(signals)
    top_names = [a.name for a in profile.attributes[:4]]
    assert any("Past Performance" in n for n in top_names)
    assert any("Transition" in n for n in top_names)


def test_no_signals_yields_empty_profile_with_guidance():
    profile = AttributeInferenceEngine().build_profile([])
    assert profile.attributes == []
    assert profile.overall_confidence == 0.0
    assert "Insufficient evidence" in profile.summary


# ── Shaping risk ─────────────────────────────────────────────────────────────────


def test_extraction_classifies_shaping_risk_signal():
    doc = EvidenceDoc(
        document_type="section_m",
        title="Section M",
        content=(
            "This is a sole source justification for other than full and open "
            "competition; salient characteristics require a brand name or equal match."
        ),
    )
    signals = SignalExtractor().extract_from_document(doc)
    categories = {s.category for s in signals}
    assert SignalCategory.SHAPING_RISK.value in categories


def test_shaping_risk_is_surfaced_but_not_diluted_into_attributes():
    """A narrowly-tailored requirement should raise a distinct flag, not quietly
    become another weighted attribute averaged in with everything else."""
    docs = [
        EvidenceDoc(
            document_type="section_m",
            title="Section M",
            content=(
                "This is a sole source justification for other than full and open "
                "competition since only one responsible source can meet the specific "
                "make and model required. Salient characteristics include "
                "compatibility with the existing proprietary system. This is a brand "
                "name or equal requirement. Past performance and technical approach "
                "will also be evaluated."
            ),
        )
    ]
    signals = SignalExtractor().extract(docs)
    profile = AttributeInferenceEngine().build_profile(signals)

    assert profile.shaping_risk.risk_level == "high"
    assert profile.shaping_risk.signal_count >= 3
    assert profile.shaping_risk.supporting_evidence
    assert profile.shaping_risk.source_refs == ["section_m"]

    # No attribute in the normal weighted list should be driven solely by
    # shaping-risk language — it must not affect importance_weight/overall_confidence.
    for attr in profile.attributes:
        assert SignalCategory.SHAPING_RISK.value not in attr.signal_categories


def test_no_shaping_language_yields_none_risk_level():
    signals = SignalExtractor().extract(SAMPLE_DOCUMENTS)
    profile = AttributeInferenceEngine().build_profile(signals)
    assert profile.shaping_risk.risk_level == "none"
    assert profile.shaping_risk.signal_count == 0
    assert profile.shaping_risk.narrative


# ── Alignment, ranking, gaps, closures ───────────────────────────────────────────


def test_full_pipeline_ranks_self_first(engine: WinningProfileEngine):
    result = engine.run(SAMPLE_DOCUMENTS, SAMPLE_CONTRACTORS)
    assert result.profile is not None
    assert result.alignments
    # The self/SDVOSB/cleared firm should out-rank the non-set-aside large firm.
    ranked_names = [a.contractor_name for a in result.alignments]
    apex_rank = next(
        a.rank for a in result.alignments if a.contractor_name == "Apex Digital Partners"
    )
    meridian_rank = next(
        a.rank for a in result.alignments if a.contractor_name == "Meridian Federal Solutions"
    )
    assert meridian_rank < apex_rank
    assert ranked_names[0] in ("Meridian Federal Solutions", "LegacyGov Systems Inc.")


def test_ranks_are_contiguous_and_unique(engine: WinningProfileEngine):
    result = engine.run(SAMPLE_DOCUMENTS, SAMPLE_CONTRACTORS)
    ranks = sorted(a.rank for a in result.alignments)
    assert ranks == list(range(1, len(result.alignments) + 1))


def test_alignment_contributions_sum_to_overall(engine: WinningProfileEngine):
    profile = engine.build_profile(engine.extract_signals(SAMPLE_DOCUMENTS))
    alignment = engine.align_contractor(profile, SAMPLE_CONTRACTORS[0])
    contribution_sum = sum(a.contribution for a in alignment.attribute_alignments)
    assert alignment.overall_alignment_score == pytest.approx(round(contribution_sum, 2), abs=0.5)


def test_ineligible_large_firm_has_setaside_gap(engine: WinningProfileEngine):
    profile = engine.build_profile(engine.extract_signals(SAMPLE_DOCUMENTS))
    apex = next(c for c in SAMPLE_CONTRACTORS if c.name == "Apex Digital Partners")
    alignment = engine.align_contractor(profile, apex)
    gap_categories = {g.category for g in alignment.gaps}
    assert "eligibility" in gap_categories or "security" in gap_categories
    # Every gap must carry a closure recommendation.
    assert len(alignment.gap_closures) == len(alignment.gaps)
    for closure in alignment.gap_closures:
        assert closure.recommendation
        assert closure.timeline_months >= 1
        assert closure.feasibility in ("high", "medium", "low")


def test_gap_severity_reflects_importance_and_size(engine: WinningProfileEngine):
    profile = engine.build_profile(engine.extract_signals(SAMPLE_DOCUMENTS))
    weak = ContractorProfile(
        name="No-Cap Firm", capability_text="general services", set_asides=[], clearances=[]
    )
    alignment = engine.align_contractor(profile, weak)
    assert alignment.gaps
    assert any(g.severity == "critical" for g in alignment.gaps)


# ── Executive assessment / PDQ ───────────────────────────────────────────────────


def test_assessment_recommends_bid_for_strong_target(engine: WinningProfileEngine):
    result = engine.run(
        SAMPLE_DOCUMENTS, SAMPLE_CONTRACTORS, target_name="Meridian Federal Solutions"
    )
    assert result.assessment is not None
    a = result.assessment
    assert a.recommendation in (
        PursuitRecommendation.BID.value,
        PursuitRecommendation.CONDITIONAL_BID.value,
    )
    assert 0 <= a.pdq_score <= 100
    assert a.candidate_pool_size == len(SAMPLE_CONTRACTORS)
    assert a.executive_summary
    assert a.assumptions  # never presented without stated assumptions


def test_assessment_no_bids_weak_target(engine: WinningProfileEngine):
    weak = ContractorProfile(
        name="Generalist LLC", capability_text="general consulting", set_asides=[], clearances=[]
    )
    result = engine.run(SAMPLE_DOCUMENTS, [weak], target_name="Generalist LLC")
    assert result.assessment is not None
    assert result.assessment.recommendation in (
        PursuitRecommendation.NO_BID.value,
        PursuitRecommendation.CONDITIONAL_BID.value,
        PursuitRecommendation.MONITOR.value,
    )


def test_monitor_when_evidence_is_thin(engine: WinningProfileEngine):
    thin = [
        EvidenceDoc(
            document_type="rfi",
            title="RFI",
            content="The agency seeks information about cloud services.",
        )
    ]
    contractor = ContractorProfile(name="Cloud Co", capability_text="cloud services")
    result = engine.run(thin, [contractor], target_name="Cloud Co")
    assert result.assessment is not None
    # Low evidence strength should not yield an over-confident bid/no-bid.
    assert result.profile.evidence_strength < 60


def test_pipeline_without_contractors_still_produces_profile(engine: WinningProfileEngine):
    result = engine.run(SAMPLE_DOCUMENTS)
    assert result.profile is not None
    assert result.alignments == []
    assert result.assessment is None


def test_result_serialization_is_json_safe(engine: WinningProfileEngine):
    import json

    result = engine.run(SAMPLE_DOCUMENTS, SAMPLE_CONTRACTORS)
    payload = result.to_dict()
    # Round-trips through JSON without error.
    reloaded = json.loads(json.dumps(payload))
    assert reloaded["assessment"]["recommendation"]
    assert "shaping_risk" in reloaded["profile"]
