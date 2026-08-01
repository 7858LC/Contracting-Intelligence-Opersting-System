"""API v1 router — all CIOS modules."""

from fastapi import APIRouter, Depends

from cios.core.dependencies import require_feature

from .endpoints import (
    admin,
    agent_runs,
    auth,
    award_simulations,
    bid_decisions,
    capabilities,
    competitors,
    knowledge_vault,
    onboarding,
    opportunities,
    past_performance,
    pir,
    research,
    subscriptions,
    teaming,
    tenants,
    webhooks,
    winning_profile,
)

api_router = APIRouter()

# Authentication
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])

# Tenant management
api_router.include_router(tenants.router, prefix="/tenants", tags=["Tenants"])

# Module 1 — Opportunity Intelligence
api_router.include_router(opportunities.router, prefix="/opportunities", tags=["Opportunities"])

# Module 2 — Bid/No-Bid Engine
api_router.include_router(bid_decisions.router, prefix="/bid-decisions", tags=["Bid Decisions"])

# Modules 5 & 15 — Capability & Organizational Intelligence
# Sold as a whole module (Professional+) on the pricing page, so the gate
# applies to the whole router — not just the AI gap-analysis trigger.
api_router.include_router(
    capabilities.router,
    prefix="/capabilities",
    tags=["Capabilities"],
    dependencies=[Depends(require_feature("capabilities"))],
)

# Module 6 — Past Performance Intelligence
api_router.include_router(
    past_performance.router, prefix="/past-performance", tags=["Past Performance"]
)

# Module 7 — Teaming Recommendation Engine
api_router.include_router(
    teaming.router,
    prefix="/teaming",
    tags=["Teaming"],
    dependencies=[Depends(require_feature("teaming"))],
)

# Module 8 — Competitive Intelligence
api_router.include_router(
    competitors.router,
    prefix="/competitors",
    tags=["Competitors"],
    dependencies=[Depends(require_feature("competitive_intel"))],
)

# Module 13 — Award Simulator (flagship)
api_router.include_router(
    award_simulations.router,
    prefix="/award-simulations",
    tags=["Award Simulator"],
    dependencies=[Depends(require_feature("award_simulator"))],
)

# Knowledge Vault
api_router.include_router(
    knowledge_vault.router, prefix="/knowledge-vault", tags=["Knowledge Vault"]
)

# Agent Runs (audit trail)
api_router.include_router(agent_runs.router, prefix="/agent-runs", tags=["Agent Runs"])

# Subscriptions & Billing
api_router.include_router(subscriptions.router, prefix="/subscriptions", tags=["Subscriptions"])

# Onboarding
api_router.include_router(onboarding.router, prefix="/onboarding", tags=["Onboarding"])

# Stripe webhooks
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])

# Admin
api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])

# Module PIR — Procurement Intelligence Radar™
api_router.include_router(pir.router, prefix="/radar", tags=["Procurement Intelligence Radar"])

# Module WPH — Winning Profile Hypothesis™ (pre-award intelligence)
api_router.include_router(
    winning_profile.router, prefix="/winning-profile", tags=["Winning Profile Hypothesis"]
)

# Research — Executive Council report access
api_router.include_router(research.router, prefix="/research", tags=["Research"])
