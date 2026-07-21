"""Contractor Alignment Analysis™, Competitive Ranking™, Gap Analysis™,
and Gap Closure Recommendations™.

Given a Winning Profile Hypothesis and a set of contractor capability profiles,
compute — deterministically and explainably — how each contractor aligns to what
winning requires, where the gaps are, and what it would take to close them.
"""

from __future__ import annotations

from .schemas import (
    AttributeAlignment,
    CapabilityGap,
    ContractorAlignment,
    ContractorProfile,
    GapClosure,
    InferredAttribute,
    WinningProfile,
)
from .taxonomy import ATTRIBUTE_LIBRARY

_ATTR_BY_KEY = {a.key: a for a in ATTRIBUTE_LIBRARY}

# Eligibility-style attributes where the socioeconomic status is binary.
_SET_ASIDE_TOKENS = {"8(a)", "8a", "sdvosb", "hubzone", "wosb", "vosb", "small business", "wbe"}
_CLEARANCE_TOKENS = {"secret", "top secret", "ts/sci", "ts", "fcl", "cleared"}


def _default_baseline(profile: ContractorProfile) -> float:
    """A generic firm with no evidence for an attribute still has *some* baseline
    capability; incumbents carry a modest institutional-knowledge premium."""
    base = 25.0
    if profile.is_incumbent:
        base += 20.0
    return base


def _keyword_level(profile: ContractorProfile, attr_key: str) -> float:
    """Estimate capability level from free-text scanning when no explicit level is given."""
    attr = _ATTR_BY_KEY.get(attr_key)
    if not attr or not attr.capability_keywords:
        return _default_baseline(profile)
    text = " ".join(
        [
            profile.capability_text or "",
            profile.description or "",
            " ".join(str(c) for c in profile.certifications),
            " ".join(
                str(p.get("title", "")) + " " + str(p.get("description", ""))
                for p in profile.past_performance
            ),
        ]
    ).lower()
    hits = sum(1 for kw in attr.capability_keywords if kw in text)
    if hits == 0:
        return _default_baseline(profile)
    # 1 hit ≈ 55, scaling toward 95 with corroboration.
    return min(95.0, 45.0 + 16.0 * hits + (10.0 if profile.is_incumbent else 0.0))


class AlignmentScorer:
    """Scores one contractor against the winning profile and derives gaps."""

    # Severity thresholds on the "weighted gap" = importance_weight * (gap/100).
    _CRITICAL = 6.0
    _MAJOR = 3.0
    _MODERATE = 1.0

    def contractor_level(self, profile: ContractorProfile, attr: InferredAttribute) -> float:
        # 1) explicit level by attribute key or name wins.
        caps = {str(k).lower(): float(v) for k, v in (profile.capabilities or {}).items()}
        for candidate in (attr.key, attr.name.lower(), attr.category):
            if candidate in caps:
                return max(0.0, min(100.0, caps[candidate]))

        # 2) special-cased eligibility/security attributes use structured fields.
        if attr.key == "set_aside_eligibility":
            tokens = {t.lower() for t in (profile.set_asides + profile.certifications)}
            return 95.0 if tokens & _SET_ASIDE_TOKENS else 5.0
        if attr.key == "security_posture":
            tokens = {t.lower() for t in (profile.clearances + profile.certifications)}
            has_clear = any(any(ct in t for ct in _CLEARANCE_TOKENS) for t in tokens)
            has_cyber = any(c in " ".join(tokens) for c in ("cmmc", "fedramp", "nist", "iso 27001"))
            level = 20.0
            if has_clear:
                level += 45.0
            if has_cyber:
                level += 30.0
            return min(95.0, level)

        # 3) fall back to free-text keyword estimation.
        return _keyword_level(profile, attr.key)

    def score(self, profile: WinningProfile, contractor: ContractorProfile) -> ContractorAlignment:
        alignments: list[AttributeAlignment] = []
        gaps: list[CapabilityGap] = []
        strengths: list[str] = []
        weaknesses: list[str] = []
        overall = 0.0

        for attr in profile.attributes:
            level = self.contractor_level(contractor, attr)
            required = attr.required_level
            met = min(1.0, level / required) if required > 0 else 1.0
            alignment_pct = round(met * 100.0, 2)
            contribution = attr.importance_weight * met
            overall += contribution

            reasoning = (
                f"Requires ~{required:.0f}/100; {contractor.name} demonstrates ~{level:.0f}/100 "
                f"→ {alignment_pct:.0f}% of the bar met."
            )
            evidence = attr.supporting_evidence[0]["text"] if attr.supporting_evidence else ""
            alignments.append(
                AttributeAlignment(
                    attribute_key=attr.key,
                    attribute_name=attr.name,
                    category=attr.category,
                    importance_weight=attr.importance_weight,
                    required_level=required,
                    contractor_level=level,
                    alignment=alignment_pct,
                    contribution=contribution,
                    evidence=evidence,
                    reasoning=reasoning,
                )
            )

            if level >= required and attr.importance_weight >= 8.0:
                strengths.append(f"{attr.name}: meets the high-importance bar ({level:.0f}/100).")

            gap_size = required - level
            if gap_size > 5.0:
                weighted_gap = attr.importance_weight * (gap_size / 100.0)
                severity = self._severity(weighted_gap)
                impact = (
                    f"Shortfall of {gap_size:.0f} points on a {attr.importance_weight:.0f}/100 "
                    f"importance attribute — {severity} exposure at evaluation."
                )
                gaps.append(
                    CapabilityGap(
                        attribute_key=attr.key,
                        attribute_name=attr.name,
                        category=attr.category,
                        severity=severity,
                        importance_weight=attr.importance_weight,
                        required_level=required,
                        contractor_level=level,
                        gap_size=gap_size,
                        impact=impact,
                    )
                )
                if severity in ("critical", "major"):
                    weaknesses.append(f"{attr.name}: {severity} gap ({gap_size:.0f} points short).")

        overall_score = round(overall, 2)  # importance sums to 100 → already 0–100
        gaps.sort(key=lambda g: g.importance_weight * g.gap_size, reverse=True)
        summary = self._summary(contractor, overall_score, gaps, strengths)

        return ContractorAlignment(
            contractor_name=contractor.name,
            overall_alignment_score=overall_score,
            attribute_alignments=alignments,
            gaps=gaps,
            strengths=strengths,
            weaknesses=weaknesses,
            summary=summary,
        )

    def _severity(self, weighted_gap: float) -> str:
        if weighted_gap >= self._CRITICAL:
            return "critical"
        if weighted_gap >= self._MAJOR:
            return "major"
        if weighted_gap >= self._MODERATE:
            return "moderate"
        return "minor"

    @staticmethod
    def _summary(
        contractor: ContractorProfile, score: float, gaps: list[CapabilityGap], strengths: list[str]
    ) -> str:
        band = (
            "strongly aligned"
            if score >= 75
            else "competitively aligned"
            if score >= 60
            else "partially aligned"
            if score >= 45
            else "weakly aligned"
        )
        crit = sum(1 for g in gaps if g.severity == "critical")
        return (
            f"{contractor.name} is {band} to the winning profile ({score:.0f}/100) with "
            f"{len(strengths)} standout strength(s) and {crit} critical gap(s)."
        )


class GapCloser:
    """Generates Gap Closure Recommendations™ — how to become competitive."""

    # Category-specific closure playbook: (action_type, template, months, feasibility, cost).
    _PLAYBOOK: dict[str, dict] = {
        "security": dict(
            action_type="partner",
            base_months=9,
            feasibility="medium",
            cost="$$$",
            template="Team with or acquire a partner holding the required facility/personnel "
            "clearances, or sponsor an FCL and accelerate CMMC/FedRAMP accreditation.",
        ),
        "past_performance": dict(
            action_type="teaming",
            base_months=2,
            feasibility="high",
            cost="$",
            template="Add a teaming partner with directly relevant, recent CPARS of similar size "
            "and scope to backfill the past-performance record.",
        ),
        "personnel": dict(
            action_type="hire",
            base_months=3,
            feasibility="high",
            cost="$$",
            template="Recruit and letter-of-commit named key personnel with the required "
            "certifications (e.g. PMP) ahead of proposal submission.",
        ),
        "capacity": dict(
            action_type="teaming",
            base_months=4,
            feasibility="medium",
            cost="$$",
            template="Establish subcontractor/teaming capacity or a surge staffing pipeline to "
            "credibly meet scale and surge requirements.",
        ),
        "technical": dict(
            action_type="invest",
            base_months=4,
            feasibility="medium",
            cost="$$",
            template="Invest in solution engineering / a proof-of-concept and capture reusable "
            "technical artifacts to deepen the technical approach.",
        ),
        "transition": dict(
            action_type="invest",
            base_months=2,
            feasibility="high",
            cost="$",
            template="Develop a detailed, low-risk phase-in plan with a transition team and "
            "knowledge-capture approach to neutralize incumbent risk.",
        ),
        "domain": dict(
            action_type="hire",
            base_months=3,
            feasibility="medium",
            cost="$$",
            template="Bring on mission SMEs or advisors with agency-specific domain experience "
            "to establish credibility.",
        ),
        "eligibility": dict(
            action_type="partner",
            base_months=6,
            feasibility="low",
            cost="$$",
            template="Pursue through a qualifying JV/mentor-protégé or as a subcontractor, since "
            "the set-aside gates prime eligibility.",
        ),
        "compliance": dict(
            action_type="certify",
            base_months=8,
            feasibility="medium",
            cost="$$",
            template="Initiate the required certification (CMMI/ISO 9001/508) or document "
            "equivalent mature processes to satisfy the requirement.",
        ),
        "innovation": dict(
            action_type="invest",
            base_months=3,
            feasibility="medium",
            cost="$$",
            template="Package modernization/innovation assets (AI, automation) and reference "
            "implementations to demonstrate differentiated value.",
        ),
        "price": dict(
            action_type="reprice",
            base_months=1,
            feasibility="high",
            cost="$",
            template="Re-engineer the cost basis (labor mix, indirect rates, subcontracting) to "
            "reach a competitive, realistic price point.",
        ),
        "geographic": dict(
            action_type="invest",
            base_months=3,
            feasibility="medium",
            cost="$$",
            template="Stand up a local presence or on-site staffing commitment at the place of "
            "performance.",
        ),
    }

    _DEFAULT = dict(
        action_type="pursue",
        base_months=3,
        feasibility="medium",
        cost="$$",
        template="Develop a targeted capture action to raise this capability toward the "
        "required bar.",
    )

    def recommend(self, gaps: list[CapabilityGap]) -> list[GapClosure]:
        closures: list[GapClosure] = []
        for gap in gaps:
            play = self._PLAYBOOK.get(gap.category, self._DEFAULT)
            # Effort/timeline scale with gap size.
            if gap.gap_size >= 45:
                effort, months_mult = "high", 1.5
            elif gap.gap_size >= 20:
                effort, months_mult = "medium", 1.0
            else:
                effort, months_mult = "low", 0.6
            timeline = max(1, round(play["base_months"] * months_mult))
            # Closing typically lifts the contractor to just above the required bar,
            # scaled by feasibility.
            lift = gap.gap_size * (
                0.9
                if play["feasibility"] == "high"
                else 0.7
                if play["feasibility"] == "medium"
                else 0.45
            )
            closes_to = min(100.0, gap.contractor_level + lift)
            rec = (
                f"[{gap.severity.upper()}] {gap.attribute_name}: {play['template']} "
                f"Target lift {gap.contractor_level:.0f} → {closes_to:.0f}/100."
            )
            closures.append(
                GapClosure(
                    gap_attribute_key=gap.attribute_key,
                    gap_attribute_name=gap.attribute_name,
                    recommendation=rec,
                    action_type=play["action_type"],
                    effort=effort,
                    timeline_months=timeline,
                    feasibility=play["feasibility"],
                    cost_band=play["cost"],
                    closes_gap_to=closes_to,
                )
            )
        return closures


def rank_alignments(alignments: list[ContractorAlignment]) -> list[ContractorAlignment]:
    """Competitive Alignment Ranking™ — order contractors by alignment and stamp ranks."""
    ordered = sorted(alignments, key=lambda a: a.overall_alignment_score, reverse=True)
    for i, alignment in enumerate(ordered, start=1):
        alignment.rank = i
    return ordered
