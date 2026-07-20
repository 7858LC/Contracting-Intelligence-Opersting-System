"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import {
  Activity,
  AlertCircle,
  ArrowLeft,
  BarChart3,
  Brain,
  Building2,
  Calendar,
  ChevronRight,
  Clock,
  ExternalLink,
  Loader2,
  RefreshCw,
  Sparkles,
  Star,
  StarOff,
  TrendingUp,
  Zap,
} from "lucide-react";
import { cn } from "@/lib/utils";
import api from "@/lib/api";

// ── Types ──────────────────────────────────────────────────────────────────

interface Company {
  id: string;
  name: string;
  domain: string | null;
  website: string | null;
  linkedin_url: string | null;
  samgov_uei: string | null;
  cage_code: string | null;
  industry: string | null;
  employee_count_range: string | null;
  revenue_range: string | null;
  headquarters_city: string | null;
  headquarters_state: string | null;
  naics_codes: string[];
  set_aside_types: string[];
  description: string | null;
  overall_signal_score: number;
  confidence_score: number;
  growth_momentum_score: number;
  government_readiness_score: number;
  priority_tier: "A" | "B" | "C";
  is_watched: boolean;
  last_scanned_at: string | null;
}

interface Signal {
  id: string;
  signal_type: string;
  source: string;
  source_url: string | null;
  title: string;
  description: string | null;
  effective_weight: number;
  detected_at: string;
}

interface AIAnalysis {
  id: string;
  status: "pending" | "running" | "completed" | "failed";
  executive_summary: string | null;
  pain_points: string[];
  recommended_outreach: string | null;
  buying_probability: number | null;
  suggested_messaging: string[];
  potential_stakeholders: { title: string; reason: string }[];
  confidence_explanation: string | null;
  error_message: string | null;
  created_at: string;
}

// ── Score ring ─────────────────────────────────────────────────────────────

function ScoreRing({
  value,
  label,
  size = 80,
  tier,
}: {
  value: number;
  label: string;
  size?: number;
  tier?: "A" | "B" | "C";
}) {
  const r = (size - 8) / 2;
  const circ = 2 * Math.PI * r;
  const offset = circ - (value / 100) * circ;
  const color =
    tier === "A" ? "#10b981"
    : tier === "B" ? "#f59e0b"
    : "#94a3b8";

  return (
    <div className="flex flex-col items-center gap-1">
      <svg width={size} height={size}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#e2e8f0" strokeWidth={4} className="dark:stroke-slate-700" />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth={4}
          strokeDasharray={circ}
          strokeDashoffset={offset}
          strokeLinecap="round"
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
        />
        <text
          x={size / 2}
          y={size / 2 + 5}
          textAnchor="middle"
          fontSize={16}
          fontWeight={700}
          fill="currentColor"
          className="fill-foreground"
        >
          {Math.round(value)}
        </text>
      </svg>
      <span className="text-[11px] text-muted-foreground text-center leading-tight">{label}</span>
    </div>
  );
}

// ── Signal type color ──────────────────────────────────────────────────────

function signalCategoryColor(type: string): string {
  if (type.startsWith("hiring_")) return "text-purple-600 dark:text-purple-400 bg-purple-500/10";
  if (type.includes("award") || type.includes("contract") || type.includes("recompete"))
    return "text-emerald-600 dark:text-emerald-400 bg-emerald-500/10";
  if (type.includes("certification") || type.includes("sam_") || type.includes("cmmc"))
    return "text-blue-600 dark:text-blue-400 bg-blue-500/10";
  return "text-amber-600 dark:text-amber-400 bg-amber-500/10";
}

function signalLabel(raw: string): string {
  return raw.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function relativeTime(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime();
  const days = Math.floor(ms / 86_400_000);
  if (days === 0) return "Today";
  if (days === 1) return "Yesterday";
  if (days < 30) return `${days}d ago`;
  if (days < 365) return `${Math.floor(days / 30)}mo ago`;
  return `${Math.floor(days / 365)}y ago`;
}

// ── Probability bar ────────────────────────────────────────────────────────

function ProbabilityBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color =
    pct >= 70 ? "bg-emerald-500"
    : pct >= 40 ? "bg-amber-500"
    : "bg-slate-400";
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 bg-secondary rounded-full h-2">
        <div className={cn("h-2 rounded-full transition-all", color)} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-sm font-semibold w-10 text-right">{pct}%</span>
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────

export function CompanyDetail({ companyId }: { companyId: string }) {
  const qc = useQueryClient();
  const [activeTab, setActiveTab] = useState<"signals" | "analysis">("signals");

  const { data: company, isLoading } = useQuery<Company>({
    queryKey: ["radar-company", companyId],
    queryFn: () => api.getCompany(companyId),
  });

  const { data: signalsData } = useQuery({
    queryKey: ["radar-signals", companyId],
    queryFn: () => api.listCompanySignals(companyId, { page_size: 50 }),
    enabled: !!company,
  });

  const { data: analysesData } = useQuery({
    queryKey: ["radar-analyses", companyId],
    queryFn: () => api.listAIAnalyses(companyId),
    enabled: !!company,
  });

  const signals: Signal[] = signalsData?.items ?? [];
  const analyses: AIAnalysis[] = analysesData?.items ?? [];
  const latestAnalysis = analyses[0] ?? null;

  const watchMutation = useMutation({
    mutationFn: () => api.updateCompany(companyId, { is_watched: !company?.is_watched }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["radar-company", companyId] }),
  });

  const scanMutation = useMutation({
    mutationFn: () => api.triggerCompanyScan(companyId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["radar-company", companyId] }),
  });

  const analyzeMutation = useMutation({
    mutationFn: () => api.triggerAIAnalysis(companyId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["radar-analyses", companyId] });
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-32">
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!company) {
    return (
      <div className="text-center py-20 text-muted-foreground">
        <AlertCircle className="w-10 h-10 mx-auto mb-3" />
        <p>Company not found</p>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-5xl">
      {/* Back + header */}
      <div className="flex items-start justify-between">
        <div>
          <Link
            href="/dashboard/radar"
            className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground mb-2 transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Back to Radar
          </Link>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold">{company.name}</h1>
            <span
              className={cn(
                "px-2.5 py-0.5 rounded-full text-xs font-bold",
                company.priority_tier === "A" && "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400",
                company.priority_tier === "B" && "bg-amber-500/15 text-amber-600 dark:text-amber-400",
                company.priority_tier === "C" && "bg-secondary text-muted-foreground"
              )}
            >
              Tier {company.priority_tier}
            </span>
          </div>
          <div className="flex items-center gap-3 mt-1 text-sm text-muted-foreground">
            {company.domain && <span>{company.domain}</span>}
            {company.headquarters_state && (
              <>
                <span>·</span>
                <span>{company.headquarters_city ? `${company.headquarters_city}, ` : ""}{company.headquarters_state}</span>
              </>
            )}
            {company.industry && (
              <>
                <span>·</span>
                <span>{company.industry}</span>
              </>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => watchMutation.mutate()}
            disabled={watchMutation.isPending}
            className={cn(
              "flex items-center gap-2 px-3 py-2 rounded-md border text-sm transition-colors",
              company.is_watched
                ? "border-amber-400/50 bg-amber-400/10 text-amber-600 dark:text-amber-400"
                : "border-border hover:bg-secondary text-muted-foreground"
            )}
          >
            {company.is_watched ? <Star className="w-3.5 h-3.5 fill-current" /> : <StarOff className="w-3.5 h-3.5" />}
            {company.is_watched ? "Watching" : "Watch"}
          </button>
          <button
            onClick={() => scanMutation.mutate()}
            disabled={scanMutation.isPending}
            className="flex items-center gap-2 px-3 py-2 rounded-md border border-border text-sm hover:bg-secondary transition-colors disabled:opacity-50"
          >
            <RefreshCw className={cn("w-3.5 h-3.5", scanMutation.isPending && "animate-spin")} />
            Scan
          </button>
        </div>
      </div>

      {/* Scores */}
      <div className="bg-card border border-border rounded-lg p-5">
        <div className="text-sm font-medium mb-4">Signal Intelligence Scores</div>
        <div className="flex items-start gap-6 flex-wrap">
          <ScoreRing value={company.overall_signal_score} label="Overall Score" tier={company.priority_tier} size={90} />
          <ScoreRing value={company.confidence_score} label="Confidence" size={80} />
          <ScoreRing value={company.growth_momentum_score} label="Momentum" size={80} />
          <ScoreRing value={company.government_readiness_score} label="Gov Readiness" size={80} />
          <div className="flex-1 min-w-[200px] space-y-3 pl-2 pt-1">
            {company.samgov_uei && (
              <div className="flex items-center gap-2 text-xs">
                <span className="text-muted-foreground w-20">UEI</span>
                <span className="font-mono font-medium">{company.samgov_uei}</span>
              </div>
            )}
            {company.cage_code && (
              <div className="flex items-center gap-2 text-xs">
                <span className="text-muted-foreground w-20">CAGE</span>
                <span className="font-mono font-medium">{company.cage_code}</span>
              </div>
            )}
            {company.set_aside_types.length > 0 && (
              <div className="flex items-start gap-2 text-xs">
                <span className="text-muted-foreground w-20 pt-0.5">Set-Asides</span>
                <div className="flex flex-wrap gap-1">
                  {company.set_aside_types.map((s) => (
                    <span key={s} className="px-1.5 py-0.5 rounded text-[10px] bg-blue-500/10 text-blue-600 dark:text-blue-400 font-medium">{s}</span>
                  ))}
                </div>
              </div>
            )}
            {company.naics_codes.length > 0 && (
              <div className="flex items-start gap-2 text-xs">
                <span className="text-muted-foreground w-20 pt-0.5">NAICS</span>
                <span className="text-foreground">{company.naics_codes.slice(0, 4).join(", ")}</span>
              </div>
            )}
            {company.last_scanned_at && (
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <Clock className="w-3 h-3" />
                Last scanned {relativeTime(company.last_scanned_at)}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-border">
        {([
          { key: "signals", label: "Signals", count: signals.length },
          { key: "analysis", label: "AI Analysis", count: analyses.length },
        ] as const).map((t) => (
          <button
            key={t.key}
            onClick={() => setActiveTab(t.key)}
            className={cn(
              "px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors flex items-center gap-1.5",
              activeTab === t.key
                ? "border-primary text-foreground"
                : "border-transparent text-muted-foreground hover:text-foreground"
            )}
          >
            {t.label}
            {t.count > 0 && (
              <span className="text-[10px] bg-secondary px-1.5 py-0.5 rounded-full font-medium">
                {t.count}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Signals tab */}
      {activeTab === "signals" && (
        <div className="space-y-2">
          {signals.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <Zap className="w-8 h-8 mx-auto mb-2 opacity-20" />
              <p className="text-sm">No signals detected yet. Run a scan to discover signals.</p>
            </div>
          ) : (
            signals.map((sig) => (
              <div key={sig.id} className="bg-card border border-border rounded-lg p-4 flex gap-3">
                <span
                  className={cn(
                    "inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold h-fit mt-0.5 shrink-0",
                    signalCategoryColor(sig.signal_type)
                  )}
                >
                  {signalLabel(sig.signal_type)}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium leading-snug">{sig.title}</div>
                  {sig.description && (
                    <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">{sig.description}</p>
                  )}
                  <div className="flex items-center gap-3 mt-1.5 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <Calendar className="w-3 h-3" />
                      {relativeTime(sig.detected_at)}
                    </span>
                    <span>{sig.source.replace(/_/g, " ")}</span>
                    <span className="text-primary font-medium">
                      +{sig.effective_weight.toFixed(1)} pts
                    </span>
                    {sig.source_url && (
                      <a
                        href={sig.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-0.5 hover:text-foreground transition-colors"
                      >
                        <ExternalLink className="w-3 h-3" />
                        Source
                      </a>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* AI Analysis tab */}
      {activeTab === "analysis" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              Claude-powered analysis based on {signals.length} detected signals.
            </p>
            <button
              onClick={() => analyzeMutation.mutate()}
              disabled={analyzeMutation.isPending || latestAnalysis?.status === "running"}
              className="flex items-center gap-2 px-3 py-2 rounded-md bg-primary text-primary-foreground text-sm font-medium disabled:opacity-50"
            >
              {analyzeMutation.isPending ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Sparkles className="w-3.5 h-3.5" />
              )}
              {latestAnalysis ? "Re-analyze" : "Run Analysis"}
            </button>
          </div>

          {latestAnalysis?.status === "running" && (
            <div className="flex items-center gap-3 px-4 py-3 rounded-lg bg-primary/5 border border-primary/20 text-sm">
              <Loader2 className="w-4 h-4 animate-spin text-primary" />
              Analysis running… This takes 10–30 seconds.
            </div>
          )}

          {latestAnalysis?.status === "completed" && (
            <div className="space-y-4">
              {/* Executive summary */}
              <div className="bg-card border border-border rounded-lg p-5">
                <div className="flex items-center gap-2 mb-3">
                  <Brain className="w-4 h-4 text-primary" />
                  <span className="text-sm font-semibold">Executive Summary</span>
                </div>
                <p className="text-sm leading-relaxed">{latestAnalysis.executive_summary}</p>
              </div>

              {/* Buying probability */}
              {latestAnalysis.buying_probability !== null && (
                <div className="bg-card border border-border rounded-lg p-5">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <TrendingUp className="w-4 h-4 text-primary" />
                      <span className="text-sm font-semibold">Buying Probability</span>
                    </div>
                    <span className="text-xs text-muted-foreground">
                      Likelihood of near-term procurement engagement
                    </span>
                  </div>
                  <ProbabilityBar value={latestAnalysis.buying_probability} />
                  {latestAnalysis.confidence_explanation && (
                    <p className="text-xs text-muted-foreground mt-2">
                      {latestAnalysis.confidence_explanation}
                    </p>
                  )}
                </div>
              )}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Pain points */}
                {latestAnalysis.pain_points.length > 0 && (
                  <div className="bg-card border border-border rounded-lg p-5">
                    <div className="text-sm font-semibold mb-3 flex items-center gap-2">
                      <AlertCircle className="w-4 h-4 text-amber-500" />
                      Pain Points / Gaps
                    </div>
                    <ul className="space-y-2">
                      {latestAnalysis.pain_points.map((p, i) => (
                        <li key={i} className="text-xs text-muted-foreground flex gap-2">
                          <span className="text-amber-500 font-bold shrink-0">{i + 1}.</span>
                          {p}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Stakeholders */}
                {latestAnalysis.potential_stakeholders.length > 0 && (
                  <div className="bg-card border border-border rounded-lg p-5">
                    <div className="text-sm font-semibold mb-3 flex items-center gap-2">
                      <Building2 className="w-4 h-4 text-blue-500" />
                      Potential Stakeholders
                    </div>
                    <ul className="space-y-2">
                      {latestAnalysis.potential_stakeholders.map((s, i) => (
                        <li key={i} className="text-xs">
                          <span className="font-medium">{s.title}</span>
                          <span className="text-muted-foreground"> — {s.reason}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              {/* Recommended outreach */}
              {latestAnalysis.recommended_outreach && (
                <div className="bg-card border border-border rounded-lg p-5">
                  <div className="text-sm font-semibold mb-2 flex items-center gap-2">
                    <Activity className="w-4 h-4 text-emerald-500" />
                    Recommended Outreach
                  </div>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    {latestAnalysis.recommended_outreach}
                  </p>
                </div>
              )}

              {/* Suggested messaging */}
              {latestAnalysis.suggested_messaging.length > 0 && (
                <div className="bg-card border border-border rounded-lg p-5">
                  <div className="text-sm font-semibold mb-3">Suggested Messaging Angles</div>
                  <ul className="space-y-2">
                    {latestAnalysis.suggested_messaging.map((m, i) => (
                      <li
                        key={i}
                        className="text-xs px-3 py-2 rounded-md bg-secondary text-secondary-foreground"
                      >
                        {m}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {latestAnalysis?.status === "failed" && (
            <div className="flex items-center gap-3 px-4 py-3 rounded-lg bg-destructive/10 border border-destructive/20 text-sm text-destructive">
              <AlertCircle className="w-4 h-4" />
              Analysis failed: {latestAnalysis.error_message ?? "Unknown error"}
            </div>
          )}

          {!latestAnalysis && !analyzeMutation.isPending && (
            <div className="text-center py-12 text-muted-foreground">
              <Sparkles className="w-8 h-8 mx-auto mb-2 opacity-20" />
              <p className="text-sm">No analysis yet. Click &ldquo;Run Analysis&rdquo; to generate intelligence.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
