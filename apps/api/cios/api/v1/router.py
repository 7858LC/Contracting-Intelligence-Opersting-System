"""API v1 router — all CIOS modules."""
from fastapi import APIRouter

from .endpoints import (
    auth,
    opportunities,
    bid_decisions,
    award_simulations,
    capabilities,
    past_performance,
    teaming,
    competitors,
    knowledge_vault,
    agent_runs,
    tenants,
    subscriptions,
    onboarding,
    webhooks,
    admin,
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
api_router.include_router(capabilities.router, prefix="/capabilities", tags=["Capabilities"])

# Module 6 — Past Performance Intelligence
api_router.include_router(past_performance.router, prefix="/past-performance", tags=["Past Performance"])

# Module 7 — Teaming Recommendation Engine
api_router.include_router(teaming.router, prefix="/teaming", tags=["Teaming"])

# Module 8 — Competitive Intelligence
api_router.include_router(competitors.router, prefix="/competitors", tags=["Competitors"])

# Module 13 — Award Simulator (flagship)
api_router.include_router(award_simulations.router, prefix="/award-simulations", tags=["Award Simulator"])

# Knowledge Vault
api_router.include_router(knowledge_vault.router, prefix="/knowledge-vault", tags=["Knowledge Vault"])

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
