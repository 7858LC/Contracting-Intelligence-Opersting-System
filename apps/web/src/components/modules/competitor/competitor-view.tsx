"use client";

import { useEffect, useMemo, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { Competitor, CompetitiveLandscapeAnalysis, LandscapeContender, Opportunity } from "@/types/api";
import {
  Building2,
  Plus,
  Shield,
  TrendingUp,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Crosshair,
  Loader2,
  Users,
  XCircle,
} from "lucide-react";

// A landscape analysis is a background Celery task (see run_competitive_analysis
// in cios/tasks/competitive_intel.py) — same "pending until the poll shows a
// terminal status" pattern as opportunity-view.tsx's "Run AI Analysis".
const ANALYSIS_TIMEOUT_SECONDS = 300;

function formatElapsed(startMs: number, nowMs: number): string {
  const elapsedSec = Math.max(0, Math.floor((nowMs - startMs) / 1000));
  const minutes = Math.floor(elapsedSec / 60);
  const seconds = elapsedSec % 60;
  return minutes > 0 ? `${minutes}m ${seconds}s` : `${seconds}s`;
}

const THREAT_STYLES: Record<string, string> = {
  critical: "border-red-500/40 bg-red-500/5",
  high: "border-orange-500/40 bg-orange-500/5",
  medium: "border-amber-500/40 bg-amber-500/5",
  low: "border-border bg-card",
};

const THREAT_BADGE: Record<string, string> = {
  critical: "bg-red-500/20 text-red-400",
  high: "bg-orange-500/20 text-orange-400",
  medium: "bg-amber-500/20 text-amber-400",
  low: "bg-secondary text-muted-foreground",
};

function formatVolume(v: number): string {
  if (v >= 1e9) return `$${(v / 1e9).toFixed(1)}B`;
  if (v >= 1e6) return `$${(v / 1e6).toFixed(0)}M`;
  if (v >= 1e3) return `$${(v / 1e3).toFixed(0)}K`;
  return `$${v}`;
}

export function CompetitorView() {
  const queryClient = useQueryClient();
  const [expanded, setExpanded] = useState<string | null>(null);
  const [showAdd, setShowAdd] = useState(false);
  const [threatFilter, setThreatFilter] = useState("");

  const { data: competitors = [], isLoading } = useQuery({
    queryKey: ["competitors", threatFilter],
    queryFn: () => api.getCompetitors({ threat_level: threatFilter || undefined }),
  });

  const comps = competitors as Competitor[];

  const threatCount = {
    critical: comps.filter((c) => c.threat_level === "critical").length,
    high: comps.filter((c) => c.threat_level === "high").length,
    medium: comps.filter((c) => c.threat_level === "medium").length,
    low: comps.filter((c) => c.threat_level === "low").length,
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Competitive Intelligence</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            {comps.length} competitors tracked
          </p>
        </div>
        <button onClick={() => setShowAdd(true)}
          className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition-colors">
          <Plus className="w-4 h-4" />
          Add Competitor
        </button>
      </div>

      <LandscapeAnalysisSection />

      {/* Threat matrix summary */}
      <div className="grid grid-cols-4 gap-3">
        {[
          { level: "critical", label: "Critical Threats", count: threatCount.critical, color: "text-red-400" },
          { level: "high", label: "High Threats", count: threatCount.high, color: "text-orange-400" },
          { level: "medium", label: "Medium Threats", count: threatCount.medium, color: "text-amber-400" },
          { level: "low", label: "Low Threats", count: threatCount.low, color: "text-muted-foreground" },
        ].map((t) => (
          <button key={t.level} onClick={() => setThreatFilter(threatFilter === t.level ? "" : t.level)}
            className={cn("bg-card border rounded-lg p-4 text-center transition-colors",
              threatFilter === t.level ? "border-primary" : "border-border hover:border-border/80")}>
            <div className={cn("text-3xl font-bold font-mono", t.color)}>{t.count}</div>
            <div className="text-xs text-muted-foreground mt-1">{t.label}</div>
          </button>
        ))}
      </div>

      {/* Competitor list */}
      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-20 bg-card border border-border rounded-lg animate-pulse" />
          ))}
        </div>
      ) : comps.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground">
          <Building2 className="w-12 h-12 mx-auto mb-3 opacity-20" />
          <p className="font-medium">No competitors tracked yet</p>
          <p className="text-sm mt-1">Add competitors to build your competitive intelligence database.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {comps.map((comp) => {
            const strengths = (comp.known_strengths ?? []) as string[];
            const weaknesses = (comp.known_weaknesses ?? []) as string[];
            const socioeconomicStatuses = (comp.socioeconomic_statuses ?? []) as string[];
            const activeClearances = (comp.active_clearances ?? []) as string[];
            const certifications = (comp.certifications ?? []) as string[];
            return (
            <div key={comp.id}
              className={cn("border rounded-lg overflow-hidden", THREAT_STYLES[comp.threat_level || "low"])}>
              <button onClick={() => setExpanded(expanded === comp.id ? null : comp.id)}
                className="w-full text-left px-4 py-3">
                <div className="flex items-center gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-medium">{comp.company_name}</p>
                      {comp.threat_level && (
                        <span className={cn("text-xs px-1.5 py-0.5 rounded font-medium", THREAT_BADGE[comp.threat_level])}>
                          {comp.threat_level}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-3 mt-0.5 text-xs text-muted-foreground">
                      {comp.cage_code && <span>CAGE: {comp.cage_code}</span>}
                      {comp.annual_contract_volume && <span>{formatVolume(comp.annual_contract_volume)}/yr</span>}
                      {comp.win_rate_estimate != null && <span>{(comp.win_rate_estimate * 100).toFixed(0)}% win rate</span>}
                      {comp.pricing_tendency && <span>{comp.pricing_tendency}</span>}
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-1 max-w-[200px]">
                    {socioeconomicStatuses.slice(0, 2).map((s) => (
                      <span key={s} className="text-xs bg-blue-500/10 text-blue-400 px-1.5 py-0.5 rounded">{s}</span>
                    ))}
                    {activeClearances.slice(0, 2).map((c) => (
                      <span key={c} className="text-xs bg-violet-500/10 text-violet-400 px-1.5 py-0.5 rounded flex items-center gap-0.5">
                        <Shield className="w-2.5 h-2.5" />{c}
                      </span>
                    ))}
                  </div>
                  {expanded === comp.id
                    ? <ChevronUp className="w-4 h-4 text-muted-foreground shrink-0" />
                    : <ChevronDown className="w-4 h-4 text-muted-foreground shrink-0" />
                  }
                </div>
              </button>

              {expanded === comp.id && (
                <div className="px-4 pb-4 border-t border-border/50 pt-4 space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    {strengths.length > 0 && (
                      <div>
                        <p className="text-xs text-muted-foreground mb-1.5 flex items-center gap-1">
                          <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />
                          Strengths
                        </p>
                        <ul className="space-y-1">
                          {strengths.map((s) => (
                            <li key={s} className="text-xs flex items-start gap-1.5">
                              <span className="text-emerald-400 shrink-0">+</span>
                              {s}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {weaknesses.length > 0 && (
                      <div>
                        <p className="text-xs text-muted-foreground mb-1.5 flex items-center gap-1">
                          <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
                          Weaknesses
                        </p>
                        <ul className="space-y-1">
                          {weaknesses.map((w) => (
                            <li key={w} className="text-xs flex items-start gap-1.5">
                              <span className="text-amber-400 shrink-0">−</span>
                              {w}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>

                  {certifications.length > 0 && (
                    <div>
                      <p className="text-xs text-muted-foreground mb-1.5">Certifications</p>
                      <div className="flex flex-wrap gap-1.5">
                        {certifications.map((c) => (
                          <span key={c} className="text-xs bg-secondary text-muted-foreground px-2 py-0.5 rounded">{c}</span>
                        ))}
                      </div>
                    </div>
                  )}

                  {comp.notes && (
                    <div className="bg-background/50 rounded-md p-3">
                      <p className="text-xs font-medium text-muted-foreground mb-1">Intel Notes</p>
                      <p className="text-sm">{comp.notes}</p>
                    </div>
                  )}
                </div>
              )}
            </div>
            );
          })}
        </div>
      )}

      {showAdd && (
        <AddCompetitorModal
          onClose={() => setShowAdd(false)}
          onCreated={() => { setShowAdd(false); queryClient.invalidateQueries({ queryKey: ["competitors"] }); }}
        />
      )}
    </div>
  );
}

function LandscapeAnalysisSection() {
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
    queryKey: ["opportunities-for-landscape"],
    queryFn: async () => (await api.getOpportunities({ page_size: 100 }))?.items ?? [],
  });
  const opps = opportunities as Opportunity[];

  const { data: analysis, isLoading: analysisLoading } = useQuery({
    queryKey: ["competitive-landscape-analysis", opportunityId],
    queryFn: async () => {
      try {
        return (await api.getLatestCompetitiveLandscapeAnalysis(opportunityId)) as CompetitiveLandscapeAnalysis;
      } catch {
        return null;
      }
    },
    enabled: !!opportunityId,
    refetchInterval: (query) => (query.state.data?.status === "pending" ? 5_000 : false),
  });

  // Clear the pending marker (and toast) once a poll shows a terminal status,
  // or once it's been in flight longer than makes sense to keep waiting.
  useEffect(() => {
    if (pendingSince == null) return;
    if (analysis?.status === "completed") {
      setPendingSince(null);
      toast.success("Competitive landscape analysis complete");
    } else if (analysis?.status === "failed") {
      setPendingSince(null);
      toast.error(analysis.error_message || "Competitive landscape analysis failed");
    } else if (Date.now() - pendingSince > ANALYSIS_TIMEOUT_SECONDS * 1000) {
      setPendingSince(null);
      toast.error("Analysis is taking longer than expected — it may have failed. Try again.");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [analysis?.status, pendingSince]);

  const analyzeMutation = useMutation({
    mutationFn: () => api.analyzeCompetitiveLandscape(opportunityId),
    onSuccess: (data) => {
      setPendingSince(Date.now());
      queryClient.setQueryData(["competitive-landscape-analysis", opportunityId], data);
      toast.success("Competitive landscape analysis queued");
    },
    onError: () => toast.error("Failed to start analysis — please try again"),
  });

  const isPending = pendingSince != null || analysis?.status === "pending";

  return (
    <div className="bg-card border border-border rounded-lg p-4 space-y-4">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-2">
          <Crosshair className="w-4 h-4 text-primary" />
          <h2 className="font-semibold text-sm">Competitive Landscape Analysis</h2>
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
            {isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Crosshair className="w-4 h-4" />}
            {isPending ? "Analyzing…" : "Analyze"}
          </button>
        </div>
      </div>

      {!opportunityId && (
        <p className="text-xs text-muted-foreground">
          Pick an opportunity to see who you&apos;re up against, ranked by Winning Profile alignment.
        </p>
      )}

      {opportunityId && isPending && (
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
          Analyzing competitive landscape{pendingSince != null ? ` — ${formatElapsed(pendingSince, now)} elapsed` : ""}
        </div>
      )}

      {opportunityId && !isPending && !analysisLoading && analysis?.status === "failed" && (
        <div className="flex items-start gap-2 text-xs text-red-400 bg-red-500/5 border border-red-500/30 rounded-md p-3">
          <XCircle className="w-4 h-4 shrink-0 mt-0.5" />
          <div>
            <p className="font-medium">Analysis failed</p>
            <p className="mt-0.5 text-red-400/80">{analysis.error_message}</p>
          </div>
        </div>
      )}

      {opportunityId && !isPending && !analysisLoading && !analysis && (
        <p className="text-xs text-muted-foreground">No analysis run yet for this opportunity.</p>
      )}

      {opportunityId && !isPending && analysis?.status === "completed" && (
        <div className="space-y-3">
          <div className="text-xs text-muted-foreground">
            {analysis.candidate_pool_size ?? 0} competing contractor{analysis.candidate_pool_size === 1 ? "" : "s"} identified
          </div>
          {analysis.front_runner && (
            <ContenderCard contender={analysis.front_runner} isFrontRunner />
          )}
          {analysis.next_tiers?.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
                <Users className="w-3.5 h-3.5" />
                Next Tier
              </p>
              {analysis.next_tiers.map((c) => (
                <ContenderCard key={c.contractor_id} contender={c} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ContenderCard({ contender, isFrontRunner }: { contender: LandscapeContender; isFrontRunner?: boolean }) {
  const strengths = (contender.known_strengths ?? []) as string[];
  const weaknesses = (contender.known_weaknesses ?? []) as string[];
  return (
    <div
      className={cn(
        "border rounded-lg p-3",
        isFrontRunner ? "border-primary/50 bg-primary/5" : THREAT_STYLES[contender.threat_level || "low"]
      )}
    >
      <div className="flex items-center gap-2 flex-wrap">
        {isFrontRunner && (
          <span className="text-[10px] font-bold uppercase tracking-wide px-1.5 py-0.5 rounded bg-primary/20 text-primary">
            Front Runner
          </span>
        )}
        {contender.rank != null && (
          <span className="text-xs text-muted-foreground">Rank #{contender.rank}</span>
        )}
        <p className="text-sm font-medium">{contender.contractor_name ?? "Unknown contractor"}</p>
        {contender.threat_level && (
          <span className={cn("text-xs px-1.5 py-0.5 rounded font-medium", THREAT_BADGE[contender.threat_level])}>
            {contender.threat_level}
          </span>
        )}
        {contender.alignment_score != null && (
          <span className="text-xs text-muted-foreground ml-auto">
            Alignment: {contender.alignment_score.toFixed(0)}
          </span>
        )}
      </div>
      <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
        {contender.pricing_tendency && <span>Pricing: {contender.pricing_tendency}</span>}
      </div>
      {(strengths.length > 0 || weaknesses.length > 0) && (
        <div className="grid grid-cols-2 gap-3 mt-2">
          {strengths.length > 0 && (
            <ul className="space-y-0.5">
              {strengths.slice(0, 3).map((s) => (
                <li key={s} className="text-xs flex items-start gap-1.5">
                  <span className="text-emerald-400 shrink-0">+</span>
                  {s}
                </li>
              ))}
            </ul>
          )}
          {weaknesses.length > 0 && (
            <ul className="space-y-0.5">
              {weaknesses.slice(0, 3).map((w) => (
                <li key={w} className="text-xs flex items-start gap-1.5">
                  <span className="text-amber-400 shrink-0">−</span>
                  {w}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
      {contender.notes && <p className="text-xs text-muted-foreground mt-2">{contender.notes}</p>}
    </div>
  );
}

function AddCompetitorModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    company_name: "", cage_code: "", annual_contract_volume: "",
    known_strengths: "", known_weaknesses: "", pricing_tendency: "",
    socioeconomic_statuses: "", active_clearances: "", certifications: "",
    win_rate_estimate: "", threat_level: "medium", notes: "",
  });

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      const split = (s: string) => s ? s.split(",").map((x) => x.trim()).filter(Boolean) : [];
      await api.createCompetitor({
        company_name: form.company_name,
        cage_code: form.cage_code || null,
        annual_contract_volume: form.annual_contract_volume ? parseFloat(form.annual_contract_volume) : null,
        known_strengths: split(form.known_strengths),
        known_weaknesses: split(form.known_weaknesses),
        pricing_tendency: form.pricing_tendency || null,
        socioeconomic_statuses: split(form.socioeconomic_statuses),
        active_clearances: split(form.active_clearances),
        certifications: split(form.certifications),
        win_rate_estimate: form.win_rate_estimate ? parseFloat(form.win_rate_estimate) / 100 : null,
        threat_level: form.threat_level,
        notes: form.notes || null,
      });
      toast.success("Competitor added");
      onCreated();
    } catch {
      toast.error("Failed to add competitor");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4 overflow-y-auto">
      <div className="bg-card border border-border rounded-xl w-full max-w-lg p-6 my-4">
        <h2 className="font-semibold text-lg mb-4">Add Competitor</h2>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium mb-1 text-muted-foreground">Company Name *</label>
              <input required value={form.company_name} onChange={(e) => setForm({ ...form, company_name: e.target.value })}
                className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                placeholder="Leidos" />
            </div>
            <div>
              <label className="block text-xs font-medium mb-1 text-muted-foreground">Threat Level</label>
              <select value={form.threat_level} onChange={(e) => setForm({ ...form, threat_level: e.target.value })}
                className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none">
                {["critical", "high", "medium", "low"].map((t) => (
                  <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium mb-1 text-muted-foreground">Annual Contract Volume ($)</label>
              <input type="number" value={form.annual_contract_volume} onChange={(e) => setForm({ ...form, annual_contract_volume: e.target.value })}
                className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                placeholder="500000000" />
            </div>
            <div>
              <label className="block text-xs font-medium mb-1 text-muted-foreground">Est. Win Rate (%)</label>
              <input type="number" min={0} max={100} value={form.win_rate_estimate} onChange={(e) => setForm({ ...form, win_rate_estimate: e.target.value })}
                className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                placeholder="35" />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium mb-1 text-muted-foreground">Strengths (comma separated)</label>
            <input value={form.known_strengths} onChange={(e) => setForm({ ...form, known_strengths: e.target.value })}
              className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
              placeholder="Incumbent, strong past performance, low pricing" />
          </div>
          <div>
            <label className="block text-xs font-medium mb-1 text-muted-foreground">Weaknesses (comma separated)</label>
            <input value={form.known_weaknesses} onChange={(e) => setForm({ ...form, known_weaknesses: e.target.value })}
              className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
              placeholder="High overhead, staff turnover, limited clearances" />
          </div>
          <div>
            <label className="block text-xs font-medium mb-1 text-muted-foreground">Price Positioning</label>
            <select value={form.pricing_tendency} onChange={(e) => setForm({ ...form, pricing_tendency: e.target.value })}
              className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none">
              <option value="">Unknown</option>
              <option value="lowest">Lowest price aggressive</option>
              <option value="low">Below market</option>
              <option value="market">At market rate</option>
              <option value="premium">Premium / best value</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium mb-1 text-muted-foreground">Socioeconomic Status</label>
            <input value={form.socioeconomic_statuses} onChange={(e) => setForm({ ...form, socioeconomic_statuses: e.target.value })}
              className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
              placeholder="Large Business, 8a" />
          </div>
          <div>
            <label className="block text-xs font-medium mb-1 text-muted-foreground">Active Clearances</label>
            <input value={form.active_clearances} onChange={(e) => setForm({ ...form, active_clearances: e.target.value })}
              className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
              placeholder="TS/SCI, Secret" />
          </div>
          <div>
            <label className="block text-xs font-medium mb-1 text-muted-foreground">Notes</label>
            <textarea value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })}
              rows={2} className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary/50"
              placeholder="Key intel, incumbent status, recent wins/losses" />
          </div>
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose}
              className="flex-1 py-2 border border-border rounded-md text-sm hover:bg-secondary transition-colors">
              Cancel
            </button>
            <button type="submit" disabled={loading}
              className="flex-1 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50">
              {loading ? "Adding…" : "Add Competitor"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
