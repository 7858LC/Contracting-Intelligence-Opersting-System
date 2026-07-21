"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import {
  Crosshair, Plus, Sparkles, Play, FileText, Trophy, Gauge,
  AlertTriangle, ChevronDown, ChevronUp, ShieldCheck, Target, Layers,
  Upload, CheckCircle2, X,
} from "lucide-react";

// ── Types ──────────────────────────────────────────────────────────────────────

interface Solicitation {
  id: string;
  title: string;
  agency: string | null;
  solicitation_number: string | null;
  set_aside_type: string | null;
  pipeline_status: string;
  document_count: number;
  signal_count: number;
}

interface EvidenceDocument {
  id: string;
  document_type: string;
  title: string;
  source_url: string | null;
  source_ref: string | null;
  is_extracted: boolean;
  created_at: string;
}

interface Attribute {
  name: string;
  category: string;
  description: string | null;
  importance_weight: number;
  evidence_confidence: number;
  confidence_level: string;
  required_level: number;
  supporting_evidence: { text: string; source: string }[];
  reasoning: string | null;
  unknown_factors: string[];
}

interface Profile {
  summary: string | null;
  narrative: string | null;
  overall_confidence: number;
  evidence_strength: number;
  attribute_count: number;
  unknown_factors: string[];
  attributes: Attribute[];
}

interface Ranking {
  contractor_id: string;
  contractor_name: string;
  overall_alignment_score: number;
  rank: number;
  gaps: { attribute_name: string; severity: string; gap_size: number }[];
  gap_closures: { recommendation: string; timeline_months: number; feasibility: string }[];
  strengths: string[];
  summary: string | null;
}

interface Assessment {
  target_contractor_name: string | null;
  pdq_score: number;
  win_positioning_score: number;
  competitive_rank: number | null;
  candidate_pool_size: number;
  recommendation: string;
  executive_summary: string | null;
  key_findings: string[];
  critical_gaps: { attribute_name: string; severity: string; impact: string }[];
  recommended_actions: { recommendation: string; timeline_months?: number; feasibility?: string }[];
  risks: { risk: string; severity: string; mitigation: string }[];
  assumptions: string[];
}

interface Intelligence {
  solicitation: Solicitation;
  profile: Profile | null;
  rankings: Ranking[];
  assessment: Assessment | null;
}

// ── Small UI helpers ─────────────────────────────────────────────────────────────

const REC_STYLES: Record<string, string> = {
  bid: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  conditional_bid: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  no_bid: "bg-red-500/15 text-red-400 border-red-500/30",
  monitor: "bg-blue-500/15 text-blue-400 border-blue-500/30",
};

const SEVERITY_STYLES: Record<string, string> = {
  critical: "bg-red-500/15 text-red-400 border-red-500/30",
  major: "bg-orange-500/15 text-orange-400 border-orange-500/30",
  moderate: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  minor: "bg-secondary text-muted-foreground border-border",
};

// Mirrors cios.wph.constants.EvidenceDocumentType — the complete pre-proposal
// evidence package the engine accepts.
const DOCUMENT_TYPES: { value: string; label: string; highValue?: boolean }[] = [
  { value: "sources_sought", label: "Sources Sought Notice" },
  { value: "rfi", label: "Request for Information (RFI)" },
  { value: "draft_rfp", label: "Draft RFP" },
  { value: "final_solicitation", label: "Final Solicitation" },
  { value: "statement_of_work", label: "Statement of Work (SOW)" },
  { value: "performance_work_statement", label: "Performance Work Statement (PWS)" },
  { value: "statement_of_objectives", label: "Statement of Objectives (SOO)" },
  { value: "section_l", label: "Section L — Instructions to Offerors", highValue: true },
  { value: "section_m", label: "Section M — Evaluation Factors", highValue: true },
  { value: "evaluation_criteria", label: "Evaluation Criteria", highValue: true },
  { value: "qa_response", label: "Pre-Award Q&A Responses", highValue: true },
  { value: "government_response", label: "Government Response", highValue: true },
  { value: "industry_day", label: "Industry Day Materials" },
  { value: "historical_award", label: "Historical Award Data", highValue: true },
  { value: "incumbent_info", label: "Incumbent Information" },
  { value: "contract_vehicle", label: "Contract Vehicle Info" },
  { value: "agency_strategy", label: "Agency Strategic Document" },
  { value: "procurement_forecast", label: "Procurement Forecast" },
  { value: "amendment", label: "Amendment" },
  { value: "attachment", label: "Attachment" },
  { value: "other", label: "Other" },
];

function documentTypeLabel(value: string): string {
  return DOCUMENT_TYPES.find((d) => d.value === value)?.label ?? value.replace(/_/g, " ");
}

function ScoreDial({ label, value, icon: Icon }: { label: string; value: number; icon: React.ComponentType<{ className?: string }> }) {
  const color = value >= 70 ? "text-emerald-400" : value >= 45 ? "text-amber-400" : "text-red-400";
  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
        <Icon className="w-3.5 h-3.5" />
        {label}
      </div>
      <div className={cn("text-2xl font-bold font-mono", color)}>{value.toFixed(0)}<span className="text-sm text-muted-foreground">/100</span></div>
    </div>
  );
}

function Bar({ value, max = 100, className }: { value: number; max?: number; className?: string }) {
  return (
    <div className="h-1.5 w-full bg-secondary rounded-full overflow-hidden">
      <div className={cn("h-full rounded-full", className ?? "bg-primary")} style={{ width: `${Math.min(100, (value / max) * 100)}%` }} />
    </div>
  );
}

// ── Main view ────────────────────────────────────────────────────────────────────

export function WinningProfileView() {
  const queryClient = useQueryClient();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);

  const { data: solList, isLoading } = useQuery({
    queryKey: ["wph-solicitations"],
    queryFn: () => api.listSolicitations(),
  });
  const solicitations: Solicitation[] = solList?.items ?? [];
  const activeId = selectedId ?? solicitations[0]?.id ?? null;

  const seedMutation = useMutation({
    mutationFn: () => api.seedWphSample(true),
    onSuccess: (res) => {
      toast.success("Sample solicitation seeded and analyzed");
      queryClient.invalidateQueries({ queryKey: ["wph-solicitations"] });
      if (res?.solicitation_id) setSelectedId(res.solicitation_id);
    },
    onError: () => toast.error("Failed to seed sample"),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Crosshair className="w-6 h-6 text-primary" />
            Winning Profile Hypothesis™
          </h1>
          <p className="text-sm text-muted-foreground mt-1 max-w-2xl">
            Pre-award intelligence. Infer what an ideal awardee would most likely need — from the
            evidence package — <span className="italic">before</span> proposal development begins.
            CIOS improves pursuit-decision quality; it does not predict winners.
          </p>
        </div>
        <div className="flex gap-2 shrink-0">
          <button onClick={() => seedMutation.mutate()} disabled={seedMutation.isPending}
            className="flex items-center gap-2 px-3 py-2 border border-border rounded-md text-sm hover:bg-secondary transition-colors disabled:opacity-50">
            <Sparkles className="w-4 h-4" />
            {seedMutation.isPending ? "Seeding…" : "Load Sample"}
          </button>
          <button onClick={() => setShowCreate(true)}
            className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition-colors">
            <Plus className="w-4 h-4" />
            New Solicitation
          </button>
        </div>
      </div>

      <div className="grid grid-cols-12 gap-6">
        {/* Solicitation list */}
        <div className="col-span-4 space-y-2">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide px-1">
            Solicitation Packages
          </p>
          {isLoading ? (
            Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="h-16 bg-card border border-border rounded-lg animate-pulse" />
            ))
          ) : solicitations.length === 0 ? (
            <div className="text-center py-10 text-muted-foreground border border-dashed border-border rounded-lg">
              <FileText className="w-8 h-8 mx-auto mb-2 opacity-20" />
              <p className="text-sm">No solicitations yet.</p>
              <p className="text-xs mt-1">Load the sample or create one.</p>
            </div>
          ) : (
            solicitations.map((s) => (
              <button key={s.id} onClick={() => setSelectedId(s.id)}
                className={cn("w-full text-left p-3 rounded-lg border transition-colors",
                  activeId === s.id ? "border-primary bg-primary/5" : "border-border bg-card hover:bg-secondary")}>
                <p className="text-sm font-medium truncate">{s.title}</p>
                <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
                  <span>{s.agency ?? "—"}</span>
                  {s.set_aside_type && <span className="text-primary">· {s.set_aside_type}</span>}
                </div>
                <div className="flex items-center gap-2 mt-1.5">
                  <span className="text-[10px] uppercase tracking-wide bg-secondary text-muted-foreground px-1.5 py-0.5 rounded">
                    {s.pipeline_status.replace(/_/g, " ")}
                  </span>
                  <span className="text-[10px] text-muted-foreground">{s.document_count} docs · {s.signal_count} signals</span>
                </div>
              </button>
            ))
          )}
        </div>

        {/* Detail */}
        <div className="col-span-8">
          {activeId ? <SolicitationDetail solicitationId={activeId} /> : (
            <div className="text-center py-24 text-muted-foreground border border-dashed border-border rounded-lg">
              <Crosshair className="w-10 h-10 mx-auto mb-3 opacity-20" />
              <p>Select a solicitation to view its Winning Profile Hypothesis.</p>
            </div>
          )}
        </div>
      </div>

      {showCreate && (
        <CreateSolicitationModal
          onClose={() => setShowCreate(false)}
          onCreated={(id) => {
            setShowCreate(false);
            setSelectedId(id);
            queryClient.invalidateQueries({ queryKey: ["wph-solicitations"] });
          }}
        />
      )}
    </div>
  );
}

// ── Detail pane ──────────────────────────────────────────────────────────────────

function SolicitationDetail({ solicitationId }: { solicitationId: string }) {
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery<Intelligence>({
    queryKey: ["wph-intelligence", solicitationId],
    queryFn: () => api.getSolicitationIntelligence(solicitationId),
  });

  const { data: documents = [], isLoading: docsLoading } = useQuery<EvidenceDocument[]>({
    queryKey: ["wph-documents", solicitationId],
    queryFn: () => api.listSolicitationDocuments(solicitationId),
  });

  const runMutation = useMutation({
    mutationFn: () => api.runWphPipeline(solicitationId),
    onSuccess: () => {
      toast.success("Pre-award intelligence pipeline complete");
      queryClient.invalidateQueries({ queryKey: ["wph-intelligence", solicitationId] });
      queryClient.invalidateQueries({ queryKey: ["wph-solicitations"] });
    },
    onError: () => toast.error("Pipeline failed — ensure the package has documents and contractors exist"),
  });

  if (isLoading) return <div className="h-96 bg-card border border-border rounded-lg animate-pulse" />;
  if (!data) return null;

  const { profile, rankings, assessment } = data;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between bg-card border border-border rounded-lg p-4">
        <div>
          <p className="text-xs text-muted-foreground">Evidence-fusion pipeline</p>
          <p className="text-sm font-medium">
            Opportunity → Evidence → <span className="text-primary">Winning Profile™</span> → Alignment → Gaps → PDQ™ → Decision
          </p>
        </div>
        <button onClick={() => runMutation.mutate()} disabled={runMutation.isPending}
          className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50">
          <Play className="w-4 h-4" />
          {runMutation.isPending ? "Running…" : "Run Intelligence"}
        </button>
      </div>

      {/* Evidence package */}
      <DocumentsPanel solicitationId={solicitationId} documents={documents} isLoading={docsLoading} />

      {!profile ? (
        <div className="text-center py-16 text-muted-foreground border border-dashed border-border rounded-lg">
          <Target className="w-10 h-10 mx-auto mb-3 opacity-20" />
          <p className="font-medium">No hypothesis generated yet</p>
          <p className="text-sm mt-1">
            {documents.length === 0
              ? "Add at least one evidence document above, then run the intelligence pipeline."
              : "Run the intelligence pipeline to infer the winning profile."}
          </p>
        </div>
      ) : (
        <>
          {/* Executive assessment */}
          {assessment && <AssessmentPanel assessment={assessment} />}

          {/* Winning profile */}
          <ProfilePanel profile={profile} />

          {/* Rankings */}
          {rankings.length > 0 && <RankingPanel rankings={rankings} />}
        </>
      )}
    </div>
  );
}

// ── Assessment ───────────────────────────────────────────────────────────────────

function AssessmentPanel({ assessment }: { assessment: Assessment }) {
  const rec = assessment.recommendation;
  return (
    <div className="bg-card border border-border rounded-lg p-5 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold flex items-center gap-2">
          <Gauge className="w-4 h-4 text-primary" />
          Executive Opportunity Intelligence Assessment™
        </h2>
        <span className={cn("text-xs font-semibold uppercase tracking-wide px-3 py-1 rounded-full border", REC_STYLES[rec] ?? REC_STYLES.monitor)}>
          {rec.replace(/_/g, "-")}
        </span>
      </div>

      <div className="grid grid-cols-3 gap-3">
        <ScoreDial label="Pursuit Decision Quality™" value={assessment.pdq_score} icon={Gauge} />
        <ScoreDial label="Win Positioning" value={assessment.win_positioning_score} icon={Target} />
        <div className="bg-card border border-border rounded-lg p-4">
          <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
            <Trophy className="w-3.5 h-3.5" /> Competitive Rank
          </div>
          <div className="text-2xl font-bold font-mono">
            {assessment.competitive_rank ?? "—"}
            <span className="text-sm text-muted-foreground">/{assessment.candidate_pool_size}</span>
          </div>
        </div>
      </div>

      {assessment.executive_summary && (
        <p className="text-sm text-foreground/90 leading-relaxed">{assessment.executive_summary}</p>
      )}

      {assessment.critical_gaps.length > 0 && (
        <div>
          <p className="text-xs font-medium text-muted-foreground mb-2 flex items-center gap-1">
            <AlertTriangle className="w-3.5 h-3.5" /> Critical Gaps
          </p>
          <div className="space-y-1.5">
            {assessment.critical_gaps.map((g, i) => (
              <div key={i} className="flex items-start gap-2 text-sm">
                <span className={cn("text-[10px] uppercase px-1.5 py-0.5 rounded border shrink-0 mt-0.5", SEVERITY_STYLES[g.severity])}>
                  {g.severity}
                </span>
                <span className="text-foreground/80">{g.attribute_name} — {g.impact}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {assessment.recommended_actions.length > 0 && (
        <div>
          <p className="text-xs font-medium text-muted-foreground mb-2">Recommended Gap-Closure Actions</p>
          <ul className="space-y-1.5">
            {assessment.recommended_actions.slice(0, 5).map((a, i) => (
              <li key={i} className="text-sm text-foreground/80 flex gap-2">
                <span className="text-primary">→</span>
                <span>{a.recommendation}{a.timeline_months ? ` (${a.timeline_months}mo, ${a.feasibility} feasibility)` : ""}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {assessment.assumptions.length > 0 && (
        <details className="text-xs text-muted-foreground">
          <summary className="cursor-pointer hover:text-foreground">Assumptions &amp; limitations</summary>
          <ul className="mt-2 space-y-1 list-disc list-inside">
            {assessment.assumptions.map((a, i) => <li key={i}>{a}</li>)}
          </ul>
        </details>
      )}
    </div>
  );
}

// ── Profile ──────────────────────────────────────────────────────────────────────

function ProfilePanel({ profile }: { profile: Profile }) {
  const [expanded, setExpanded] = useState<string | null>(null);
  return (
    <div className="bg-card border border-border rounded-lg p-5 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold flex items-center gap-2">
          <Crosshair className="w-4 h-4 text-primary" />
          Winning Profile Hypothesis™
        </h2>
        <div className="flex gap-4 text-xs">
          <span className="text-muted-foreground">Confidence <span className="font-mono font-bold text-foreground">{profile.overall_confidence.toFixed(0)}</span></span>
          <span className="text-muted-foreground">Evidence <span className="font-mono font-bold text-foreground">{profile.evidence_strength.toFixed(0)}</span></span>
        </div>
      </div>

      {profile.narrative && (
        <p className="text-sm text-foreground/90 leading-relaxed bg-primary/5 border border-primary/10 rounded-md p-3">
          {profile.narrative}
        </p>
      )}
      {profile.summary && <p className="text-sm text-muted-foreground leading-relaxed">{profile.summary}</p>}

      <div className="space-y-2">
        {profile.attributes.map((attr) => {
          const isOpen = expanded === attr.name;
          const confColor = attr.confidence_level === "high" ? "text-emerald-400"
            : attr.confidence_level === "medium" ? "text-amber-400" : "text-muted-foreground";
          return (
            <div key={attr.name} className="border border-border rounded-lg overflow-hidden">
              <button onClick={() => setExpanded(isOpen ? null : attr.name)} className="w-full text-left px-3 py-2.5">
                <div className="flex items-center gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-medium truncate">{attr.name}</p>
                      <span className={cn("text-[10px] uppercase", confColor)}>{attr.confidence_level}</span>
                    </div>
                    <div className="mt-1.5 flex items-center gap-3">
                      <div className="flex-1"><Bar value={attr.importance_weight} className="bg-primary" /></div>
                      <span className="text-xs font-mono text-muted-foreground shrink-0 w-24 text-right">
                        imp {attr.importance_weight.toFixed(0)} · req {attr.required_level.toFixed(0)}
                      </span>
                    </div>
                  </div>
                  {isOpen ? <ChevronUp className="w-4 h-4 text-muted-foreground shrink-0" />
                    : <ChevronDown className="w-4 h-4 text-muted-foreground shrink-0" />}
                </div>
              </button>
              {isOpen && (
                <div className="px-3 pb-3 border-t border-border/50 pt-3 space-y-3 text-sm">
                  {attr.description && <p className="text-muted-foreground">{attr.description}</p>}
                  {attr.reasoning && (
                    <div className="bg-background/50 rounded-md p-2.5">
                      <p className="text-xs font-medium text-muted-foreground mb-1">Reasoning</p>
                      <p className="text-foreground/80 text-xs leading-relaxed">{attr.reasoning}</p>
                    </div>
                  )}
                  {attr.supporting_evidence.length > 0 && (
                    <div>
                      <p className="text-xs font-medium text-muted-foreground mb-1 flex items-center gap-1">
                        <ShieldCheck className="w-3.5 h-3.5" /> Supporting Evidence
                      </p>
                      <ul className="space-y-1.5">
                        {attr.supporting_evidence.map((e, i) => (
                          <li key={i} className="text-xs text-foreground/70 border-l-2 border-primary/30 pl-2">
                            “{e.text}” <span className="text-muted-foreground italic">— {e.source}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {attr.unknown_factors.length > 0 && (
                    <div className="text-xs text-amber-400/80">
                      <span className="font-medium">Unknown factors: </span>
                      {attr.unknown_factors.join(" ")}
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {profile.unknown_factors.length > 0 && (
        <div className="text-xs text-muted-foreground border-t border-border pt-3">
          <span className="font-medium text-amber-400/80">Package-level unknowns: </span>
          {profile.unknown_factors.join(" ")}
        </div>
      )}
    </div>
  );
}

// ── Rankings ─────────────────────────────────────────────────────────────────────

function RankingPanel({ rankings }: { rankings: Ranking[] }) {
  return (
    <div className="bg-card border border-border rounded-lg p-5 space-y-3">
      <h2 className="font-semibold flex items-center gap-2">
        <Layers className="w-4 h-4 text-primary" />
        Competitive Alignment Ranking™
      </h2>
      <div className="space-y-2">
        {rankings.map((r) => {
          const color = r.overall_alignment_score >= 70 ? "text-emerald-400"
            : r.overall_alignment_score >= 45 ? "text-amber-400" : "text-red-400";
          const criticalGaps = r.gaps.filter((g) => g.severity === "critical").length;
          return (
            <div key={r.contractor_id} className="border border-border rounded-lg p-3">
              <div className="flex items-center gap-3">
                <span className="flex items-center justify-center w-7 h-7 rounded-full bg-secondary text-sm font-bold shrink-0">
                  {r.rank}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{r.contractor_name}</p>
                  <div className="mt-1"><Bar value={r.overall_alignment_score} className={r.overall_alignment_score >= 70 ? "bg-emerald-400" : r.overall_alignment_score >= 45 ? "bg-amber-400" : "bg-red-400"} /></div>
                </div>
                <div className="text-right shrink-0">
                  <p className={cn("text-lg font-bold font-mono", color)}>{r.overall_alignment_score.toFixed(0)}</p>
                  <p className="text-[10px] text-muted-foreground">
                    {criticalGaps > 0 ? `${criticalGaps} critical gap${criticalGaps > 1 ? "s" : ""}` : "no critical gaps"}
                  </p>
                </div>
              </div>
              {r.summary && <p className="text-xs text-muted-foreground mt-2">{r.summary}</p>}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Documents ────────────────────────────────────────────────────────────────────

function DocumentsPanel({
  solicitationId, documents, isLoading,
}: { solicitationId: string; documents: EvidenceDocument[]; isLoading: boolean }) {
  const [showAdd, setShowAdd] = useState(false);
  const highValueCount = documents.filter(
    (d) => DOCUMENT_TYPES.find((t) => t.value === d.document_type)?.highValue
  ).length;

  return (
    <div className="bg-card border border-border rounded-lg p-5 space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold flex items-center gap-2">
          <FileText className="w-4 h-4 text-primary" />
          Evidence Package
          <span className="text-xs font-normal text-muted-foreground">
            {documents.length} document{documents.length === 1 ? "" : "s"}
            {highValueCount > 0 && ` · ${highValueCount} high-value`}
          </span>
        </h2>
        <button onClick={() => setShowAdd(true)}
          className="flex items-center gap-1.5 px-3 py-1.5 border border-border rounded-md text-xs font-medium hover:bg-secondary transition-colors">
          <Upload className="w-3.5 h-3.5" />
          Add Document
        </button>
      </div>

      {isLoading ? (
        <div className="h-10 bg-secondary/50 rounded-md animate-pulse" />
      ) : documents.length === 0 ? (
        <p className="text-sm text-muted-foreground py-2">
          No evidence documents yet. Add a Section M, Q&amp;A response, SOW/PWS, or other
          solicitation document to extract procurement signals from.
        </p>
      ) : (
        <div className="space-y-1.5">
          {documents.map((doc) => (
            <div key={doc.id} className="flex items-center gap-2 px-3 py-2 bg-background/50 rounded-md text-sm">
              {doc.is_extracted
                ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                : <FileText className="w-3.5 h-3.5 text-muted-foreground shrink-0" />}
              <span className="flex-1 truncate">{doc.title}</span>
              <span className="text-[10px] uppercase tracking-wide bg-secondary text-muted-foreground px-1.5 py-0.5 rounded shrink-0">
                {documentTypeLabel(doc.document_type)}
              </span>
            </div>
          ))}
        </div>
      )}

      {showAdd && (
        <AddDocumentModal solicitationId={solicitationId} onClose={() => setShowAdd(false)} />
      )}
    </div>
  );
}

function AddDocumentModal({
  solicitationId, onClose,
}: { solicitationId: string; onClose: () => void }) {
  const queryClient = useQueryClient();
  const [form, setForm] = useState({
    document_type: "statement_of_work", title: "", content: "", source_ref: "",
  });

  const addMutation = useMutation({
    mutationFn: () => api.addSolicitationDocument(solicitationId, {
      document_type: form.document_type,
      title: form.title,
      content: form.content,
      source_ref: form.source_ref || null,
    }),
    onSuccess: () => {
      toast.success("Document added — extract signals or run intelligence to include it");
      queryClient.invalidateQueries({ queryKey: ["wph-documents", solicitationId] });
      queryClient.invalidateQueries({ queryKey: ["wph-solicitations"] });
      onClose();
    },
    onError: () => toast.error("Failed to add document"),
  });

  const selected = DOCUMENT_TYPES.find((d) => d.value === form.document_type);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    addMutation.mutate();
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-card border border-border rounded-xl w-full max-w-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold text-lg">Add Evidence Document</h2>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground">
            <X className="w-4 h-4" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="block text-xs font-medium mb-1 text-muted-foreground">Document Type *</label>
            <select required value={form.document_type}
              onChange={(e) => setForm({ ...form, document_type: e.target.value })}
              className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/50">
              {DOCUMENT_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}{t.highValue ? " ★ high evidentiary value" : ""}
                </option>
              ))}
            </select>
            {selected?.highValue && (
              <p className="text-[11px] text-primary mt-1">
                ★ This document type carries above-average weight in the evidence-fusion engine.
              </p>
            )}
          </div>
          <div>
            <label className="block text-xs font-medium mb-1 text-muted-foreground">Title *</label>
            <input required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })}
              className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
              placeholder="Section M — Evaluation Factors for Award" />
          </div>
          <div>
            <label className="block text-xs font-medium mb-1 text-muted-foreground">
              Content * <span className="font-normal">(paste the document text)</span>
            </label>
            <textarea required value={form.content}
              onChange={(e) => setForm({ ...form, content: e.target.value })}
              rows={10}
              className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm font-mono resize-y focus:outline-none focus:ring-2 focus:ring-primary/50"
              placeholder="Paste the raw text of this document. The engine scans it sentence-by-sentence to extract and classify procurement signals — the more complete, the stronger the resulting hypothesis." />
            <p className="text-[11px] text-muted-foreground mt-1">{form.content.length.toLocaleString()} characters</p>
          </div>
          <div>
            <label className="block text-xs font-medium mb-1 text-muted-foreground">
              Source Reference <span className="font-normal">(optional — e.g. page/section citation)</span>
            </label>
            <input value={form.source_ref} onChange={(e) => setForm({ ...form, source_ref: e.target.value })}
              className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
              placeholder="Section M, ¶2.4" />
          </div>
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose}
              className="flex-1 py-2 border border-border rounded-md text-sm hover:bg-secondary transition-colors">
              Cancel
            </button>
            <button type="submit" disabled={addMutation.isPending}
              className="flex-1 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50">
              {addMutation.isPending ? "Adding…" : "Add Document"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Create modal ─────────────────────────────────────────────────────────────────

function CreateSolicitationModal({ onClose, onCreated }: { onClose: () => void; onCreated: (id: string) => void }) {
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    title: "", agency: "", solicitation_number: "", set_aside_type: "", description: "",
  });

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      const sol = await api.createSolicitation({
        title: form.title,
        agency: form.agency || null,
        solicitation_number: form.solicitation_number || null,
        set_aside_type: form.set_aside_type || null,
        description: form.description || null,
      });
      toast.success("Solicitation created — add evidence documents, then run intelligence");
      onCreated(sol.id);
    } catch {
      toast.error("Failed to create solicitation");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-card border border-border rounded-xl w-full max-w-lg p-6">
        <h2 className="font-semibold text-lg mb-4">New Solicitation Package</h2>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="block text-xs font-medium mb-1 text-muted-foreground">Title *</label>
            <input required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })}
              className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
              placeholder="Enterprise IT Modernization & Operations Support" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium mb-1 text-muted-foreground">Agency</label>
              <input value={form.agency} onChange={(e) => setForm({ ...form, agency: e.target.value })}
                className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                placeholder="Department of Veterans Affairs" />
            </div>
            <div>
              <label className="block text-xs font-medium mb-1 text-muted-foreground">Solicitation No.</label>
              <input value={form.solicitation_number} onChange={(e) => setForm({ ...form, solicitation_number: e.target.value })}
                className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                placeholder="FA8730-26-R-0042" />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium mb-1 text-muted-foreground">Set-Aside</label>
            <input value={form.set_aside_type} onChange={(e) => setForm({ ...form, set_aside_type: e.target.value })}
              className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
              placeholder="SDVOSB Set-Aside" />
          </div>
          <div>
            <label className="block text-xs font-medium mb-1 text-muted-foreground">Description</label>
            <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })}
              rows={2} className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary/50"
              placeholder="Brief description of the acquisition" />
          </div>
          <p className="text-xs text-muted-foreground">
            After creating, use the <span className="font-medium">Evidence Package</span> panel to
            add documents (Section M, Q&amp;A, SOW…), or use
            <span className="font-medium"> Load Sample</span> for a fully-worked example.
          </p>
          <div className="flex gap-3 pt-2">
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
