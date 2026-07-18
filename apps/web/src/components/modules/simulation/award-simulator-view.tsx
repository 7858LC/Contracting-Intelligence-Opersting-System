"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Award,
  ChevronDown,
  ChevronRight,
  Loader2,
  Plus,
  AlertTriangle,
  XCircle,
  CheckCircle2,
  Zap,
  MessageSquareWarning,
  BookMarked,
  TrendingUp,
  Shield,
} from "lucide-react";
import { toast } from "sonner";
import api from "@/lib/api";
import { formatProbability, getScoreColor, getScoreLabel, cn } from "@/lib/utils";

interface FactorRating {
  score: number;
  adjectival: string;
  color: string;
  risk: string;
  narrative?: string;
}

interface Finding {
  factor?: string;
  description?: string;
  citation?: string;
  severity?: string;
}

interface Improvement {
  title?: string;
  description?: string;
  expected_score_impact?: string;
  priority?: string;
  factor?: string;
}

interface RedTeamComment {
  observation?: string;
  impact?: string;
  recommendation?: string;
}

interface RuleCitation {
  regulation?: string;
  section?: string;
  text?: string;
}

interface Simulation {
  id: string;
  name: string;
  status: string;
  evaluation_methodology: string;
  award_probability: number | null;
  confidence_score: number | null;
  gate_review_recommendation: string | null;
  technical_score: number | null;
  management_score: number | null;
  past_performance_score: number | null;
  price_competitiveness_score: number | null;
  compliance_score: number | null;
  risk_score: number | null;
  overall_score: number | null;
  executive_summary: string | null;
  strengths: Finding[];
  weaknesses: Finding[];
  significant_weaknesses: Finding[];
  deficiencies: Finding[];
  red_team_comments: RedTeamComment[];
  suggested_improvements: Improvement[];
  rule_citations: RuleCitation[];
  evidence: { factor_ratings?: Record<string, FactorRating> } | null;
  error_message: string | null;
  created_at: string | null;
}

const DOD_COLOR_MAP: Record<string, { bg: string; text: string; border: string }> = {
  Blue:   { bg: "bg-blue-500/10",   text: "text-blue-400",   border: "border-blue-500/30" },
  Purple: { bg: "bg-violet-500/10", text: "text-violet-400", border: "border-violet-500/30" },
  Green:  { bg: "bg-emerald-500/10",text: "text-emerald-400",border: "border-emerald-500/30" },
  Yellow: { bg: "bg-amber-500/10",  text: "text-amber-400",  border: "border-amber-500/30" },
  Red:    { bg: "bg-red-500/10",    text: "text-red-400",    border: "border-red-500/30" },
};

function DodChip({ adjectival, color }: { adjectival: string; color: string }) {
  const style = DOD_COLOR_MAP[color] ?? DOD_COLOR_MAP.Green;
  return (
    <span className={cn(
      "inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold border tracking-wide",
      style.bg, style.text, style.border
    )}>
      <span className={cn("w-1.5 h-1.5 rounded-full", style.text.replace("text-", "bg-"))} />
      {adjectival.toUpperCase()}
    </span>
  );
}

function GateChip({ rec }: { rec: string }) {
  const cfg = {
    SUBMIT:   { cls: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30", label: "SUBMIT" },
    REVISE:   { cls: "bg-amber-500/10 text-amber-400 border-amber-500/30",       label: "REVISE BEFORE SUBMIT" },
    WITHDRAW: { cls: "bg-red-500/10 text-red-400 border-red-500/30",             label: "WITHDRAW" },
  }[rec] ?? { cls: "bg-secondary text-muted-foreground border-border", label: rec };
  return (
    <span className={cn("px-3 py-1 rounded border text-xs font-bold tracking-widest", cfg.cls)}>
      {cfg.label}
    </span>
  );
}

function ProbabilityGauge({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color = pct >= 70 ? "text-emerald-400" : pct >= 50 ? "text-amber-400" : "text-red-400";
  const barColor = pct >= 70 ? "bg-emerald-500" : pct >= 50 ? "bg-amber-500" : "bg-red-500";
  return (
    <div className="space-y-1.5">
      <div className={cn("text-4xl font-bold tabular-nums", color)}>{pct}%</div>
      <div className="h-2 bg-secondary rounded-full overflow-hidden w-32">
        <div className={cn("h-full rounded-full transition-all", barColor)} style={{ width: `${pct}%` }} />
      </div>
      <div className="text-xs text-muted-foreground">Award Probability</div>
    </div>
  );
}

function ScoreBar({ label, value, factorRating }: { label: string; value: number | null; factorRating?: FactorRating }) {
  const pct = value ?? 0;
  const adjective = factorRating?.adjectival ?? getScoreLabel(value);
  const color = factorRating?.color;
  const style = color ? DOD_COLOR_MAP[color] : null;

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted-foreground">{label}</span>
        <div className="flex items-center gap-2">
          {style ? (
            <DodChip adjectival={adjective} color={color!} />
          ) : (
            <span className={cn("font-medium", getScoreColor(value))}>{adjective}</span>
          )}
          <span className={cn("font-bold tabular-nums", getScoreColor(value))}>{value != null ? Math.round(value) : "—"}</span>
        </div>
      </div>
      <div className="h-1.5 bg-secondary rounded-full overflow-hidden">
        <div
          className={cn("h-full rounded-full", style ? style.text.replace("text-", "bg-") : "bg-primary")}
          style={{ width: `${pct}%`, opacity: 0.7 }}
        />
      </div>
    </div>
  );
}

function FindingItem({ finding, variant }: { finding: Finding; variant: "strength" | "weakness" | "significant" | "deficiency" }) {
  const config = {
    strength:    { icon: CheckCircle2,      cls: "text-emerald-400" },
    weakness:    { icon: AlertTriangle,     cls: "text-amber-400" },
    significant: { icon: AlertTriangle,     cls: "text-orange-400" },
    deficiency:  { icon: XCircle,           cls: "text-red-400" },
  }[variant];
  const Icon = config.icon;
  const text = typeof finding === "string" ? finding : finding.description ?? JSON.stringify(finding);
  const citation = typeof finding === "object" ? finding.citation : null;
  const factor = typeof finding === "object" ? finding.factor : null;

  return (
    <div className="flex items-start gap-2.5 py-2 border-b border-border/50 last:border-0">
      <Icon className={cn("w-3.5 h-3.5 mt-0.5 shrink-0", config.cls)} />
      <div className="flex-1 min-w-0">
        {factor && <div className="text-[10px] font-semibold text-muted-foreground mb-0.5 uppercase tracking-wide">{factor}</div>}
        <p className="text-xs text-foreground/80 leading-relaxed">{text}</p>
        {citation && <p className="text-[10px] text-muted-foreground/60 mt-0.5 font-mono">{citation}</p>}
      </div>
    </div>
  );
}

function Section({ title, icon: Icon, children, defaultOpen = false }: {
  title: string;
  icon: React.ComponentType<{ className?: string }>;
  children: React.ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border border-border rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-4 py-3 bg-secondary/30 hover:bg-secondary/50 transition-colors text-left"
      >
        <div className="flex items-center gap-2">
          <Icon className="w-3.5 h-3.5 text-primary" />
          <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{title}</span>
        </div>
        {open ? <ChevronDown className="w-3.5 h-3.5 text-muted-foreground" /> : <ChevronRight className="w-3.5 h-3.5 text-muted-foreground" />}
      </button>
      {open && <div className="px-4 py-2">{children}</div>}
    </div>
  );
}

function SimulationReport({ sim }: { sim: Simulation }) {
  const factorRatings = sim.evidence?.factor_ratings ?? {};
  const SCORE_ROWS = [
    { label: "Technical",         value: sim.technical_score,           key: "Technical" },
    { label: "Management",        value: sim.management_score,          key: "Management" },
    { label: "Past Performance",  value: sim.past_performance_score,    key: "Past Performance" },
    { label: "Price",             value: sim.price_competitiveness_score, key: "Price" },
    { label: "Compliance",        value: sim.compliance_score,          key: "Compliance" },
    { label: "Risk",              value: sim.risk_score,                key: "Risk" },
  ];

  return (
    <div className="border-t border-border p-5 space-y-5 bg-background/50">
      {/* Top strip: probability + gate + overall */}
      <div className="flex items-end justify-between gap-6 flex-wrap">
        {sim.award_probability != null && (
          <ProbabilityGauge value={sim.award_probability} />
        )}
        <div className="space-y-2 text-right">
          {sim.gate_review_recommendation && (
            <div>
              <div className="text-[10px] text-muted-foreground mb-1">Gate Review</div>
              <GateChip rec={sim.gate_review_recommendation} />
            </div>
          )}
          {sim.overall_score != null && (
            <div className="text-xs text-muted-foreground">
              Overall score: <span className={cn("font-bold", getScoreColor(sim.overall_score))}>{Math.round(sim.overall_score)}</span>
              {sim.confidence_score != null && (
                <span className="ml-2 opacity-60">· {Math.round(sim.confidence_score * 100)}% confidence</span>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Score bars */}
      <div className="space-y-2.5">
        {SCORE_ROWS.map(({ label, value, key }) => (
          <ScoreBar key={label} label={label} value={value} factorRating={factorRatings[key]} />
        ))}
      </div>

      {/* Executive summary */}
      {sim.executive_summary && (
        <div className="bg-secondary/20 rounded-lg px-4 py-3 border border-border/50">
          <div className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wide mb-2">Executive Summary</div>
          <p className="text-sm leading-relaxed text-foreground/80">{sim.executive_summary}</p>
        </div>
      )}

      {/* Findings sections */}
      <div className="space-y-2">
        {sim.deficiencies?.length > 0 && (
          <Section title={`Deficiencies (${sim.deficiencies.length})`} icon={XCircle} defaultOpen>
            {sim.deficiencies.map((d, i) => <FindingItem key={i} finding={d} variant="deficiency" />)}
          </Section>
        )}
        {sim.significant_weaknesses?.length > 0 && (
          <Section title={`Significant Weaknesses (${sim.significant_weaknesses.length})`} icon={AlertTriangle} defaultOpen>
            {sim.significant_weaknesses.map((w, i) => <FindingItem key={i} finding={w} variant="significant" />)}
          </Section>
        )}
        {sim.weaknesses?.length > 0 && (
          <Section title={`Weaknesses (${sim.weaknesses.length})`} icon={AlertTriangle}>
            {sim.weaknesses.map((w, i) => <FindingItem key={i} finding={w} variant="weakness" />)}
          </Section>
        )}
        {sim.strengths?.length > 0 && (
          <Section title={`Strengths (${sim.strengths.length})`} icon={CheckCircle2}>
            {sim.strengths.map((s, i) => <FindingItem key={i} finding={s} variant="strength" />)}
          </Section>
        )}

        {/* Improvements */}
        {sim.suggested_improvements?.length > 0 && (
          <Section title={`Ranked Improvements (${sim.suggested_improvements.length})`} icon={TrendingUp} defaultOpen>
            <div className="space-y-2 py-1">
              {sim.suggested_improvements.map((imp, i) => {
                const item = typeof imp === "string" ? { description: imp } : imp;
                const priorityCls = item.priority === "high" ? "text-red-400" : item.priority === "medium" ? "text-amber-400" : "text-muted-foreground";
                return (
                  <div key={i} className="flex items-start gap-3 py-2 border-b border-border/50 last:border-0">
                    <div className="w-5 h-5 rounded bg-primary/10 text-primary text-[10px] font-bold flex items-center justify-center shrink-0 mt-0.5">
                      {i + 1}
                    </div>
                    <div className="flex-1 min-w-0">
                      {item.title && <div className="text-xs font-semibold mb-0.5">{item.title}</div>}
                      <p className="text-xs text-muted-foreground leading-relaxed">{item.description}</p>
                      <div className="flex items-center gap-3 mt-1">
                        {item.factor && <span className="text-[10px] text-muted-foreground/60">{item.factor}</span>}
                        {item.expected_score_impact && (
                          <span className="text-[10px] font-mono text-emerald-400">{item.expected_score_impact}</span>
                        )}
                        {item.priority && (
                          <span className={cn("text-[10px] uppercase font-semibold", priorityCls)}>{item.priority}</span>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </Section>
        )}

        {/* Red team */}
        {sim.red_team_comments?.length > 0 && (
          <Section title={`Red Team Commentary (${sim.red_team_comments.length})`} icon={MessageSquareWarning}>
            <div className="space-y-3 py-1">
              {sim.red_team_comments.map((c, i) => {
                const item = typeof c === "string" ? { observation: c } : c;
                return (
                  <div key={i} className="space-y-1">
                    {item.observation && <p className="text-xs font-medium">{item.observation}</p>}
                    {item.impact && <p className="text-xs text-muted-foreground">Impact: {item.impact}</p>}
                    {item.recommendation && <p className="text-xs text-primary/80">→ {item.recommendation}</p>}
                  </div>
                );
              })}
            </div>
          </Section>
        )}

        {/* Rule citations */}
        {sim.rule_citations?.length > 0 && (
          <Section title={`Rule Citations (${sim.rule_citations.length})`} icon={BookMarked}>
            <div className="space-y-2 py-1">
              {sim.rule_citations.map((c, i) => {
                const item = typeof c === "string" ? { text: c } : c;
                return (
                  <div key={i} className="text-xs">
                    {(item.regulation || item.section) && (
                      <span className="font-mono text-primary font-semibold">{item.regulation} {item.section} </span>
                    )}
                    <span className="text-muted-foreground">{item.text}</span>
                  </div>
                );
              })}
            </div>
          </Section>
        )}
      </div>
    </div>
  );
}

function SimulationCard({ sim, onClick, expanded }: { sim: Simulation; onClick: () => void; expanded: boolean }) {
  const isCompleted = sim.status === "completed";
  const isRunning = sim.status === "running" || sim.status === "queued";
  const isFailed = sim.status === "failed";

  return (
    <div
      className={cn(
        "border rounded-xl bg-card overflow-hidden transition-colors",
        expanded ? "border-primary" : "border-border hover:border-primary/40",
        !isFailed && "cursor-pointer"
      )}
      onClick={!isFailed ? onClick : undefined}
    >
      <div className="p-5 flex items-center gap-4">
        <div className={cn(
          "w-10 h-10 rounded-lg flex items-center justify-center shrink-0",
          isCompleted ? "bg-primary/10" : isRunning ? "bg-blue-500/10" : "bg-red-500/10"
        )}>
          {isRunning ? (
            <Loader2 className="w-5 h-5 text-blue-400 animate-spin" />
          ) : isFailed ? (
            <XCircle className="w-5 h-5 text-red-400" />
          ) : (
            <Award className="w-5 h-5 text-primary" />
          )}
        </div>

        <div className="flex-1 min-w-0">
          <h3 className="font-semibold truncate">{sim.name}</h3>
          <div className="flex items-center gap-3 mt-0.5">
            <span className="text-xs text-muted-foreground">{sim.evaluation_methodology?.replace(/_/g, " ")}</span>
            {isRunning && <span className="text-xs text-blue-400">Analyzing…</span>}
            {isFailed && <span className="text-xs text-red-400">Failed</span>}
          </div>
        </div>

        {isCompleted && (
          <div className="flex items-center gap-5 shrink-0">
            {sim.award_probability != null && (
              <div className="text-right">
                <div className={cn("text-2xl font-bold tabular-nums", getScoreColor((sim.award_probability) * 100))}>
                  {formatProbability(sim.award_probability)}
                </div>
                <div className="text-[10px] text-muted-foreground">Probability</div>
              </div>
            )}
            {sim.gate_review_recommendation && (
              <GateChip rec={sim.gate_review_recommendation} />
            )}
            {sim.deficiencies?.length > 0 && (
              <div className="flex items-center gap-1 text-xs text-red-400">
                <XCircle className="w-3.5 h-3.5" />
                <span>{sim.deficiencies.length} deficiencie{sim.deficiencies.length !== 1 ? "s" : ""}</span>
              </div>
            )}
          </div>
        )}

        {isCompleted && (
          <ChevronDown className={cn("w-4 h-4 text-muted-foreground transition-transform shrink-0", expanded && "rotate-180")} />
        )}
      </div>

      {expanded && isCompleted && <SimulationReport sim={sim} />}
    </div>
  );
}

function NewSimulationForm({ opportunities, onSubmit, onCancel, isLoading }: {
  opportunities: { id: string; title: string }[];
  onSubmit: (p: Record<string, unknown>) => void;
  onCancel: () => void;
  isLoading: boolean;
}) {
  const [form, setForm] = useState({
    opportunity_id: "",
    name: "",
    evaluation_methodology: "BEST_VALUE_TRADEOFF",
    proposal_content: { technical: "", management: "", past_performance: "", price: "" },
  });
  const [step, setStep] = useState<1 | 2>(1);

  const canProceed = form.opportunity_id && form.name;

  return (
    <div className="border border-primary/40 rounded-xl bg-card overflow-hidden">
      {/* Step header */}
      <div className="px-6 py-4 border-b border-border bg-secondary/20 flex items-center gap-4">
        <div className="flex items-center gap-2">
          {[1, 2].map((s) => (
            <div key={s} className="flex items-center gap-2">
              <div className={cn(
                "w-6 h-6 rounded-full text-xs font-bold flex items-center justify-center",
                step >= s ? "bg-primary text-primary-foreground" : "bg-secondary text-muted-foreground"
              )}>
                {s}
              </div>
              <span className="text-xs text-muted-foreground">
                {s === 1 ? "Setup" : "Proposal Content"}
              </span>
              {s < 2 && <ChevronRight className="w-3 h-3 text-muted-foreground" />}
            </div>
          ))}
        </div>
      </div>

      <div className="p-6 space-y-4">
        {step === 1 ? (
          <>
            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-medium text-muted-foreground mb-1.5 block">Opportunity *</label>
                <select
                  value={form.opportunity_id}
                  onChange={(e) => setForm({ ...form, opportunity_id: e.target.value })}
                  className="w-full bg-background border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                >
                  <option value="">Select opportunity…</option>
                  {opportunities.map((o) => (
                    <option key={o.id} value={o.id}>{o.title}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs font-medium text-muted-foreground mb-1.5 block">Simulation Name *</label>
                <input
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="Initial Gate Review — Q3 2026"
                  className="w-full bg-background border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                />
              </div>
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground mb-1.5 block">Evaluation Methodology</label>
              <select
                value={form.evaluation_methodology}
                onChange={(e) => setForm({ ...form, evaluation_methodology: e.target.value })}
                className="w-full bg-background border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
              >
                <option value="BEST_VALUE_TRADEOFF">Best Value Tradeoff (FAR 15.101-1)</option>
                <option value="LPTA">LPTA — Lowest Price Technically Acceptable (FAR 15.101-2)</option>
                <option value="BEST_VALUE_CONTINUUM">Best Value Continuum (DoD)</option>
                <option value="MEAT">MEAT — Most Economically Advantageous Tender (EU 2014/24)</option>
                <option value="QCBS">Quality and Cost Based Selection (World Bank)</option>
              </select>
            </div>
            <div className="flex items-center justify-between pt-2">
              <button onClick={onCancel} className="text-sm text-muted-foreground hover:text-foreground transition-colors">
                Cancel
              </button>
              <button
                onClick={() => setStep(2)}
                disabled={!canProceed}
                className="flex items-center gap-2 bg-primary text-primary-foreground px-5 py-2 rounded-md text-sm font-medium hover:bg-primary/90 disabled:opacity-40 transition-colors"
              >
                Next: Proposal Content <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </>
        ) : (
          <>
            <div className="text-xs text-muted-foreground bg-secondary/30 rounded-lg px-4 py-3 border border-border/50">
              <Shield className="w-3.5 h-3.5 inline mr-1.5 text-primary" />
              Proposal content is optional. The simulation uses your Knowledge Vault for context. Adding content enables pre-submission red-teaming.
            </div>
            <div className="space-y-3">
              {[
                { key: "technical", label: "Technical Approach", placeholder: "Summarize your technical solution, methodology, and staffing plan…" },
                { key: "management", label: "Management Approach", placeholder: "Key personnel, org structure, quality control, risk management…" },
                { key: "past_performance", label: "Past Performance", placeholder: "Relevant contract experience, CPARs, references…" },
                { key: "price", label: "Price / Cost", placeholder: "Estimated total contract value, rate structure, or pricing notes…" },
              ].map(({ key, label, placeholder }) => (
                <div key={key}>
                  <label className="text-xs font-medium text-muted-foreground mb-1.5 block">{label}</label>
                  <textarea
                    value={form.proposal_content[key as keyof typeof form.proposal_content]}
                    onChange={(e) => setForm({ ...form, proposal_content: { ...form.proposal_content, [key]: e.target.value } })}
                    placeholder={placeholder}
                    className="w-full bg-background border border-border rounded-md px-3 py-2 text-sm h-20 resize-none focus:outline-none focus:ring-2 focus:ring-primary/50 placeholder:text-muted-foreground/50"
                  />
                </div>
              ))}
            </div>
            <div className="flex items-center justify-between pt-2">
              <button onClick={() => setStep(1)} className="text-sm text-muted-foreground hover:text-foreground transition-colors">
                ← Back
              </button>
              <button
                onClick={() => onSubmit(form)}
                disabled={isLoading}
                className="flex items-center gap-2 bg-primary text-primary-foreground px-6 py-2.5 rounded-md text-sm font-semibold hover:bg-primary/90 disabled:opacity-50 transition-colors"
              >
                {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
                Run Simulation
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function EmptyState({ onNew }: { onNew: () => void }) {
  return (
    <div className="border border-dashed border-border rounded-xl p-16 text-center">
      <div className="w-16 h-16 bg-primary/10 rounded-2xl flex items-center justify-center mx-auto mb-5">
        <Award className="w-8 h-8 text-primary" />
      </div>
      <h3 className="font-semibold text-lg mb-2">No simulations yet</h3>
      <p className="text-sm text-muted-foreground mb-2 max-w-xs mx-auto">
        Emulate how government evaluators will score your proposal — before you submit it.
      </p>
      <p className="text-xs text-muted-foreground/60 mb-6 max-w-xs mx-auto">
        Ratings follow FAR 15.305 and DoD color/adjectival methodology.
      </p>
      <button
        onClick={onNew}
        className="bg-primary text-primary-foreground px-6 py-2.5 rounded-md text-sm font-semibold hover:bg-primary/90 transition-colors"
      >
        Run First Simulation
      </button>
    </div>
  );
}

export function AwardSimulatorView() {
  const [showNewForm, setShowNewForm] = useState(false);
  const [selectedSim, setSelectedSim] = useState<string | null>(null);
  const qc = useQueryClient();

  const { data: simsData, isLoading } = useQuery({
    queryKey: ["simulations"],
    queryFn: () => api.getSimulations(),
    refetchInterval: 10_000,
  });

  const { data: oppsData } = useQuery({
    queryKey: ["opportunities", "list"],
    queryFn: () => api.getOpportunities({ page_size: 50 }),
  });

  const createMutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) => api.createSimulation(payload as Parameters<typeof api.createSimulation>[0]),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["simulations"] });
      setShowNewForm(false);
      toast.success("Simulation queued — results in 1–3 minutes.");
    },
    onError: () => toast.error("Failed to create simulation"),
  });

  const simulations: Simulation[] = simsData?.items ?? [];
  const opportunities: { id: string; title: string }[] = oppsData?.items ?? [];
  const running = simulations.filter((s) => s.status === "running" || s.status === "queued").length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2.5">
            <Award className="w-6 h-6 text-primary" />
            Award Simulator
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Emulate government source selection evaluation before proposal submission · FAR 15.305 / DFARS
          </p>
        </div>
        <div className="flex items-center gap-3">
          {running > 0 && (
            <div className="flex items-center gap-1.5 text-xs text-blue-400 bg-blue-500/10 px-3 py-1.5 rounded-md border border-blue-500/20">
              <Loader2 className="w-3 h-3 animate-spin" />
              {running} running
            </div>
          )}
          {!showNewForm && (
            <button
              onClick={() => setShowNewForm(true)}
              className="flex items-center gap-2 bg-primary text-primary-foreground px-4 py-2 rounded-md text-sm font-medium hover:bg-primary/90 transition-colors"
            >
              <Plus className="w-4 h-4" />
              New Simulation
            </button>
          )}
        </div>
      </div>

      {showNewForm && (
        <NewSimulationForm
          opportunities={opportunities}
          onSubmit={(p) => createMutation.mutate(p)}
          onCancel={() => setShowNewForm(false)}
          isLoading={createMutation.isPending}
        />
      )}

      <div className="space-y-3">
        {isLoading ? (
          <div className="flex items-center justify-center py-16 text-muted-foreground">
            <Loader2 className="w-5 h-5 animate-spin mr-2" />
            Loading simulations…
          </div>
        ) : simulations.length === 0 ? (
          <EmptyState onNew={() => setShowNewForm(true)} />
        ) : (
          simulations.map((sim) => (
            <SimulationCard
              key={sim.id}
              sim={sim}
              onClick={() => setSelectedSim(sim.id === selectedSim ? null : sim.id)}
              expanded={sim.id === selectedSim}
            />
          ))
        )}
      </div>
    </div>
  );
}
