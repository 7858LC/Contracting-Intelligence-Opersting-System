"use client";

import { useEffect, useMemo, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "@/lib/api";
import {
  formatCurrency,
  formatProbability,
  getScoreColor,
  getScoreLabel,
  getDaysUntil,
  cn,
} from "@/lib/utils";
import { Target, Plus, Search, Filter, Zap, Eye, FileText, TrendingUp } from "lucide-react";

const PIPELINE_STAGES = ["tracking", "qualifying", "capture", "proposal", "submitted", "awarded", "lost"];
const JURISDICTIONS = ["us_federal", "us_state", "us_local", "eu", "world_bank", "other"];
const STATUS_OPTIONS = ["open", "closed", "awarded", "cancelled"];

// Directors now run in parallel (see ceo_agent.py's orchestrate_full_assessment),
// so the realistic wall-clock cost is one director call plus the CEO synthesis
// call after it, not all six sequentially. Progress is capped short of 100% so
// the bar never implies "done" before analyzed_at actually lands — see
// bid-decision-view.tsx's identical pattern.
const EXPECTED_ANALYSIS_SECONDS = 180;
const PROGRESS_CAP_PERCENT = 92;
// If analyzed_at still hasn't landed by this point, the task most likely hit
// its soft_time_limit or exhausted its retries — surface that instead of
// leaving the spinner running forever with no explanation.
const ANALYSIS_TIMEOUT_SECONDS = 900;

function formatElapsed(startMs: number, nowMs: number): string {
  const elapsedSec = Math.max(0, Math.floor((nowMs - startMs) / 1000));
  const minutes = Math.floor(elapsedSec / 60);
  const seconds = elapsedSec % 60;
  return minutes > 0 ? `${minutes}m ${seconds}s` : `${seconds}s`;
}

interface Opportunity {
  id: string;
  title: string;
  agency: string;
  solicitation_number: string;
  status: string;
  pipeline_stage: string;
  estimated_value: number | null;
  response_due_date: string | null;
  award_probability_score: number | null;
  bid_no_bid_recommendation: string | null;
  procurement_rule_pack: string | null;
  naics_code: string | null;
  set_aside: string | null;
  jurisdiction: string | null;
  place_of_performance: string | null;
  created_at: string;
  analyzed_at: string | null;
}

const STAGE_COLORS: Record<string, string> = {
  tracking: "bg-slate-500/20 text-slate-400",
  qualifying: "bg-blue-500/20 text-blue-400",
  capture: "bg-violet-500/20 text-violet-400",
  proposal: "bg-amber-500/20 text-amber-400",
  submitted: "bg-cyan-500/20 text-cyan-400",
  awarded: "bg-emerald-500/20 text-emerald-400",
  lost: "bg-red-500/20 text-red-400",
};

const BID_COLORS: Record<string, string> = {
  BID: "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30",
  NO_BID: "bg-red-500/10 text-red-400 border border-red-500/30",
  CONDITIONAL_BID: "bg-amber-500/10 text-amber-400 border border-amber-500/30",
};

export function OpportunityView() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [stageFilter, setStageFilter] = useState("");
  const [showAdd, setShowAdd] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  // opportunity id -> epoch ms when "Run AI Analysis" was clicked. Unlike
  // bid decisions (every row exists specifically to be analyzed, so
  // !analyzed_at alone means "pending"), most opportunities in the pipeline
  // were never analyzed and never will be — polling every row with a null
  // score would poll forever for no reason. This tracks only opportunities
  // actually in flight, and is cleared once a poll shows analyzed_at newer
  // than the click, or after ANALYSIS_TIMEOUT_SECONDS elapses.
  const [pendingAnalysis, setPendingAnalysis] = useState<Record<string, number>>({});
  const [now, setNow] = useState(() => Date.now());

  const hasPending = Object.keys(pendingAnalysis).length > 0;
  useEffect(() => {
    if (!hasPending) return;
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, [hasPending]);

  const { data: oppsData, isLoading } = useQuery({
    queryKey: ["opportunities", search, stageFilter],
    queryFn: () => api.getOpportunities({ search: search || undefined, pipeline_stage: stageFilter || undefined, page_size: 100 }),
    refetchInterval: hasPending ? 8_000 : 30_000,
  });
  const opportunities = useMemo(() => (oppsData?.items ?? []) as Opportunity[], [oppsData]);
  const selected = opportunities.find((o) => o.id === selectedId) ?? null;

  // Clear (and toast) any pending marker once a poll shows the analysis
  // actually landed, and flag any that have blown past the timeout instead
  // of leaving the spinner running with no explanation.
  useEffect(() => {
    if (!hasPending) return;
    setPendingAnalysis((prev) => {
      let changed = false;
      const next = { ...prev };
      for (const [id, requestedAt] of Object.entries(prev)) {
        const opp = opportunities.find((o) => o.id === id);
        const analyzedAt = opp?.analyzed_at ? new Date(opp.analyzed_at).getTime() : null;
        if (analyzedAt && analyzedAt >= requestedAt) {
          delete next[id];
          changed = true;
          toast.success(`AI analysis complete for "${opp?.title ?? "opportunity"}"`);
        } else if (Date.now() - requestedAt > ANALYSIS_TIMEOUT_SECONDS * 1000) {
          delete next[id];
          changed = true;
          toast.error(`AI analysis for "${opp?.title ?? "opportunity"}" is taking longer than expected — it may have failed. Try again.`);
        }
      }
      return changed ? next : prev;
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [opportunities, hasPending]);

  const analyzeMutation = useMutation({
    mutationFn: (id: string) => api.analyzeOpportunity(id),
    onSuccess: (_data, id) => {
      setPendingAnalysis((prev) => ({ ...prev, [id]: Date.now() }));
      toast.success("AI analysis queued — usually a few minutes");
      queryClient.invalidateQueries({ queryKey: ["opportunities"] });
    },
    onError: () => toast.error("Analysis failed — please try again"),
  });

  const pipeline: Record<string, Opportunity[]> = {};
  PIPELINE_STAGES.forEach((s) => { pipeline[s] = []; });
  opportunities.forEach((o) => {
    const stage = pipeline[o.pipeline_stage] ? o.pipeline_stage : "tracking";
    pipeline[stage].push(o);
  });

  if (selected) {
    const pendingSince = pendingAnalysis[selected.id];
    return (
      <OpportunityDetail
        opp={selected}
        onBack={() => setSelectedId(null)}
        onAnalyze={() => analyzeMutation.mutate(selected.id)}
        analyzing={analyzeMutation.isPending || pendingSince != null}
        pendingSince={pendingSince}
        now={now}
      />
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Opportunity Intelligence</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            {(opportunities as Opportunity[]).length} opportunities in pipeline
          </p>
        </div>
        <button
          onClick={() => setShowAdd(true)}
          className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Add Opportunity
        </button>
      </div>

      {/* Search + filter */}
      <div className="flex gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search opportunities, agencies, solicitation numbers…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2 bg-card border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
          />
        </div>
        <select
          value={stageFilter}
          onChange={(e) => setStageFilter(e.target.value)}
          className="px-3 py-2 bg-card border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
        >
          <option value="">All stages</option>
          {PIPELINE_STAGES.map((s) => (
            <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
          ))}
        </select>
      </div>

      {/* Pipeline Kanban */}
      {isLoading ? (
        <div className="grid grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="bg-card border border-border rounded-lg p-4 space-y-3 animate-pulse">
              <div className="h-4 bg-secondary rounded w-20" />
              {Array.from({ length: 2 }).map((_, j) => (
                <div key={j} className="h-24 bg-secondary rounded" />
              ))}
            </div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-4 xl:grid-cols-7 gap-3 overflow-x-auto pb-2">
          {PIPELINE_STAGES.map((stage) => (
            <div key={stage} className="min-w-[200px]">
              <div className="flex items-center justify-between mb-2 px-1">
                <span className={cn("text-xs font-medium px-2 py-0.5 rounded-full", STAGE_COLORS[stage])}>
                  {stage.charAt(0).toUpperCase() + stage.slice(1)}
                </span>
                <span className="text-xs text-muted-foreground">{pipeline[stage].length}</span>
              </div>
              <div className="space-y-2">
                {pipeline[stage].map((opp) => (
                  <button
                    key={opp.id}
                    onClick={() => setSelectedId(opp.id)}
                    className="w-full text-left bg-card border border-border rounded-lg p-3 hover:border-primary/50 transition-colors group"
                  >
                    <p className="text-xs font-medium line-clamp-2 group-hover:text-primary transition-colors">
                      {opp.title}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1 truncate">{opp.agency}</p>
                    {opp.estimated_value && (
                      <p className="text-xs font-mono mt-1.5 text-emerald-400">
                        {formatCurrency(opp.estimated_value)}
                      </p>
                    )}
                    {opp.award_probability_score != null && (
                      <div className="mt-2">
                        <div className="flex items-center justify-between text-xs mb-0.5">
                          <span className="text-muted-foreground">P(win)</span>
                          <span className={getScoreColor(opp.award_probability_score * 100)}>
                            {formatProbability(opp.award_probability_score)}
                          </span>
                        </div>
                        <div className="h-1 bg-secondary rounded-full overflow-hidden">
                          <div
                            className={cn("h-full rounded-full", getScoreColor(opp.award_probability_score * 100).replace("text-", "bg-"))}
                            style={{ width: `${opp.award_probability_score * 100}%` }}
                          />
                        </div>
                      </div>
                    )}
                    {opp.bid_no_bid_recommendation && (
                      <span className={cn("inline-block mt-2 text-[10px] font-bold px-1.5 py-0.5 rounded", BID_COLORS[opp.bid_no_bid_recommendation] || "bg-secondary text-muted-foreground")}>
                        {opp.bid_no_bid_recommendation.replace("_", " ")}
                      </span>
                    )}
                    {pendingAnalysis[opp.id] != null && (
                      <span className="inline-flex items-center gap-1 mt-2 text-[10px] font-medium px-1.5 py-0.5 rounded bg-primary/10 text-primary">
                        <Zap className="w-2.5 h-2.5" />
                        Analyzing…
                      </span>
                    )}
                    {opp.response_due_date && (
                      <p className="text-[10px] text-muted-foreground mt-1">
                        Due {getDaysUntil(opp.response_due_date)}d
                      </p>
                    )}
                  </button>
                ))}
                {pipeline[stage].length === 0 && (
                  <div className="h-16 border border-dashed border-border rounded-lg flex items-center justify-center">
                    <span className="text-xs text-muted-foreground">Empty</span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {showAdd && <AddOpportunityModal onClose={() => setShowAdd(false)} onCreated={() => { setShowAdd(false); queryClient.invalidateQueries({ queryKey: ["opportunities"] }); }} />}
    </div>
  );
}

function OpportunityDetail({
  opp,
  onBack,
  onAnalyze,
  analyzing,
  pendingSince,
  now,
}: {
  opp: Opportunity;
  onBack: () => void;
  onAnalyze: () => void;
  analyzing: boolean;
  pendingSince?: number;
  now: number;
}) {
  const scoreNum = opp.award_probability_score != null ? Math.round(opp.award_probability_score * 100) : null;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <button onClick={onBack} className="text-sm text-muted-foreground hover:text-foreground transition-colors">
          ← Back
        </button>
        <h1 className="text-xl font-bold flex-1 line-clamp-1">{opp.title}</h1>
        <button
          onClick={onAnalyze}
          disabled={analyzing}
          className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50"
        >
          <Zap className="w-4 h-4" />
          {analyzing ? "Analyzing…" : "Run AI Analysis"}
        </button>
      </div>

      {pendingSince != null && (
        <div className="bg-card border border-border rounded-lg p-3">
          <div className="flex items-center justify-between text-xs mb-1.5">
            <span className="text-muted-foreground">
              AI analysis in progress — {formatElapsed(pendingSince, now)} elapsed (usually ~3 min)
            </span>
          </div>
          <div className="w-full h-1 bg-secondary rounded-full overflow-hidden">
            <div
              className="h-full bg-primary/60 rounded-full transition-all"
              style={{
                width: `${Math.min(PROGRESS_CAP_PERCENT, ((now - pendingSince) / 1000 / EXPECTED_ANALYSIS_SECONDS) * 100)}%`,
              }}
            />
          </div>
        </div>
      )}

      <div className="grid grid-cols-3 gap-4">
        {/* Probability Card */}
        {scoreNum != null && (
          <div className="bg-card border border-border rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2 text-sm text-muted-foreground">
              <TrendingUp className="w-4 h-4" />
              Award Probability
            </div>
            <div className={cn("text-4xl font-bold font-mono", getScoreColor(scoreNum))}>
              {scoreNum}%
            </div>
            <div className={cn("text-sm mt-1", getScoreColor(scoreNum))}>{getScoreLabel(scoreNum)}</div>
          </div>
        )}

        {/* Bid Recommendation */}
        {opp.bid_no_bid_recommendation && (
          <div className="bg-card border border-border rounded-lg p-4">
            <div className="text-sm text-muted-foreground mb-2">Bid Recommendation</div>
            <span className={cn("inline-block text-lg font-bold px-3 py-1 rounded-md", BID_COLORS[opp.bid_no_bid_recommendation] || "bg-secondary text-muted-foreground")}>
              {opp.bid_no_bid_recommendation.replace("_", " ")}
            </span>
          </div>
        )}

        {/* Value */}
        {opp.estimated_value && (
          <div className="bg-card border border-border rounded-lg p-4">
            <div className="text-sm text-muted-foreground mb-2">Estimated Value</div>
            <div className="text-3xl font-bold font-mono text-emerald-400">
              {formatCurrency(opp.estimated_value)}
            </div>
          </div>
        )}
      </div>

      {/* Details grid */}
      <div className="bg-card border border-border rounded-lg p-6">
        <h3 className="font-semibold mb-4 flex items-center gap-2">
          <FileText className="w-4 h-4" />
          Opportunity Details
        </h3>
        <div className="grid grid-cols-2 gap-4 text-sm">
          {[
            ["Agency", opp.agency],
            ["Solicitation Number", opp.solicitation_number || "—"],
            ["Status", opp.status],
            ["Pipeline Stage", opp.pipeline_stage],
            ["NAICS Code", opp.naics_code || "—"],
            ["Set-Aside", opp.set_aside || "Full & Open"],
            ["Jurisdiction", opp.jurisdiction || "—"],
            ["Place of Performance", opp.place_of_performance || "—"],
            ["Rule Pack", opp.procurement_rule_pack || "—"],
            ["Response Due", opp.response_due_date ? new Date(opp.response_due_date).toLocaleDateString() : "—"],
          ].map(([label, value]) => (
            <div key={label} className="flex flex-col gap-0.5">
              <span className="text-muted-foreground text-xs">{label}</span>
              <span className="font-medium">{value}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function AddOpportunityModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    title: "",
    agency: "",
    solicitation_number: "",
    estimated_value: "",
    response_due_date: "",
    jurisdiction: "us_federal",
    naics_code: "",
    set_aside: "",
    place_of_performance: "",
  });

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      await api.createOpportunity({
        ...form,
        estimated_value: form.estimated_value ? parseFloat(form.estimated_value) : null,
        response_due_date: form.response_due_date || null,
      });
      toast.success("Opportunity added");
      onCreated();
    } catch {
      toast.error("Failed to create opportunity");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-card border border-border rounded-xl w-full max-w-lg p-6">
        <h2 className="font-semibold text-lg mb-4">Add Opportunity</h2>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="block text-xs font-medium mb-1 text-muted-foreground">Title *</label>
            <input required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })}
              className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
              placeholder="IT Modernization Support Services" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium mb-1 text-muted-foreground">Agency *</label>
              <input required value={form.agency} onChange={(e) => setForm({ ...form, agency: e.target.value })}
                className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                placeholder="Dept. of Homeland Security" />
            </div>
            <div>
              <label className="block text-xs font-medium mb-1 text-muted-foreground">Solicitation #</label>
              <input value={form.solicitation_number} onChange={(e) => setForm({ ...form, solicitation_number: e.target.value })}
                className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                placeholder="70RSAT24R00000001" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium mb-1 text-muted-foreground">Estimated Value ($)</label>
              <input type="number" value={form.estimated_value} onChange={(e) => setForm({ ...form, estimated_value: e.target.value })}
                className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                placeholder="5000000" />
            </div>
            <div>
              <label className="block text-xs font-medium mb-1 text-muted-foreground">Response Due</label>
              <input type="date" value={form.response_due_date} onChange={(e) => setForm({ ...form, response_due_date: e.target.value })}
                className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/50" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium mb-1 text-muted-foreground">Jurisdiction</label>
              <select value={form.jurisdiction} onChange={(e) => setForm({ ...form, jurisdiction: e.target.value })}
                className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/50">
                {JURISDICTIONS.map((j) => <option key={j} value={j}>{j}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium mb-1 text-muted-foreground">NAICS Code</label>
              <input value={form.naics_code} onChange={(e) => setForm({ ...form, naics_code: e.target.value })}
                className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                placeholder="541512" />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium mb-1 text-muted-foreground">Set-Aside</label>
            <select value={form.set_aside} onChange={(e) => setForm({ ...form, set_aside: e.target.value })}
              className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/50">
              <option value="">Full & Open</option>
              <option value="8a">8(a) Program</option>
              <option value="small_business">Small Business</option>
              <option value="hubzone">HUBZone</option>
              <option value="sdvosb">SDVOSB</option>
              <option value="wosb">WOSB</option>
              <option value="vosb">VOSB</option>
            </select>
          </div>
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose}
              className="flex-1 py-2 border border-border rounded-md text-sm hover:bg-secondary transition-colors">
              Cancel
            </button>
            <button type="submit" disabled={loading}
              className="flex-1 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50">
              {loading ? "Adding…" : "Add Opportunity"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
