"use client";

import { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { Capability, CapabilityGap, CapabilityGapAnalysisRun, Opportunity } from "@/types/api";
import {
  Brain, Plus, ChevronDown, ChevronUp, AlertTriangle, CheckCircle2, TrendingUp,
  Target, Loader2, XCircle, Clock, DollarSign, Users2,
} from "lucide-react";

const CATEGORIES = [
  "technical", "management", "past_performance", "financial",
  "security_clearance", "compliance", "operational", "other"
];

const PROFICIENCY_LABELS = ["", "Beginner", "Basic", "Intermediate", "Advanced", "Expert"];

function ProficiencyBar({ level }: { level: number | null }) {
  const colors = ["", "bg-red-400", "bg-orange-400", "bg-amber-400", "bg-blue-400", "bg-emerald-400"];
  const lvl = level ?? 0;
  return (
    <div className="flex gap-0.5">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className={cn("h-2 w-5 rounded-sm", i < lvl ? colors[lvl] : "bg-secondary")} />
      ))}
    </div>
  );
}

export function CapabilityView() {
  const queryClient = useQueryClient();
  const [expanded, setExpanded] = useState<string | null>(null);
  const [showAdd, setShowAdd] = useState(false);
  const [categoryFilter, setCategoryFilter] = useState("");

  const { data: capabilities = [], isLoading } = useQuery({
    queryKey: ["capabilities", categoryFilter],
    queryFn: () => api.getCapabilities({ category: categoryFilter || undefined }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteCapability(id),
    onSuccess: () => {
      toast.success("Capability removed");
      queryClient.invalidateQueries({ queryKey: ["capabilities"] });
    },
  });

  const caps = capabilities as Capability[];
  const withGaps = caps.filter((c) => c.gap_score != null && c.gap_score > 30);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Capabilities & Gap Analysis</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            {caps.length} capabilities · {withGaps.length} gaps identified
          </p>
        </div>
        <button onClick={() => setShowAdd(true)}
          className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition-colors">
          <Plus className="w-4 h-4" />
          Add Capability
        </button>
      </div>

      <OpportunityGapAnalysisSection />

      {/* Summary cards */}
      {withGaps.length > 0 && (
        <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle className="w-4 h-4 text-amber-400" />
            <span className="text-sm font-medium text-amber-400">Capability Gaps Requiring Attention</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {withGaps.map((c) => (
              <span key={c.id} className="text-xs bg-amber-500/10 border border-amber-500/20 text-amber-300 px-2 py-0.5 rounded-full">
                {c.name} ({c.gap_score?.toFixed(0)}% gap)
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Filter */}
      <div className="flex gap-2">
        <select value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value)}
          className="px-3 py-2 bg-card border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/50">
          <option value="">All categories</option>
          {CATEGORIES.map((c) => (
            <option key={c} value={c}>{c.charAt(0).toUpperCase() + c.slice(1).replace("_", " ")}</option>
          ))}
        </select>
      </div>

      {/* Capability list */}
      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-16 bg-card border border-border rounded-lg animate-pulse" />
          ))}
        </div>
      ) : caps.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground">
          <Brain className="w-12 h-12 mx-auto mb-3 opacity-20" />
          <p className="font-medium">No capabilities registered</p>
          <p className="text-sm mt-1">Add your company capabilities to enable gap analysis.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {caps.map((cap) => (
            <div key={cap.id} className="bg-card border border-border rounded-lg overflow-hidden">
              <button onClick={() => setExpanded(expanded === cap.id ? null : cap.id)}
                className="w-full text-left px-4 py-3">
                <div className="flex items-center gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-medium">{cap.name}</p>
                      {cap.is_certified && (
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                      )}
                      <span className="text-xs bg-secondary text-muted-foreground px-1.5 py-0.5 rounded">
                        {cap.category.replace("_", " ")}
                      </span>
                    </div>
                    {cap.description && (
                      <p className="text-xs text-muted-foreground mt-0.5 truncate">{cap.description}</p>
                    )}
                  </div>
                  <div className="flex items-center gap-4 mr-2">
                    <div className="text-right">
                      <ProficiencyBar level={cap.proficiency_level} />
                      <p className="text-xs text-muted-foreground mt-0.5">{PROFICIENCY_LABELS[cap.proficiency_level ?? 0]}</p>
                    </div>
                    {cap.gap_score != null && (
                      <div className="text-right">
                        <p className={cn("text-sm font-mono font-bold",
                          cap.gap_score > 60 ? "text-red-400" : cap.gap_score > 30 ? "text-amber-400" : "text-emerald-400")}>
                          {cap.gap_score.toFixed(0)}%
                        </p>
                        <p className="text-xs text-muted-foreground">gap</p>
                      </div>
                    )}
                  </div>
                  {expanded === cap.id
                    ? <ChevronUp className="w-4 h-4 text-muted-foreground shrink-0" />
                    : <ChevronDown className="w-4 h-4 text-muted-foreground shrink-0" />
                  }
                </div>
              </button>

              {expanded === cap.id && (
                <div className="px-4 pb-4 border-t border-border/50 pt-4 space-y-3">
                  {cap.certifications?.length > 0 && (
                    <div>
                      <p className="text-xs text-muted-foreground mb-1">Certifications</p>
                      <div className="flex flex-wrap gap-1.5">
                        {(cap.certifications as string[]).map((cert) => (
                          <span key={cert} className="text-xs bg-blue-500/10 text-blue-400 border border-blue-500/20 px-2 py-0.5 rounded-full">
                            {cert}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  {cap.gap_analysis && (
                    <div className="bg-background/50 rounded-md p-3">
                      <p className="text-xs font-medium text-muted-foreground mb-1 flex items-center gap-1">
                        <TrendingUp className="w-3.5 h-3.5" />
                        Gap Analysis
                      </p>
                      <pre className="text-xs text-foreground/80 whitespace-pre-wrap">
                        {JSON.stringify(cap.gap_analysis, null, 2)}
                      </pre>
                    </div>
                  )}
                  {cap.improvement_plan && (
                    <div className="bg-background/50 rounded-md p-3">
                      <p className="text-xs font-medium text-muted-foreground mb-1">Improvement Plan</p>
                      <p className="text-sm">{cap.improvement_plan}</p>
                    </div>
                  )}
                  <button onClick={() => deleteMutation.mutate(cap.id)}
                    className="text-xs text-red-400 hover:underline">
                    Remove capability
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {showAdd && (
        <AddCapabilityModal
          onClose={() => setShowAdd(false)}
          onCreated={() => { setShowAdd(false); queryClient.invalidateQueries({ queryKey: ["capabilities"] }); }}
        />
      )}
    </div>
  );
}

function AddCapabilityModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    name: "", description: "", category: "technical",
    proficiency_level: "3", is_certified: false, certifications: "", naics_codes: "",
  });

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      await api.createCapability({
        name: form.name,
        description: form.description || null,
        category: form.category,
        proficiency_level: parseInt(form.proficiency_level),
        is_certified: form.is_certified,
        certifications: form.certifications ? form.certifications.split(",").map((s) => s.trim()).filter(Boolean) : [],
        naics_codes: form.naics_codes ? form.naics_codes.split(",").map((s) => s.trim()).filter(Boolean) : [],
      });
      toast.success("Capability added");
      onCreated();
    } catch {
      toast.error("Failed to add capability");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-card border border-border rounded-xl w-full max-w-lg p-6">
        <h2 className="font-semibold text-lg mb-4">Add Capability</h2>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="block text-xs font-medium mb-1 text-muted-foreground">Capability Name *</label>
            <input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
              placeholder="Cybersecurity Operations" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium mb-1 text-muted-foreground">Category</label>
              <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}
                className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none">
                {CATEGORIES.map((c) => <option key={c} value={c}>{c.replace("_", " ")}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium mb-1 text-muted-foreground">Proficiency (1–5)</label>
              <select value={form.proficiency_level} onChange={(e) => setForm({ ...form, proficiency_level: e.target.value })}
                className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none">
                {[1, 2, 3, 4, 5].map((n) => <option key={n} value={n}>{n} – {PROFICIENCY_LABELS[n]}</option>)}
              </select>
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium mb-1 text-muted-foreground">Description</label>
            <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })}
              rows={2} className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary/50"
              placeholder="Brief description of this capability" />
          </div>
          <div>
            <label className="block text-xs font-medium mb-1 text-muted-foreground">Certifications (comma separated)</label>
            <input value={form.certifications} onChange={(e) => setForm({ ...form, certifications: e.target.value })}
              className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
              placeholder="ISO 27001, CMMC Level 2, FedRAMP" />
          </div>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={form.is_certified} onChange={(e) => setForm({ ...form, is_certified: e.target.checked })}
              className="rounded" />
            Has current certifications
          </label>
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose}
              className="flex-1 py-2 border border-border rounded-md text-sm hover:bg-secondary transition-colors">
              Cancel
            </button>
            <button type="submit" disabled={loading}
              className="flex-1 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50">
              {loading ? "Adding…" : "Add Capability"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// A gap analysis run is a background Celery task (see run_capability_gap_analysis
// in cios/tasks/gap_analysis.py) — same "pending until the poll shows a terminal
// status" pattern as opportunity-view.tsx's "Run AI Analysis" and the Competitive
// Intelligence landscape analysis.
const ANALYSIS_TIMEOUT_SECONDS = 300;

function formatElapsed(startMs: number, nowMs: number): string {
  const elapsedSec = Math.max(0, Math.floor((nowMs - startMs) / 1000));
  const minutes = Math.floor(elapsedSec / 60);
  const seconds = elapsedSec % 60;
  return minutes > 0 ? `${minutes}m ${seconds}s` : `${seconds}s`;
}

const SEVERITY_STYLES: Record<string, string> = {
  critical: "border-red-500/40 bg-red-500/5",
  major: "border-orange-500/40 bg-orange-500/5",
  moderate: "border-amber-500/40 bg-amber-500/5",
  minor: "border-border bg-card",
};

const SEVERITY_BADGE: Record<string, string> = {
  critical: "bg-red-500/20 text-red-400",
  major: "bg-orange-500/20 text-orange-400",
  moderate: "bg-amber-500/20 text-amber-400",
  minor: "bg-secondary text-muted-foreground",
};

function OpportunityGapAnalysisSection() {
  const queryClient = useQueryClient();
  const [opportunityId, setOpportunityId] = useState("");
  const [pendingSince, setPendingSince] = useState<number | null>(null);
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (pendingSince == null) return;
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, [pendingSince]);

  const { data: opportunities = [] } = useQuery({
    queryKey: ["opportunities-for-gap-analysis"],
    queryFn: async () => (await api.getOpportunities({ page_size: 100 }))?.items ?? [],
  });
  const opps = opportunities as Opportunity[];

  const { data: run, isLoading: runLoading } = useQuery({
    queryKey: ["capability-gap-analysis-run", opportunityId],
    queryFn: async () => {
      try {
        return (await api.getLatestCapabilityGapAnalysisRun(opportunityId)) as CapabilityGapAnalysisRun;
      } catch {
        return null;
      }
    },
    enabled: !!opportunityId,
    refetchInterval: (query) => (query.state.data?.status === "pending" ? 5_000 : false),
  });

  const { data: gaps = [] } = useQuery({
    queryKey: ["capability-gaps-for-opportunity", opportunityId, run?.id],
    queryFn: () => api.getCapabilityGaps({ opportunity_id: opportunityId }),
    enabled: !!opportunityId && run?.status === "completed",
  });
  const opportunityGaps = gaps as CapabilityGap[];

  // Clear the pending marker (and toast) once a poll shows a terminal status,
  // or once it's been in flight longer than makes sense to keep waiting.
  useEffect(() => {
    if (pendingSince == null) return;
    if (run?.status === "completed") {
      setPendingSince(null);
      toast.success("Capability gap analysis complete");
      queryClient.invalidateQueries({ queryKey: ["capability-gaps-for-opportunity"] });
    } else if (run?.status === "failed") {
      setPendingSince(null);
      toast.error(run.error_message || "Capability gap analysis failed");
    } else if (Date.now() - pendingSince > ANALYSIS_TIMEOUT_SECONDS * 1000) {
      setPendingSince(null);
      toast.error("Analysis is taking longer than expected — it may have failed. Try again.");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [run?.status, pendingSince]);

  const analyzeMutation = useMutation({
    mutationFn: () => api.analyzeCapabilityGaps(opportunityId),
    onSuccess: (data) => {
      setPendingSince(Date.now());
      queryClient.setQueryData(["capability-gap-analysis-run", opportunityId], data);
      toast.success("Capability gap analysis queued");
    },
    onError: () => toast.error("Failed to start analysis — please try again"),
  });

  const isPending = pendingSince != null || run?.status === "pending";

  return (
    <div className="bg-card border border-border rounded-lg p-4 space-y-4">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-2">
          <Target className="w-4 h-4 text-primary" />
          <h2 className="font-semibold text-sm">Opportunity Gap Analysis</h2>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={opportunityId}
            onChange={(e) => setOpportunityId(e.target.value)}
            className="px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 min-w-[220px]"
          >
            <option value="">Select an opportunity…</option>
            {opps.map((o) => (
              <option key={o.id} value={o.id}>{o.title}</option>
            ))}
          </select>
          <button
            onClick={() => analyzeMutation.mutate()}
            disabled={!opportunityId || isPending}
            className="flex items-center gap-2 px-3 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50"
          >
            {isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Target className="w-4 h-4" />}
            {isPending ? "Analyzing…" : "Analyze Gaps"}
          </button>
        </div>
      </div>

      {!opportunityId && (
        <p className="text-xs text-muted-foreground">
          Pick an opportunity to see what stands between your org and its Winning Profile —
          each gap comes with a closure recommendation, timeline, and cost band.
        </p>
      )}

      {opportunityId && isPending && (
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
          Analyzing capability gaps{pendingSince != null ? ` — ${formatElapsed(pendingSince, now)} elapsed` : ""}
        </div>
      )}

      {opportunityId && !isPending && !runLoading && run?.status === "failed" && (
        <div className="flex items-start gap-2 text-xs text-red-400 bg-red-500/5 border border-red-500/30 rounded-md p-3">
          <XCircle className="w-4 h-4 shrink-0 mt-0.5" />
          <div>
            <p className="font-medium">Analysis failed</p>
            <p className="mt-0.5 text-red-400/80">{run.error_message}</p>
          </div>
        </div>
      )}

      {opportunityId && !isPending && !runLoading && !run && (
        <p className="text-xs text-muted-foreground">No analysis run yet for this opportunity.</p>
      )}

      {opportunityId && !isPending && run?.status === "completed" && (
        <div className="space-y-2">
          <div className="text-xs text-muted-foreground">
            {run.gap_count ?? 0} gap{run.gap_count === 1 ? "" : "s"} identified
          </div>
          {opportunityGaps
            .slice()
            .sort((a, b) => SEVERITY_ORDER.indexOf(a.severity) - SEVERITY_ORDER.indexOf(b.severity))
            .map((gap) => (
              <GapCard key={gap.id} gap={gap} />
            ))}
        </div>
      )}
    </div>
  );
}

const SEVERITY_ORDER = ["critical", "major", "moderate", "minor"];

function GapCard({ gap }: { gap: CapabilityGap }) {
  const remediation = (gap.remediation_options?.[0] ?? null) as {
    recommendation?: string;
    action_type?: string;
    effort?: string;
    feasibility?: string;
    cost_band?: string;
  } | null;

  return (
    <div className={cn("border rounded-lg p-3", SEVERITY_STYLES[gap.severity] ?? SEVERITY_STYLES.minor)}>
      <div className="flex items-center gap-2 flex-wrap">
        <span className={cn("text-xs px-1.5 py-0.5 rounded font-medium", SEVERITY_BADGE[gap.severity] ?? SEVERITY_BADGE.minor)}>
          {gap.severity}
        </span>
        <p className="text-sm font-medium">{gap.gap_name}</p>
        <span className="text-xs bg-secondary text-muted-foreground px-1.5 py-0.5 rounded">
          {gap.category.replace("_", " ")}
        </span>
      </div>

      {gap.description && (
        <p className="text-xs text-muted-foreground mt-1.5">{gap.description}</p>
      )}

      <div className="flex flex-wrap items-center gap-3 mt-2 text-xs text-muted-foreground">
        {gap.estimated_time_to_close_days != null && (
          <span className="flex items-center gap-1"><Clock className="w-3 h-3" />
            ~{Math.round(gap.estimated_time_to_close_days / 30)} mo to close
          </span>
        )}
        {gap.estimated_cost_to_close != null && (
          <span className="flex items-center gap-1"><DollarSign className="w-3 h-3" />
            {remediation?.cost_band ?? ""} (~${Math.round(gap.estimated_cost_to_close).toLocaleString()})
          </span>
        )}
        {gap.teaming_recommendation && (
          <span className="flex items-center gap-1 text-blue-400"><Users2 className="w-3 h-3" />Teaming opportunity</span>
        )}
      </div>

      {remediation?.recommendation && (
        <div className="bg-background/50 rounded-md p-2.5 mt-2">
          <p className="text-xs font-medium text-muted-foreground mb-1">Recommended Closure</p>
          <p className="text-xs">{remediation.recommendation}</p>
        </div>
      )}
    </div>
  );
}
