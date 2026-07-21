"""Procurement Evidence Extraction + Signal Classification services.

Deterministic, explainable extraction: each sentence of each evidence document is
scanned against the ``SIGNAL_LEXICON``. Every match yields an ``ExtractedSignal``
that preserves the verbatim sentence and its source, so downstream inference is
fully traceable. No LLM is required — evidence (the document text) is the source
of truth. An optional LLM enrichment layer may add interpretation later, but it
never overrides the extracted evidence.
"""

from __future__ import annotations

import re

from .schemas import EvidenceDoc, ExtractedSignal
from .taxonomy import DOCUMENT_EVIDENCE_VALUE, SIGNAL_LEXICON

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?;:])\s+|\n+")
_WS = re.compile(r"\s+")


def _sentences(text: str) -> list[str]:
    raw = _SENTENCE_SPLIT.split(text or "")
    out: list[str] = []
    for s in raw:
        s = _WS.sub(" ", s).strip()
        if len(s) >= 8:
            out.append(s)
    return out


def _snippet(sentence: str, limit: int = 400) -> str:
    return sentence if len(sentence) <= limit else sentence[: limit - 1].rstrip() + "…"


class SignalExtractor:
    """Extracts and classifies acquisition signals from an evidence package."""

    def extract_from_document(self, doc: EvidenceDoc) -> list[ExtractedSignal]:
        doc_value = DOCUMENT_EVIDENCE_VALUE.get(doc.document_type, 1.0)
        signals: list[ExtractedSignal] = []

        for sentence in _sentences(doc.content):
            lowered = sentence.lower()
            for pattern in SIGNAL_LEXICON:
                matched = [kw for kw in pattern.keywords if kw in lowered]
                if not matched:
                    continue

                # Strength scales with document evidentiary value and number of
                # distinct keyword hits (more corroborating language = stronger).
                hit_bonus = min(1.25, 1.0 + 0.08 * (len(matched) - 1))
                strength = min(100.0, pattern.base_strength * doc_value * hit_bonus)

                # Classification confidence: high-value docs and multi-keyword hits
                # are more certain classifications.
                confidence = min(
                    98.0,
                    55.0 + 12.0 * len(matched) + 18.0 * (doc_value - 1.0),
                )

                signals.append(
                    ExtractedSignal(
                        category=pattern.category.value,
                        evidence_text=_snippet(sentence),
                        interpretation=pattern.interpretation,
                        strength=round(strength, 2),
                        confidence=round(confidence, 2),
                        source_document_type=doc.document_type,
                        source_ref=doc.source_ref or doc.title,
                        keywords=matched,
                        document_id=doc.document_id,
                    )
                )
        return signals

    def extract(self, docs: list[EvidenceDoc]) -> list[ExtractedSignal]:
        """Extract signals across a full evidence package, deduplicating near-identical
        evidence within the same category+document."""
        all_signals: list[ExtractedSignal] = []
        seen: set[tuple[str, str, str]] = set()
        for doc in docs:
            for sig in self.extract_from_document(doc):
                key = (sig.category, sig.source_document_type, sig.evidence_text[:80].lower())
                if key in seen:
                    continue
                seen.add(key)
                all_signals.append(sig)
        # Strongest evidence first — deterministic ordering.
        all_signals.sort(key=lambda s: (s.strength, s.confidence), reverse=True)
        return all_signals
