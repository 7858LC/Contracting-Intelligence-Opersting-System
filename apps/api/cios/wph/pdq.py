"""Pursuit Decision Quality™ (PDQ™) and the Executive Opportunity Intelligence
Assessment™.

PDQ measures the *quality of the pursuit decision* the engine can support — i.e.
how confidently and defensibly a bid / no-bid can be made — NOT a probability of
winning. A high PDQ means the evidence is strong and the target's competitive
position is clear (whether that clarity points to BID or NO-BID). This preserves
the CIOS positioning: CIOS improves decision quality; it does not predict winners.
"""

from __future__ import annotations

from .constants import PursuitRecommendation
from .schemas import Assessment, ContractorAlignment, GapClosure, WinningProfile


class PDQEngine:
    """Synthesizes profile + alignment into an executive assessment."""

    def assess(
        self,
        profile: WinningProfile,
        target: ContractorAlignment,
        ranked: list[ContractorAlignment],
        closures: list[GapClosure],
    ) -> Assessment:
        pool = len(ranked)
        rank = target.rank or self._lookup_rank(target, ranked)

        win_positioning = self._win_positioning(target, ranked)
        pdq = self._pdq_score(profile, target, ranked)
        recommendation = self._recommend(profile, target, closures)

        critical_gaps = [g.to_dict() for g in target.gaps if g.severity in ("critical", "major")]
        closable = {c.gap_attribute_key for c in closures if c.feasibility in ("high", "medium")}
        unclosable_critical = [
            g for g in target.gaps if g.severity == "critical" and g.attribute_key not in closable
        ]

        decision_factors = self._decision_factors(profile, target, rank, pool)
        key_findings = self._key_findings(profile, target, rank, pool, recommendation)
        actions = self._actions(recommendation, closures)
        risks = self._risks(profile, unclosable_critical)
        assumptions = self._assumptions(profile)

        summary = self._executive_summary(
            profile, target, rank, pool, recommendation, pdq, win_positioning
        )

        return Assessment(
            pdq_score=pdq,
            win_positioning_score=win_positioning,
            recommendation=recommendation,
            competitive_rank=rank,
            candidate_pool_size=pool,
            executive_summary=summary,
            key_findings=key_findings,
            decision_factors=decision_factors,
            critical_gaps=critical_gaps,
            recommended_actions=actions,
            risks=risks,
            assumptions=assumptions,
        )

    # ── Scoring ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _lookup_rank(target: ContractorAlignment, ranked: list[ContractorAlignment]) -> int | None:
        for a in ranked:
            if a.contractor_name == target.contractor_name:
                return a.rank
        return None

    @staticmethod
    def _win_positioning(target: ContractorAlignment, ranked: list[ContractorAlignment]) -> float:
        """Alignment adjusted for competitive separation from the field."""
        score = target.overall_alignment_score
        others = [
            a.overall_alignment_score for a in ranked if a.contractor_name != target.contractor_name
        ]
        if others:
            best_other = max(others)
            # Reward/penalize the lead or deficit vs the strongest competitor.
            separation = score - best_other
            score = max(0.0, min(100.0, score + 0.4 * separation))
        return round(score, 2)

    @staticmethod
    def _pdq_score(
        profile: WinningProfile, target: ContractorAlignment, ranked: list[ContractorAlignment]
    ) -> float:
        """Decision-quality confidence.

        Driven by how well we understand winning (evidence strength + profile
        confidence) and how unambiguous the target's position is (distance of the
        alignment from the 50/50 coin-flip zone). Clear positions — high OR low —
        yield high decision quality.
        """
        intel_quality = 0.55 * profile.evidence_strength + 0.45 * profile.overall_confidence
        clarity = abs(target.overall_alignment_score - 50.0) / 50.0  # 0 at 50, 1 at extremes
        decisiveness = 40.0 + 60.0 * clarity
        pdq = 0.6 * intel_quality + 0.4 * decisiveness
        return round(max(0.0, min(100.0, pdq)), 2)

    @staticmethod
    def _recommend(
        profile: WinningProfile, target: ContractorAlignment, closures: list[GapClosure]
    ) -> str:
        score = target.overall_alignment_score
        critical = [g for g in target.gaps if g.severity == "critical"]
        closable = {c.gap_attribute_key for c in closures if c.feasibility in ("high", "medium")}
        unclosable_critical = [g for g in critical if g.attribute_key not in closable]

        # Not enough intelligence to make a high-quality decision yet.
        if profile.evidence_strength < 35.0:
            return PursuitRecommendation.MONITOR.value
        if score >= 70.0 and not unclosable_critical:
            return PursuitRecommendation.BID.value
        if score >= 50.0 and not unclosable_critical:
            return PursuitRecommendation.CONDITIONAL_BID.value
        if score >= 60.0 and unclosable_critical:
            # Strong overall but a hard blocker (e.g. set-aside ineligibility).
            return PursuitRecommendation.CONDITIONAL_BID.value
        return PursuitRecommendation.NO_BID.value

    # ── Narrative builders ───────────────────────────────────────────────────────

    @staticmethod
    def _decision_factors(
        profile: WinningProfile, target: ContractorAlignment, rank: int | None, pool: int
    ) -> list[dict]:
        factors = [
            {
                "factor": "Winning-profile clarity",
                "value": f"{profile.overall_confidence:.0f}/100 confidence, "
                f"{profile.evidence_strength:.0f}/100 evidence strength",
            },
            {"factor": "Target alignment", "value": f"{target.overall_alignment_score:.0f}/100"},
            {
                "factor": "Competitive position",
                "value": f"rank {rank} of {pool}" if rank else "unranked",
            },
            {
                "factor": "Critical gaps",
                "value": f"{sum(1 for g in target.gaps if g.severity == 'critical')} critical, "
                f"{sum(1 for g in target.gaps if g.severity == 'major')} major",
            },
        ]
        # Add the top-3 profile drivers.
        for a in profile.attributes[:3]:
            factors.append(
                {
                    "factor": f"Driver — {a.name}",
                    "value": f"importance {a.importance_weight:.0f}/100, "
                    f"required {a.required_level:.0f}/100",
                }
            )
        return factors

    @staticmethod
    def _key_findings(
        profile: WinningProfile, target: ContractorAlignment, rank: int | None, pool: int, rec: str
    ) -> list[str]:
        findings = [profile.summary, target.summary]
        if rank == 1 and pool > 1:
            findings.append(f"{target.contractor_name} is the best-aligned candidate in the field.")
        elif rank and pool > 1:
            findings.append(
                f"{target.contractor_name} ranks {rank} of {pool} on alignment to the "
                f"winning profile."
            )
        findings.append(f"Engine recommendation: {rec.replace('_', '-').upper()}.")
        return findings

    @staticmethod
    def _actions(rec: str, closures: list[GapClosure]) -> list[dict]:
        actions = [c.to_dict() for c in closures[:6]]
        if rec == PursuitRecommendation.MONITOR.value:
            actions.insert(
                0,
                {
                    "recommendation": "Acquire more of the pre-proposal evidence package "
                    "(Section M, Q&A responses, SOW) before committing B&P investment.",
                    "action_type": "intel",
                    "effort": "low",
                    "timeline_months": 1,
                    "feasibility": "high",
                    "cost_band": "$",
                },
            )
        return actions

    @staticmethod
    def _risks(profile: WinningProfile, unclosable_critical: list) -> list[dict]:
        risks: list[dict] = []
        for g in unclosable_critical:
            risks.append(
                {
                    "risk": f"Unclosable critical gap: {g.attribute_name}",
                    "severity": "high",
                    "mitigation": "Reposition as subcontractor/teaming member, or no-bid.",
                }
            )
        if profile.evidence_strength < 50.0:
            risks.append(
                {
                    "risk": "Winning profile rests on limited evidence; weighting may shift "
                    "materially.",
                    "severity": "medium",
                    "mitigation": "Re-run the hypothesis once Section M and Q&A responses are "
                    "released.",
                }
            )
        for u in profile.unknown_factors[:3]:
            risks.append(
                {"risk": u, "severity": "low", "mitigation": "Track amendments and pre-award Q&A."}
            )
        return risks

    @staticmethod
    def _assumptions(profile: WinningProfile) -> list[str]:
        return [
            "Inferred importance weights approximate — not replace — the government's stated "
            "Section M evaluation factors.",
            "Contractor capability levels are estimated from supplied profile data; validate "
            "against actual CPARS and resumes before B&P commitment.",
            "This assessment improves pursuit-decision quality; it does not predict the award.",
        ]

    @staticmethod
    def _executive_summary(
        profile: WinningProfile,
        target: ContractorAlignment,
        rank: int | None,
        pool: int,
        rec: str,
        pdq: float,
        win_pos: float,
    ) -> str:
        rec_label = rec.replace("_", "-").upper()
        pos = f"ranks {rank} of {pool}" if rank and pool > 1 else "was assessed"
        return (
            f"{target.contractor_name} {pos} against the inferred Winning Profile Hypothesis, "
            f"aligning {target.overall_alignment_score:.0f}/100 "
            f"(win-positioning {win_pos:.0f}/100). "
            f"With {profile.evidence_strength:.0f}/100 evidence strength and "
            f"{profile.overall_confidence:.0f}/100 profile confidence, Pursuit Decision Quality is "
            f"{pdq:.0f}/100. Recommendation: {rec_label}. "
            f"The most decisive requirements are "
            f"{', '.join(a.name for a in profile.attributes[:3])}."
        )
