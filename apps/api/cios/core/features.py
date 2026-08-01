"""Canonical plan → feature entitlements — single source of truth for both
the /subscriptions display endpoint (subscriptions.py) and route-level
enforcement (dependencies.require_feature).

Previously PLAN_FEATURES was defined once in subscriptions.py and returned
only in a GET response for display — nothing ever checked it as an
authorization gate, so every subscription tier's feature list was enforced
by nothing but which sidebar link happened to render (see the commercial
audit that prompted this file).

Keys here are the real values Tenant.plan/the JWT "plan" claim actually
carry: "starter"/"professional"/"growth"/"enterprise" (the four tiers on
apps/web/src/app/(public)/pricing/page.tsx — "growth" added here to match;
it previously had no representation in the backend at all, so the tier
that includes exactly the two modules built this session — Competitive
Intelligence and Capability Gap Analysis — could never actually be granted
or denied), plus "trial" (what /auth/register actually assigns new
tenants, per auth.py — not itself a Stripe-billed tier, treated as
starter-equivalent access here, same fallback subscriptions.py already
used for a tenant with no Subscription row yet).

Award Simulation™/Teaming Intelligence/Competitive Intelligence/
Capabilities & Gaps move from "professional and up" to "growth and up"
here to match the pricing page's own feature comparison table exactly
(it lists all four as growth-only) — a real behavior tightening for any
professional-plan tenant, not just a naming cleanup.

Deliberately NOT extended to Opportunities/Winning Profile Hypothesis™/
Knowledge Vault/Bid-No-Bid/Diagnostics/PDQ, even though the pricing page
lists those as professional-and-up too: none of those routers have ever
had any require_feature() gate, restricting them now would block every
non-professional tenant (including "trial", i.e. every self-serve
signup) from the product's core pre-award workflow that Competitive
Intel and Gap Analysis are themselves built on top of, and the pricing
page's own FAQ describes an "Early Access Program" pricing pilot where
tier boundaries plausibly aren't meant to be hard product walls yet.
That's a real pricing/product decision, not something to enforce
unilaterally alongside a naming cleanup.
"""

from __future__ import annotations

PLAN_FEATURES: dict[str, dict[str, bool | int]] = {
    "starter": {
        "tracked_companies": 250,
        "watchlist_slots": 25,
        "saved_searches": 5,
        "ai_reports_per_month": 10,
        "bulk_scan_jobs_per_month": 2,
        "seats": 3,
        "api_access": False,
        "award_simulator": False,
        "competitive_intel": False,
        "capabilities": False,
        "teaming": False,
    },
    "professional": {
        "tracked_companies": 1000,
        "watchlist_slots": 100,
        "saved_searches": 25,
        "ai_reports_per_month": 100,
        "bulk_scan_jobs_per_month": 20,
        "seats": 10,
        "api_access": False,
        "award_simulator": False,
        "competitive_intel": False,
        "capabilities": False,
        "teaming": False,
    },
    "growth": {
        "tracked_companies": 5000,
        "watchlist_slots": 500,
        "saved_searches": 100,
        "ai_reports_per_month": 500,
        "bulk_scan_jobs_per_month": 100,
        "seats": 25,
        "api_access": False,
        "award_simulator": True,
        "competitive_intel": True,
        "capabilities": True,
        "teaming": True,
    },
    "enterprise": {
        "tracked_companies": -1,
        "watchlist_slots": -1,
        "saved_searches": -1,
        "ai_reports_per_month": -1,
        "bulk_scan_jobs_per_month": -1,
        "seats": -1,
        "api_access": True,
        "award_simulator": True,
        "competitive_intel": True,
        "capabilities": True,
        "teaming": True,
        "customer_owned_keys": True,
        "sso": True,
        "dedicated_support": True,
    },
}

# Plan values that exist on real tenants/JWTs but aren't a distinct paid
# tier of their own — mapped to the tier whose features they get.
_PLAN_ALIASES = {"trial": "starter"}


def _normalize_plan(plan: str) -> str:
    plan = _PLAN_ALIASES.get(plan, plan)
    return plan if plan in PLAN_FEATURES else "starter"


def plan_has_feature(plan: str, feature: str) -> bool:
    return bool(PLAN_FEATURES[_normalize_plan(plan)].get(feature, False))


def plan_limit(plan: str, metric: str) -> int:
    """-1 means unlimited (Enterprise's convention throughout this table)."""
    return int(PLAN_FEATURES[_normalize_plan(plan)].get(metric, 0))


def features_for_plan(plan: str) -> dict[str, bool | int]:
    return PLAN_FEATURES[_normalize_plan(plan)]
