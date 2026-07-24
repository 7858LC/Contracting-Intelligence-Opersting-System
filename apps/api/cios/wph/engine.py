"""Winning Profile Hypothesis™ Engine — pure orchestrator.

Ties the evidence-fusion pipeline together over plain dataclasses so the whole
capability can be exercised (and unit-tested) end-to-end without a database or
network. The service/task layer maps ORM rows to these inputs and persists the
outputs.

    docs → signals → profile → alignments → ranking → gaps → closures → assessment
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .alignment import AlignmentScorer, GapCloser, rank_alignments
from .extraction import SignalExtractor
from .inference import AttributeInferenceEngine
from .pdq import PDQEngine
from .schemas import (
    Assessment,
    ContractorAlignment,
    ContractorProfile,
    EvidenceDoc,
    ExtractedSignal,
    WinningProfile,
)


@dataclass
class IntelligenceResult:
    """The complete pre-award intelligence output for one solicitation."""

    signals: list[ExtractedSignal] = field(default_factory=list)
    profile: WinningProfile | None = None
    alignments: list[ContractorAlignment] = field(default_factory=list)
    assessment: Assessment | None = None

    def to_dict(self) -> dict:
        return {
            "signal_count": len(self.signals),
            "signals": [s.to_dict() for s in self.signals],
            "profile": self.profile.to_dict() if self.profile else None,
            "alignments": [a.to_dict() for a in self.alignments],
            "assessment": self.assessment.to_dict() if self.assessment else None,
        }


class WinningProfileEngine:
    """Facade over the four fusion stages. Stateless and deterministic."""

    def __init__(self) -> None:
        self._extractor = SignalExtractor()
        self._inference = AttributeInferenceEngine()
        self._scorer = AlignmentScorer()
        self._closer = GapCloser()
        self._pdq = PDQEngine()

    # ── Individual stages ────────────────────────────────────────────────────────

    def extract_signals(self, docs: list[EvidenceDoc]) -> list[ExtractedSignal]:
        return self._extractor.extract(docs)

    def build_profile(self, signals: list[ExtractedSignal]) -> WinningProfile:
        return self._inference.build_profile(signals)

    def align_contractor(
        self, profile: WinningProfile, contractor: ContractorProfile
    ) -> ContractorAlignment:
        alignment = self._scorer.score(profile, contractor)
        alignment.gap_closures = self._closer.recommend(alignment.gaps)
        return alignment

    def align_and_rank(
        self, profile: WinningProfile, contractors: list[ContractorProfile]
    ) -> list[ContractorAlignment]:
        alignments = [self.align_contractor(profile, c) for c in contractors]
        return rank_alignments(alignments)

    def assess(
        self,
        profile: WinningProfile,
        target: ContractorAlignment,
        ranked: list[ContractorAlignment],
    ) -> Assessment:
        return self._pdq.assess(profile, target, ranked, target.gap_closures)

    # ── Full vertical slice ──────────────────────────────────────────────────────

    def run(
        self,
        docs: list[EvidenceDoc],
        contractors: list[ContractorProfile] | None = None,
        target_name: str | None = None,
    ) -> IntelligenceResult:
        """Run the complete pre-award pipeline end to end."""
        signals = self.extract_signals(docs)
        profile = self.build_profile(signals)
        result = IntelligenceResult(signals=signals, profile=profile)

        if not contractors:
            return result

        ranked = self.align_and_rank(profile, contractors)
        result.alignments = ranked

        # Choose the assessment target: explicit name → the `is_self` contractor →
        # the top-ranked candidate.
        target = None
        if target_name:
            target = next((a for a in ranked if a.contractor_name == target_name), None)
        if target is None:
            self_names = {c.name for c in contractors if c.is_self}
            target = next((a for a in ranked if a.contractor_name in self_names), None)
        if target is None and ranked:
            target = ranked[0]

        if target is not None:
            result.assessment = self.assess(profile, target, ranked)

        return result
