"""Attribute Inference + Evidence Weighting — the fusion core.

Fuses classified procurement signals into a Winning Profile Hypothesis™:

    signals ──group by driving attribute──▶ candidate attributes
            ──weight by strength+evidentiary value──▶ importance_weight (Σ = 100)
            ──corroboration (count, source diversity, confidence)──▶ evidence_confidence
            ──strength──▶ required_level (the proficiency bar a candidate must clear)

Every attribute records the exact signals (evidence text + source) that produced
it, plus explicit unknown factors, so the hypothesis is fully explainable and
never presented as a black-box prediction.
"""

from __future__ import annotations

from collections import defaultdict

from .constants import ConfidenceLevel
from .schemas import ExtractedSignal, InferredAttribute, WinningProfile
from .taxonomy import ATTRIBUTE_LIBRARY, DOCUMENT_EVIDENCE_VALUE, AttributeDef

# Document types whose presence materially raises overall evidence strength.
_HIGH_VALUE_DOCS = {
    "section_m",
    "evaluation_criteria",
    "qa_response",
    "government_response",
    "historical_award",
    "section_l",
}

_MIN_ATTRIBUTE_IMPORTANCE = 2.0  # below this (post-normalization) an attribute is dropped


def _confidence_level(score: float) -> str:
    if score >= 75.0:
        return ConfidenceLevel.HIGH.value
    if score >= 50.0:
        return ConfidenceLevel.MEDIUM.value
    return ConfidenceLevel.LOW.value


class AttributeInferenceEngine:
    """Turns extracted signals into a ranked, weighted, explainable attribute set."""

    def infer(self, signals: list[ExtractedSignal]) -> list[InferredAttribute]:
        # Group signals under every attribute they drive.
        by_attr: dict[str, list[ExtractedSignal]] = defaultdict(list)
        attr_defs: dict[str, AttributeDef] = {}

        for attr in ATTRIBUTE_LIBRARY:
            driving = {s.value for s in attr.driving_signals}
            matched = [sig for sig in signals if sig.category in driving]
            if matched:
                by_attr[attr.key] = matched
                attr_defs[attr.key] = attr

        if not by_attr:
            return []

        # Raw importance = intrinsic prior + accumulated signal pressure.
        raw_importance: dict[str, float] = {}
        for key, sigs in by_attr.items():
            attr = attr_defs[key]
            pressure = sum(
                (sig.strength / 100.0) * DOCUMENT_EVIDENCE_VALUE.get(sig.source_document_type, 1.0)
                for sig in sigs
            )
            # Diminishing returns on repeated signals for the same attribute.
            pressure = pressure**0.85
            raw_importance[key] = attr.base_importance * (0.6 + 0.9 * min(pressure, 6.0))

        total_raw = sum(raw_importance.values()) or 1.0

        attributes: list[InferredAttribute] = []
        for key, sigs in by_attr.items():
            attr = attr_defs[key]
            importance = 100.0 * raw_importance[key] / total_raw
            if importance < _MIN_ATTRIBUTE_IMPORTANCE:
                continue

            evidence_conf = self._evidence_confidence(sigs)
            required = self._required_level(sigs)

            # Preserve strongest, most diverse evidence (verbatim + source).
            top = sorted(sigs, key=lambda s: (s.strength, s.confidence), reverse=True)[:4]
            supporting = [
                {"text": s.evidence_text, "source": s.source_ref or s.source_document_type}
                for s in top
            ]
            source_refs = sorted({s.source_document_type for s in sigs})
            categories = sorted({s.category for s in sigs})

            attributes.append(
                InferredAttribute(
                    key=key,
                    name=attr.name,
                    category=attr.category,
                    description=attr.description,
                    importance_weight=importance,
                    evidence_confidence=evidence_conf,
                    confidence_level=_confidence_level(evidence_conf),
                    required_level=required,
                    supporting_evidence=supporting,
                    evidence_source_refs=source_refs,
                    reasoning=self._reasoning(attr, sigs, importance, evidence_conf),
                    unknown_factors=self._unknowns(attr, sigs, evidence_conf),
                    signal_categories=categories,
                )
            )

        attributes.sort(key=lambda a: a.importance_weight, reverse=True)
        return attributes

    def build_profile(self, signals: list[ExtractedSignal]) -> WinningProfile:
        attributes = self.infer(signals)
        overall_conf = self._overall_confidence(attributes)
        evidence_strength = self._evidence_strength(signals)
        summary = self._summary(attributes, evidence_strength)
        unknowns = self._package_unknowns(signals, attributes)
        return WinningProfile(
            summary=summary,
            overall_confidence=overall_conf,
            evidence_strength=evidence_strength,
            attributes=attributes,
            unknown_factors=unknowns,
        )

    # ── Component computations ───────────────────────────────────────────────────

    @staticmethod
    def _evidence_confidence(sigs: list[ExtractedSignal]) -> float:
        """Confidence the attribute is genuinely required.

        Blends: mean classification confidence, corroboration volume, and source-
        document diversity (independent documents saying the same thing = strong).
        """
        n = len(sigs)
        mean_conf = sum(s.confidence for s in sigs) / n
        volume_bonus = min(18.0, 4.5 * (n - 1))
        diversity = len({s.source_document_type for s in sigs})
        diversity_bonus = min(15.0, 5.0 * (diversity - 1))
        high_value = any(s.source_document_type in _HIGH_VALUE_DOCS for s in sigs)
        hv_bonus = 6.0 if high_value else 0.0
        return round(min(99.0, mean_conf * 0.72 + volume_bonus + diversity_bonus + hv_bonus), 2)

    @staticmethod
    def _required_level(sigs: list[ExtractedSignal]) -> float:
        """The proficiency bar (0–100). Stronger, more corroborated signals raise
        the bar a candidate must clear to be competitive."""
        peak = max(s.strength for s in sigs)
        corroboration = min(12.0, 3.0 * (len(sigs) - 1))
        return round(min(95.0, 52.0 + 0.35 * peak + corroboration), 2)

    @staticmethod
    def _reasoning(
        attr: AttributeDef, sigs: list[ExtractedSignal], importance: float, evidence_conf: float
    ) -> str:
        doc_types = sorted({s.source_document_type.replace("_", " ") for s in sigs})
        return (
            f"{len(sigs)} corroborating signal(s) across {len(doc_types)} document type(s) "
            f"({', '.join(doc_types)}) indicate that '{attr.name.lower()}' is a material "
            f"evaluation concern (importance {importance:.0f}/100, evidence confidence "
            f"{evidence_conf:.0f}/100). {sigs[0].interpretation}"
        )

    @staticmethod
    def _unknowns(
        attr: AttributeDef, sigs: list[ExtractedSignal], evidence_conf: float
    ) -> list[str]:
        unknowns: list[str] = []
        if evidence_conf < 60.0:
            unknowns.append(
                f"Evidence for '{attr.name}' is thin; weighting may shift once Section M "
                f"or Q&A responses are released."
            )
        if not any(s.source_document_type in _HIGH_VALUE_DOCS for s in sigs):
            unknowns.append(
                "No Section M / evaluation-criteria evidence yet — importance is inferred "
                "from narrative language rather than stated evaluation factors."
            )
        return unknowns

    @staticmethod
    def _overall_confidence(attributes: list[InferredAttribute]) -> float:
        if not attributes:
            return 0.0
        weight = sum(a.importance_weight for a in attributes) or 1.0
        return round(
            sum(a.evidence_confidence * a.importance_weight for a in attributes) / weight, 2
        )

    @staticmethod
    def _evidence_strength(signals: list[ExtractedSignal]) -> float:
        """How much evidence the hypothesis rests on (0–100)."""
        if not signals:
            return 0.0
        volume = min(40.0, 2.0 * len(signals))
        categories = len({s.category for s in signals})
        breadth = min(25.0, 2.5 * categories)
        doc_types = {s.source_document_type for s in signals}
        source_diversity = min(20.0, 4.0 * len(doc_types))
        high_value = min(15.0, 5.0 * len(doc_types & _HIGH_VALUE_DOCS))
        return round(min(100.0, volume + breadth + source_diversity + high_value), 2)

    @staticmethod
    def _summary(attributes: list[InferredAttribute], evidence_strength: float) -> str:
        if not attributes:
            return (
                "Insufficient evidence to form a Winning Profile Hypothesis. Add more of "
                "the pre-proposal evidence package (Section M, Q&A responses, SOW/PWS)."
            )
        top = attributes[: min(3, len(attributes))]
        drivers = "; ".join(f"{a.name} ({a.importance_weight:.0f}/100)" for a in top)
        return (
            f"The ideal awardee is most defined by: {drivers}. This hypothesis is built on "
            f"{evidence_strength:.0f}/100 evidence strength across "
            f"{len(attributes)} inferred attributes. It describes what a successful offeror "
            f"would most likely need — it does not predict an award outcome."
        )

    @staticmethod
    def _package_unknowns(
        signals: list[ExtractedSignal], attributes: list[InferredAttribute]
    ) -> list[str]:
        unknowns: list[str] = []
        doc_types = {s.source_document_type for s in signals}
        if not (doc_types & {"section_m", "evaluation_criteria"}):
            unknowns.append(
                "Section M / evaluation factors not yet in evidence — weighting is provisional."
            )
        if not (doc_types & {"qa_response", "government_response"}):
            unknowns.append(
                "No pre-award Q&A yet — a high-value source of evaluation emphasis is missing."
            )
        if not any(a.category == "price" for a in attributes):
            unknowns.append(
                "Price sensitivity is unstated; cost-vs-technical trade-off remains unknown."
            )
        return unknowns
