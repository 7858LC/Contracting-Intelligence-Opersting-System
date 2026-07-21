"""Winning Profile Agent — Director-tier narrative enrichment.

The Winning Profile Hypothesis™ is produced deterministically by the evidence-
fusion engine (``cios.wph``); *evidence is the source of truth*. This agent adds
an optional executive-readable narrative on top of the already-computed profile.
It never changes weights, scores, or attributes — it only explains them. If the
Claude call fails or no API key is configured, the deterministic output stands
on its own.
"""
from __future__ import annotations

from typing import Any

from cios.config import settings
from cios.wph.schemas import WinningProfile

from .base import AgentContext, BaseAgent

_SYSTEM_PROMPT = """You are the Winning Profile Director for CIOS — the Contract \
Intelligence Operating System. You operate inside Procurement Intelligence™, a \
management discipline that improves executive pursuit decisions BEFORE proposal \
development begins.

You are given a Winning Profile Hypothesis™ that has ALREADY been computed by an \
explainable evidence-fusion engine — attribute weights, confidence scores, and \
required levels are fixed and authoritative. Your job is ONLY to write a concise, \
executive-grade narrative that explains what the ideal awardee would most likely \
look like and why, grounded strictly in the supplied attributes and evidence.

Rules:
- NEVER predict the winner or claim certainty about the award outcome.
- NEVER invent attributes, weights, or evidence not provided.
- Frame everything as an inferred hypothesis about what winning likely requires.
- Be candid about unknown factors and evidence limitations.
- 150 words maximum. No preamble, no headers — just the narrative paragraph(s)."""


def _profile_brief(profile: WinningProfile, context_meta: dict[str, Any]) -> str:
    lines = [
        f"Solicitation: {context_meta.get('title', 'Unknown')}",
        f"Agency: {context_meta.get('agency', 'Unknown')}",
        f"Overall confidence: {profile.overall_confidence:.0f}/100 · "
        f"Evidence strength: {profile.evidence_strength:.0f}/100",
        "",
        "Inferred winning-profile attributes (importance / evidence-confidence / required):",
    ]
    for a in profile.attributes:
        lines.append(
            f"- {a.name}: importance {a.importance_weight:.0f}/100, "
            f"evidence {a.evidence_confidence:.0f}/100, required {a.required_level:.0f}/100. "
            f"{(a.reasoning or '')[:180]}"
        )
    if profile.unknown_factors:
        lines.append("")
        lines.append("Unknown factors: " + "; ".join(profile.unknown_factors[:4]))
    return "\n".join(lines)


class WinningProfileAgent(BaseAgent):
    """Director-tier agent (Claude Sonnet) that narrates a computed hypothesis."""

    name = "winning_profile_director"
    model = settings.anthropic_model_director
    max_tokens = 700
    temperature = 0.2

    async def _execute(self, context: AgentContext, **kwargs: Any) -> dict[str, Any]:
        profile: WinningProfile = kwargs["profile"]
        meta = context.metadata or {}
        user_message = (
            "Write the executive narrative for this Winning Profile Hypothesis.\n\n"
            + _profile_brief(profile, meta)
        )
        narrative = await self._call_claude(_SYSTEM_PROMPT, user_message)
        return {"narrative": narrative.strip(), "model": self.model}


async def enrich_profile_narrative(
    profile: WinningProfile,
    tenant_id: Any,
    solicitation_meta: dict[str, Any] | None = None,
) -> str | None:
    """Best-effort narrative enrichment. Returns None on any failure."""
    import uuid as _uuid

    try:
        agent = WinningProfileAgent()
        ctx = AgentContext(
            tenant_id=tenant_id,
            user_id=_uuid.uuid4(),
            metadata=solicitation_meta or {},
        )
        run = await agent.run(ctx, profile=profile)
        narrative = run["result"]["narrative"]
        return str(narrative) if narrative else None
    except Exception:  # noqa: BLE001 — enrichment is optional, never fatal
        return None
