"""Canonical plan → feature entitlements — single source of truth for both
the /subscriptions display endpoint (subscriptions.py) and route-level
enforcement (dependencies.require_feature).

Previously PLAN_FEATURES was defined once in subscriptions.py and returned
only in a GET response for display — nothing ever checked it as an
authorization gate, so every subscription tier's feature list was enforced
by nothing but which sidebar link happened to render (see the commercial
audit that prompted this file). This is the fix: the same dict now backs
an actual 403 on the gated routers in api/v1/router.py.

Keys here are the real values Tenant.plan/the JWT "plan" claim actually
carry — "starter"/"professional"/"enterprise" (Tenant.plan's default and
what subscriptions.py's Stripe price map already uses), plus "trial" (what
/auth/register actually assigns new tenants, per auth.py — not itself a
Stripe-billed tier, treated as starter-equivalent access here, same
fallback subscriptions.py already used for a tenant with no Subscription
row yet). This is deliberately NOT the marketing pricing page's four-tier
naming (radar/professional/growth/enterprise) — reconciling those two
tier vocabularies is a separate, larger product decision; this file only
makes the tiers that actually exist in the database enforceable.
"""

from __future__ import annotations

PLAN_FEATURES: dict[str, dict[str, bool | int]] = {
    "starter": {
        "opportunities": 50,
        "simulations": 5,
        "knowledge_vault_mb": 500,
        "seats": 3,
        "api_access": False,
        "award_simulator": True,
        "competitive_intel": False,
        "capabilities": False,
        "teaming": False,
    },
    "professional": {
        "opportunities": 500,
        "simulations": 50,
        "knowledge_vault_mb": 5000,
        "seats": 10,
        "api_access": True,
        "award_simulator": True,
        "competitive_intel": True,
        "capabilities": True,
        "teaming": True,
    },
    "enterprise": {
        "opportunities": -1,
        "simulations": -1,
        "knowledge_vault_mb": -1,
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


def features_for_plan(plan: str) -> dict[str, bool | int]:
    return PLAN_FEATURES[_normalize_plan(plan)]
