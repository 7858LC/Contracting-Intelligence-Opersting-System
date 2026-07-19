"""PIR Signal Scoring Engine — computes company-level scores from detected signals."""
from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from cios.models.pir import PriorityTier, SignalType

if TYPE_CHECKING:
    from cios.models.pir import PIRSignal

# Base weight per signal type (raw contribution toward overall score)
SIGNAL_WEIGHTS: dict[str, int] = {
    # Hiring signals
    SignalType.HIRING_CAPTURE_MANAGER: 10,
    SignalType.HIRING_PROPOSAL_MANAGER: 8,
    SignalType.HIRING_BD_DIRECTOR: 9,
    SignalType.HIRING_CONTRACTS_MANAGER: 7,
    SignalType.HIRING_PRICING_MANAGER: 7,
    SignalType.HIRING_COMPLIANCE_MANAGER: 6,
    SignalType.HIRING_GOVERNMENT_SALES: 8,
    SignalType.HIRING_PROGRAM_MANAGER: 5,
    SignalType.HIRING_CLEARED_PERSONNEL: 6,
    # Award signals
    SignalType.FEDERAL_CONTRACT_AWARD: 15,
    SignalType.STATE_CONTRACT_AWARD: 8,
    SignalType.IDIQ_AWARD: 12,
    SignalType.GWAC_AWARD: 12,
    SignalType.SBIR_STTR_AWARD: 10,
    SignalType.CONTRACT_RECOMPETE: 12,
    SignalType.MENTOR_PROTEGE: 8,
    SignalType.JOINT_VENTURE: 7,
    SignalType.TEAMING_ANNOUNCEMENT: 6,
    # Growth signals
    SignalType.NEW_OFFICE: 5,
    SignalType.EXECUTIVE_HIRE: 6,
    SignalType.MERGER_ACQUISITION: 7,
    SignalType.EXPANSION_ANNOUNCEMENT: 5,
    # Certification signals
    SignalType.SAM_REGISTRATION: 3,
    SignalType.CMMC_CERTIFICATION: 8,
    SignalType.ISO_CERTIFICATION: 4,
    SignalType.SOC2_CERTIFICATION: 4,
    SignalType.CMMI_CERTIFICATION: 5,
    SignalType.CERTIFICATION_8A: 6,
    SignalType.CERTIFICATION_SDVOSB: 5,
    SignalType.CERTIFICATION_HUBZONE: 5,
    SignalType.CERTIFICATION_WOSB: 5,
    SignalType.CERTIFICATION_VETERAN: 4,
    SignalType.CERTIFICATION_MINORITY: 4,
}

# Signal types that directly contribute to government readiness
_GOVREADY_SIGNALS: frozenset[str] = frozenset({
    SignalType.SAM_REGISTRATION,
    SignalType.CMMC_CERTIFICATION,
    SignalType.CMMI_CERTIFICATION,
    SignalType.CERTIFICATION_8A,
    SignalType.CERTIFICATION_SDVOSB,
    SignalType.CERTIFICATION_HUBZONE,
    SignalType.CERTIFICATION_WOSB,
    SignalType.CERTIFICATION_VETERAN,
    SignalType.CERTIFICATION_MINORITY,
    SignalType.FEDERAL_CONTRACT_AWARD,
    SignalType.IDIQ_AWARD,
    SignalType.GWAC_AWARD,
    SignalType.SBIR_STTR_AWARD,
    SignalType.CONTRACT_RECOMPETE,
})

# Decay half-lives (days) — older signals matter less
_HALF_LIFE_DAYS: dict[str, float] = {
    "hiring": 45.0,   # Job posts stale quickly
    "award": 180.0,   # Awards remain relevant longer
    "growth": 90.0,
    "certification": 365.0,  # Certs don't expire quickly
}

_SIGNAL_CATEGORY: dict[str, str] = {}
for _st in [
    SignalType.HIRING_CAPTURE_MANAGER, SignalType.HIRING_PROPOSAL_MANAGER,
    SignalType.HIRING_BD_DIRECTOR, SignalType.HIRING_CONTRACTS_MANAGER,
    SignalType.HIRING_PRICING_MANAGER, SignalType.HIRING_COMPLIANCE_MANAGER,
    SignalType.HIRING_GOVERNMENT_SALES, SignalType.HIRING_PROGRAM_MANAGER,
    SignalType.HIRING_CLEARED_PERSONNEL,
]:
    _SIGNAL_CATEGORY[_st] = "hiring"

for _st in [
    SignalType.FEDERAL_CONTRACT_AWARD, SignalType.STATE_CONTRACT_AWARD,
    SignalType.IDIQ_AWARD, SignalType.GWAC_AWARD, SignalType.SBIR_STTR_AWARD,
    SignalType.CONTRACT_RECOMPETE, SignalType.MENTOR_PROTEGE,
    SignalType.JOINT_VENTURE, SignalType.TEAMING_ANNOUNCEMENT,
]:
    _SIGNAL_CATEGORY[_st] = "award"

for _st in [
    SignalType.NEW_OFFICE, SignalType.EXECUTIVE_HIRE,
    SignalType.MERGER_ACQUISITION, SignalType.EXPANSION_ANNOUNCEMENT,
]:
    _SIGNAL_CATEGORY[_st] = "growth"

for _st in [
    SignalType.SAM_REGISTRATION, SignalType.CMMC_CERTIFICATION,
    SignalType.ISO_CERTIFICATION, SignalType.SOC2_CERTIFICATION,
    SignalType.CMMI_CERTIFICATION, SignalType.CERTIFICATION_8A,
    SignalType.CERTIFICATION_SDVOSB, SignalType.CERTIFICATION_HUBZONE,
    SignalType.CERTIFICATION_WOSB, SignalType.CERTIFICATION_VETERAN,
    SignalType.CERTIFICATION_MINORITY,
]:
    _SIGNAL_CATEGORY[_st] = "certification"


def _decay_factor(detected_at: datetime, category: str) -> float:
    """Exponential decay based on signal age relative to category half-life."""
    now = datetime.now(UTC)
    age_days = max(0.0, (now - detected_at).total_seconds() / 86_400)
    half_life = _HALF_LIFE_DAYS.get(category, 90.0)
    return math.exp(-math.log(2) * age_days / half_life)


class SignalScorer:
    """
    Computes four composite scores (0–100) from a list of PIRSignal records
    and assigns a priority tier (A/B/C).

    Designed to be called after signals are upserted into the database.
    """

    def compute(self, signals: list["PIRSignal"]) -> dict:
        """
        Returns a dict with keys:
            overall_signal_score, confidence_score, growth_momentum_score,
            government_readiness_score, priority_tier
        and per-signal effective_weight/decay_factor (mutates signal objects in-place).
        """
        if not signals:
            return self._zero_scores()

        active = [s for s in signals if not s.is_duplicate]

        # Compute and store decay factor + effective weight for each signal
        for sig in active:
            category = _SIGNAL_CATEGORY.get(sig.signal_type, "growth")
            decay = _decay_factor(sig.detected_at, category)
            raw_w = SIGNAL_WEIGHTS.get(sig.signal_type, 3)
            sig.decay_factor = round(decay, 4)
            sig.effective_weight = round(raw_w * decay, 4)

        overall = self._overall_score(active)
        confidence = self._confidence_score(active)
        momentum = self._growth_momentum_score(active)
        readiness = self._government_readiness_score(active)
        tier = self._assign_tier(overall)

        return {
            "overall_signal_score": overall,
            "confidence_score": confidence,
            "growth_momentum_score": momentum,
            "government_readiness_score": readiness,
            "priority_tier": tier,
        }

    # ── Individual score computations ──────────────────────────────────────────

    def _overall_score(self, signals: list) -> float:
        """
        Sum of effective weights, capped at 100.
        Uses soft-cap via tanh so score approaches 100 asymptotically rather
        than hard-clipping (avoids perverse incentive of score = 100 forever).
        """
        raw = sum(s.effective_weight for s in signals)
        # tanh soft cap: raw=50 → ~91; raw=40 → ~83; raw=30 → ~67
        scaled = 100.0 * math.tanh(raw / 50.0)
        return round(min(100.0, scaled), 2)

    def _confidence_score(self, signals: list) -> float:
        """
        Composite confidence based on:
        - Signal volume (more signals = higher confidence, up to 20)
        - Source diversity (unique sources, up to 10 sources)
        - Recency (fraction of signals < 30 days old)
        - Verification rate (fraction is_verified)
        """
        now = datetime.now(UTC)
        n = len(signals)
        if n == 0:
            return 0.0

        # Volume component (0–40 pts)
        volume_pts = min(40.0, n * 2.0)

        # Source diversity component (0–25 pts)
        unique_sources = len({s.source for s in signals})
        diversity_pts = min(25.0, unique_sources * 5.0)

        # Recency component (0–20 pts)
        recent = sum(1 for s in signals if (now - s.detected_at).days < 30)
        recency_pts = 20.0 * (recent / n)

        # Verification component (0–15 pts)
        verified = sum(1 for s in signals if s.is_verified)
        verify_pts = 15.0 * (verified / n)

        total = volume_pts + diversity_pts + recency_pts + verify_pts
        return round(min(100.0, total), 2)

    def _growth_momentum_score(self, signals: list) -> float:
        """
        Recency-weighted count of growth and hiring signals in three windows.
        30-day window → 3× weight, 60-day → 2×, 90-day → 1×.
        Normalized to 100 based on a target of 15 weighted signal-points.
        """
        now = datetime.now(UTC)
        d30 = timedelta(days=30)
        d60 = timedelta(days=60)
        d90 = timedelta(days=90)

        relevant_types = set(_SIGNAL_CATEGORY.keys())
        # Use all signal types for momentum, not just growth category
        total = 0.0
        for sig in signals:
            if sig.signal_type not in relevant_types:
                continue
            age = now - sig.detected_at
            if age <= d30:
                total += 3.0
            elif age <= d60:
                total += 2.0
            elif age <= d90:
                total += 1.0

        target = 15.0
        return round(min(100.0, (total / target) * 100.0), 2)

    def _government_readiness_score(self, signals: list) -> float:
        """
        Score based on certifications, registrations, and contract history.
        Max raw points: SAM(5) + certs(up to 30) + awards(up to 40) + others(up to 25)
        """
        seen_types: set[str] = set()
        pts = 0.0

        for sig in signals:
            if sig.signal_type not in _GOVREADY_SIGNALS:
                continue
            if sig.signal_type in seen_types:
                # Only count each type once for readiness (don't stack duplicates)
                continue
            seen_types.add(sig.signal_type)

            weight = SIGNAL_WEIGHTS.get(sig.signal_type, 3)
            # Apply decay so stale certs don't fully count
            pts += weight * sig.decay_factor

        # Normalize against a realistic "ideal" company (e.g., 8a + SAM + 2 awards = ~36 pts)
        return round(min(100.0, (pts / 36.0) * 100.0), 2)

    def _assign_tier(self, overall: float) -> str:
        if overall >= 60.0:
            return PriorityTier.A
        if overall >= 30.0:
            return PriorityTier.B
        return PriorityTier.C

    @staticmethod
    def _zero_scores() -> dict:
        return {
            "overall_signal_score": 0.0,
            "confidence_score": 0.0,
            "growth_momentum_score": 0.0,
            "government_readiness_score": 0.0,
            "priority_tier": PriorityTier.C,
        }
