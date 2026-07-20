export const SubscriptionTier = {
  Radar: "radar",
  Professional: "professional",
  Growth: "growth",
  Enterprise: "enterprise",
} as const;

export type SubscriptionTier = (typeof SubscriptionTier)[keyof typeof SubscriptionTier];

export const Feature = {
  ProcurementIntelligenceRadar: "pir",
  ProcurementIntelligenceDiagnostics: "diagnostics",
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

const TIER_FEATURES: Record<SubscriptionTier, Feature[]> = {
  radar: [Feature.ProcurementIntelligenceRadar],
  professional: [
    Feature.ProcurementIntelligenceRadar,
    Feature.ProcurementIntelligenceDiagnostics,
    Feature.PursuitDecisionQuality,
    Feature.KnowledgeVault,
    Feature.Opportunities,
    Feature.BidDecisions,
  ],
  growth: [
    Feature.ProcurementIntelligenceRadar,
    Feature.ProcurementIntelligenceDiagnostics,
    Feature.PursuitDecisionQuality,
    Feature.KnowledgeVault,
    Feature.Opportunities,
    Feature.BidDecisions,
    Feature.AwardSimulation,
    Feature.Teaming,
    Feature.Competitors,
    Feature.Capabilities,
  ],
  enterprise: [
    Feature.ProcurementIntelligenceRadar,
    Feature.ProcurementIntelligenceDiagnostics,
    Feature.PursuitDecisionQuality,
    Feature.KnowledgeVault,
    Feature.Opportunities,
    Feature.BidDecisions,
    Feature.AwardSimulation,
    Feature.Teaming,
    Feature.Competitors,
    Feature.Capabilities,
    Feature.ExecutiveDashboard,
  ],
};

export function getFeaturesForTier(tier: SubscriptionTier): Feature[] {
  return TIER_FEATURES[tier] ?? [];
}

export function hasFeature(tier: SubscriptionTier, feature: Feature): boolean {
  return getFeaturesForTier(tier).includes(feature);
}
