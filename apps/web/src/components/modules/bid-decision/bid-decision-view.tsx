"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { formatCurrency, getScoreColor, cn } from "@/lib/utils";
import { BarChart3, Plus, ChevronDown, ChevronUp, CheckCircle2, XCircle, AlertCircle } from "lucide-react";

interface BidDecision {
  id: string;
  opportunity_title: string;
  opportunity_id: string;
  decision: string | null;
  overall_score: number | null;
  strategic_fit_score: number | null;
  win_probability_score: number | null;
  past_performance_score: number | null;
  capability_score: number | null;
  competitive_position_score: number | null;
  cost_of_bid_score: number | null;
  risk_score: number | null;
  relationship_score: number | null;
  go_no_go_threshold: number;
  rationale: string | null;
  risk_factors: Record<string, unknown>[] | null;
  created_at: string;
  analyzed_at: string | null;
}

const DECISION_ICONS = {
  BID: <CheckCircle2 className="w-5 h-5 text-emerald-400" />,
  NO_BID: <XCircle className="w-5 h-5 text-red-400" />,
  CONDITIONAL_BID: <AlertCircle className="w-5 h-5 text-amber-400" />,
};

const DECISION_STYLES: Record<string, string> = {
  BID: "border-emerald-500/40 bg-emerald-500/5",
  NO_BID: "border-red-500/40 bg-red-500/5",
  CONDITIONAL_BID: "border-amber-500/40 bg-amber-500/5",
};

const SCORE_FACTORS = [
  { key: "strategic_fit_score", label: "Strategic Fit" },
  { key: "win_probability_score", label: "Win Probability" },
  { key: "past_performance_score", label: "Past Performance" },
  { key: "capability_score", label: "Capability Match" },
  { key: "competitive_position_score", label: "Competitive Position" },
  { key: "cost_of_bid_score", label: "Cost of Bid" },
  { key: "risk_score", label: "Risk" },
  { key: "relationship_score", label: "Relationship" },
] as const;

export function BidDecisionView() {
  const queryClient = useQueryClient();
  const [expanded, setExpanded] = useState<string | null>(null);
  const [showAdd, setShowAdd] = useState(false);

  const { data: decisions = [], isLoading } = useQuery({
    queryKey: ["bid-decisions"],
    queryFn: () => api.getBidDecisions(),
  });

  const summary = {
    bid: (decisions as BidDecision[]).filter((d) => d.decision === "BID").length,
    no_bid: (decisions as BidDecision[]).filter((d) => d.decision === "NO_BID").length,
    conditional: (decisions as BidDecision[]).filter((d) => d.decision === "CONDITIONAL_BID").length,
    pending: (decisions as BidDecision[]).filter((d) => !d.decision).length,
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Bid / No-Bid Engine</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Shipley-framework capture scoring across {(decisions as BidDecision[]).length} decisions
          </p>
        </div>
        <button
          onClick={() => setShowAdd(true)}
          className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition-colors"
        >
          <Plus className="w-4 h-4" />
          New Analysis
        </button>
      </div>

      {/* Summary row */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: "Bid", count: summary.bid, color: "text-emerald-400" },
          { label: "No Bid", count: summary.no_bid, color: "text-red-400" },
          { label: "Conditional", count: summary.conditional, color: "text-amber-400" },
          { label: "Pending Analysis", count: summary.pending, color: "text-muted-foreground" },
        ].map((s) => (
          <div key={s.label} className="bg-card border border-border rounded-lg p-4 text-center">
            <div className={cn("text-3xl font-bold font-mono", s.color)}>{s.count}</div>
            <div className="text-xs text-muted-foreground mt-1">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Decision list */}
      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-20 bg-card border border-border rounded-lg animate-pulse" />
          ))}
        </div>
      ) : (decisions as BidDecision[]).length === 0 ? (
        <div className="text-center py-16 text-muted-foreground">
          <BarChart3 className="w-12 h-12 mx-auto mb-3 opacity-20" />
          <p className="font-medium">No bid decisions yet</p>
          <p className="text-sm mt-1">Run a Bid/No-Bid analysis on an opportunity to get started.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {(decisions as BidDecision[]).map((d) => (
            <div
              key={d.id}
              className={cn(
                "border rounded-lg overflow-hidden transition-colors",
                d.decision ? DECISION_STYLES[d.decision] : "border-border bg-card"
              )}
            >
              <button
                onClick={() => setExpanded(expanded === d.id ? null : d.id)}
                className="w-full text-left p-4"
              >
                <div className="flex items-center gap-3">
                  {d.decision && DECISION_ICONS[d.decision as keyof typeof DECISION_ICONS]}
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-sm truncate">{d.opportunity_title}</p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {d.analyzed_at ? `Analyzed ${new Date(d.analyzed_at).toLocaleDateString()}` : "Pending analysis"}
                    </p>
                  </div>
                  {d.overall_score != null && (
                    <div className="text-right mr-2">
                      <div className={cn("text-2xl font-bold font-mono", getScoreColor(d.overall_score))}>
                        {d.overall_score}
                      </div>
                      <div className="text-xs text-muted-foreground">/ 100</div>
                    </div>
                  )}
                  {expanded === d.id ? (
                    <ChevronUp className="w-4 h-4 text-muted-foreground shrink-0" />
                  ) : (
                    <ChevronDown className="w-4 h-4 text-muted-foreground shrink-0" />
                  )}
                </div>
              </button>

              {expanded === d.id && (
                <div className="px-4 pb-4 space-y-4 border-t border-border/50 pt-4">
                  {/* Threshold indicator */}
                  {d.overall_score != null && (
                    <div className="flex items-center gap-2 text-xs">
                      <span className="text-muted-foreground">Go/No-Go threshold:</span>
                      <span className="font-mono">{d.go_no_go_threshold}</span>
                      <span className={d.overall_score >= d.go_no_go_threshold ? "text-emerald-400" : "text-red-400"}>
                        {d.overall_score >= d.go_no_go_threshold ? "✓ Exceeds threshold" : "✗ Below threshold"}
                      </span>
                    </div>
                  )}

                  {/* Factor scores */}
                  <div className="grid grid-cols-2 gap-2">
                    {SCORE_FACTORS.map(({ key, label }) => {
                      const score = d[key as keyof BidDecision] as number | null;
                      return score != null ? (
                        <div key={key} className="flex items-center justify-between text-sm">
                          <span className="text-muted-foreground text-xs">{label}</span>
                          <div className="flex items-center gap-2">
                            <div className="w-20 h-1.5 bg-secondary rounded-full overflow-hidden">
                              <div
                                className={cn("h-full rounded-full", getScoreColor(score).replace("text-", "bg-"))}
                                style={{ width: `${score}%` }}
                              />
                            </div>
                            <span className={cn("text-xs font-mono w-6 text-right", getScoreColor(score))}>
                              {score}
                            </span>
                          </div>
                        </div>
                      ) : null;
                    })}
                  </div>

                  {/* Rationale */}
                  {d.rationale && (
                    <div className="bg-background/50 rounded-md p-3">
                      <p className="text-xs font-medium text-muted-foreground mb-1">AI Rationale</p>
                      <p className="text-sm">{d.rationale}</p>
                    </div>
                  )}

                  {/* Risk factors */}
                  {d.risk_factors && d.risk_factors.length > 0 && (
                    <div>
                      <p className="text-xs font-medium text-muted-foreground mb-2">Risk Factors</p>
                      <div className="space-y-1">
                        {d.risk_factors.map((r, i) => (
                          <div key={i} className="flex items-start gap-2 text-xs">
                            <AlertCircle className="w-3 h-3 text-amber-400 shrink-0 mt-0.5" />
                            <span>{(r as { description?: string }).description || JSON.stringify(r)}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {showAdd && (
        <AddBidDecisionModal
          onClose={() => setShowAdd(false)}
          onCreated={() => { setShowAdd(false); queryClient.invalidateQueries({ queryKey: ["bid-decisions"] }); }}
        />
      )}
    </div>
  );
}

function AddBidDecisionModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [loading, setLoading] = useState(false);
  const [opportunityId, setOpportunityId] = useState("");
  const [threshold, setThreshold] = useState("65");

  const { data: opportunities = [] } = useQuery({
    queryKey: ["opportunities-list"],
    queryFn: () => api.getOpportunities(),
  });

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!opportunityId) { toast.error("Select an opportunity"); return; }
    setLoading(true);
    try {
      await api.createBidDecision({ opportunity_id: opportunityId, go_no_go_threshold: parseInt(threshold) });
      toast.success("Bid/No-Bid analysis created — run AI analysis to score");
      onCreated();
    } catch {
      toast.error("Failed to create analysis");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-card border border-border rounded-xl w-full max-w-md p-6">
        <h2 className="font-semibold text-lg mb-4">New Bid/No-Bid Analysis</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium mb-1.5 text-muted-foreground">Opportunity</label>
            <select value={opportunityId} onChange={(e) => setOpportunityId(e.target.value)}
              className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/50">
              <option value="">Select opportunity…</option>
              {(opportunities as { id: string; title: string }[]).map((o) => (
                <option key={o.id} value={o.id}>{o.title}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium mb-1.5 text-muted-foreground">
              Go/No-Go Threshold (0–100) — default 65
            </label>
            <input type="number" min={0} max={100} value={threshold}
              onChange={(e) => setThreshold(e.target.value)}
              className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/50" />
          </div>
          <div className="flex gap-3 pt-1">
            <button type="button" onClick={onClose}
              className="flex-1 py-2 border border-border rounded-md text-sm hover:bg-secondary transition-colors">
              Cancel
            </button>
            <button type="submit" disabled={loading}
              className="flex-1 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50">
              {loading ? "Creating…" : "Create"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
