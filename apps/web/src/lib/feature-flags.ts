// Mirrors cios/core/features.py's PLAN_FEATURES — the tiers here are the
// real values Tenant.plan/the JWT "plan" claim carry (trial/starter/
// professional/enterprise, see lib/auth.ts's getUserPlan()), NOT the
// marketing pricing page's four-tier naming (radar/professional/growth/
// enterprise). Reconciling those two vocabularies is a separate product
// decision; this file only needs to match what the backend actually
// enforces, since that's what a mismatch here would silently hide behind.
export const SubscriptionTier = {
  Trial: "trial",
  Starter: "starter",
  Professional: "professional",
  Enterprise: "enterprise",
} as const;

export type SubscriptionTier = (typeof SubscriptionTier)[keyof typeof SubscriptionTier];

export const Feature = {
  ProcurementIntelligenceRadar: "pir",
  ProcurementIntelligenceDiagnostics: "diagnostics",
  WinningProfileHypothesis: "winning_profile",
  PursuitDecisionQuality: "pdq",
  KnowledgeVault: "knowledge_vault",
  Opportunities: "opportunities",
  BidDecisions: "bid_decisions",
  AwardSimulation: "award_simulation",
  Teaming: "teaming",
  Competitors: "competitors",
  Capabilities: "capabilities",
  ExecutiveDashboard: "executive_dashboard",
} as const;

export type Feature = (typeof Feature)[keyof typeof Feature];

// Base set: every module whose API routes are NOT plan-gated server-side
// today (see api/v1/router.py) — kept visible on every plan so the nav
// never hides something the backend would actually still serve.
const UNGATED_MODULES: Feature[] = [
  Feature.ProcurementIntelligenceRadar,
  Feature.ProcurementIntelligenceDiagnostics,
  Feature.WinningProfileHypothesis,
  Feature.PursuitDecisionQuality,
  Feature.KnowledgeVault,
  Feature.Opportunities,
  Feature.BidDecisions,
];

// Gated server-side via require_feature() in router.py — must stay in sync
// with cios/core/features.py's PLAN_FEATURES.
const GATED_MODULES: Feature[] = [
  Feature.AwardSimulation,
  Feature.Teaming,
  Feature.Competitors,
  Feature.Capabilities,
];

const TIER_FEATURES: Record<SubscriptionTier, Feature[]> = {
  trial: UNGATED_MODULES,
  starter: UNGATED_MODULES,
  professional: [...UNGATED_MODULES, ...GATED_MODULES],
  enterprise: [...UNGATED_MODULES, ...GATED_MODULES, Feature.ExecutiveDashboard],
};

export function getFeaturesForTier(tier: SubscriptionTier): Feature[] {
  return TIER_FEATURES[tier] ?? TIER_FEATURES.starter;
}

export function hasFeature(tier: SubscriptionTier, feature: Feature): boolean {
  return getFeaturesForTier(tier).includes(feature);
}
