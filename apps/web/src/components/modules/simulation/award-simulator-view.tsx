"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Award, ChevronRight, Loader2, Plus, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import api from "@/lib/api";
import { formatProbability, getScoreColor, getScoreLabel, cn } from "@/lib/utils";

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
    mutationFn: (payload: any) => api.createSimulation(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["simulations"] });
      setShowNewForm(false);
      toast.success("Award simulation queued. Results in 1–3 minutes.");
    },
    onError: () => toast.error("Failed to create simulation"),
  });

  const simulations = simsData?.items || [];
  const opportunities = oppsData?.items || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Award className="w-6 h-6 text-primary" />
            Award Simulator
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Emulate government source selection before proposal submission
          </p>
        </div>
        <button
          onClick={() => setShowNewForm(true)}
          className="flex items-center gap-2 bg-primary text-primary-foreground px-4 py-2 rounded-md text-sm font-medium hover:bg-primary/90 transition-colors"
        >
          <Plus className="w-4 h-4" />
          New Simulation
        </button>
      </div>

      {showNewForm && (
        <NewSimulationForm
          opportunities={opportunities}
          onSubmit={(p) => createMutation.mutate(p)}
          onCancel={() => setShowNewForm(false)}
          isLoading={createMutation.isPending}
        />
      )}

      <div className="grid gap-4">
        {isLoading ? (
          <div className="text-center py-12 text-muted-foreground">
            <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />
            Loading simulations...
          </div>
        ) : simulations.length === 0 ? (
          <EmptyState onNew={() => setShowNewForm(true)} />
        ) : (
          simulations.map((sim: any) => (
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

function SimulationCard({ sim, onClick, expanded }: { sim: any; onClick: () => void; expanded: boolean }) {
  const prob = sim.award_probability;
  const isCompleted = sim.status === "completed";
  const isRunning = sim.status === "running" || sim.status === "queued";

  return (
    <div
      className={cn(
        "border border-border rounded-xl bg-card overflow-hidden cursor-pointer hover:border-primary/50 transition-colors",
        expanded && "border-primary"
      )}
      onClick={onClick}
    >
      <div className="p-5 flex items-center gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="font-semibold truncate">{sim.name}</h3>
            {isRunning && <Loader2 className="w-3.5 h-3.5 animate-spin text-primary shrink-0" />}
          </div>
          <div className="text-xs text-muted-foreground">{sim.evaluation_methodology}</div>
        </div>

        <div className="flex items-center gap-6 shrink-0">
          {isCompleted && prob != null && (
            <div className="text-right">
              <div className={`text-2xl font-bold ${getScoreColor((prob || 0) * 100)}`}>
                {formatProbability(prob)}
              </div>
              <div className="text-xs text-muted-foreground">Award Probability</div>
            </div>
          )}
          {isCompleted && sim.gate_review_recommendation && (
            <div className={cn(
              "px-3 py-1.5 rounded-md text-xs font-bold tracking-wide",
              sim.gate_review_recommendation === "SUBMIT" ? "bg-emerald-500/10 text-emerald-500" :
              sim.gate_review_recommendation === "WITHDRAW" ? "bg-red-500/10 text-red-500" :
              "bg-amber-500/10 text-amber-500"
            )}>
              {sim.gate_review_recommendation}
            </div>
          )}
          {isRunning && (
            <div className="text-xs text-muted-foreground">Analyzing...</div>
          )}
          <ChevronRight className={cn("w-4 h-4 text-muted-foreground transition-transform", expanded && "rotate-90")} />
        </div>
      </div>

      {expanded && isCompleted && (
        <div className="border-t border-border p-5 space-y-4">
          {/* Score breakdown */}
          <div className="grid grid-cols-3 gap-4">
            {[
              { label: "Technical", value: sim.technical_score },
              { label: "Mgmt", value: sim.management_score },
              { label: "Past Perf.", value: sim.past_performance_score },
              { label: "Price", value: sim.price_competitiveness_score },
              { label: "Compliance", value: sim.compliance_score },
              { label: "Risk", value: sim.risk_score },
            ].map(({ label, value }) => (
              <div key={label} className="bg-secondary/50 rounded-lg p-3 text-center">
                <div className={`text-lg font-bold ${getScoreColor(value)}`}>
                  {value != null ? Math.round(value) : "—"}
                </div>
                <div className="text-xs text-muted-foreground">{label}</div>
                <div className="text-xs mt-0.5 font-medium" style={{ color: "inherit" }}>
                  {getScoreLabel(value)}
                </div>
              </div>
            ))}
          </div>

          {/* Executive summary */}
          {sim.executive_summary && (
            <div>
              <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">Executive Summary</div>
              <p className="text-sm text-foreground/80 leading-relaxed">{sim.executive_summary}</p>
            </div>
          )}

          {/* Deficiencies */}
          {sim.deficiencies?.length > 0 && (
            <div>
              <div className="text-xs font-semibold text-red-500 uppercase tracking-wide mb-2">
                Deficiencies ({sim.deficiencies.length})
              </div>
              <ul className="space-y-1">
                {sim.deficiencies.slice(0, 3).map((d: any, i: number) => (
                  <li key={i} className="text-sm text-red-400 flex items-start gap-2">
                    <span className="mt-1">•</span>
                    {typeof d === "string" ? d : d.description || JSON.stringify(d)}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Top improvements */}
          {sim.suggested_improvements?.length > 0 && (
            <div>
              <div className="text-xs font-semibold text-primary uppercase tracking-wide mb-2">
                Top Improvements
              </div>
              <ul className="space-y-1">
                {sim.suggested_improvements.slice(0, 3).map((imp: any, i: number) => (
                  <li key={i} className="text-sm flex items-start gap-2">
                    <span className="text-primary mt-1">{i + 1}.</span>
                    {typeof imp === "string" ? imp : imp.description || JSON.stringify(imp)}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function NewSimulationForm({ opportunities, onSubmit, onCancel, isLoading }: {
  opportunities: any[]; onSubmit: (p: any) => void; onCancel: () => void; isLoading: boolean;
}) {
  const [form, setForm] = useState({
    opportunity_id: "",
    name: "",
    evaluation_methodology: "BEST_VALUE_TRADEOFF",
    proposal_content: {
      technical: "",
      management: "",
      past_performance: "",
      price: "",
    },
  });

  return (
    <div className="border border-primary/50 rounded-xl bg-card p-6 space-y-4">
      <h2 className="font-semibold text-lg">New Award Simulation</h2>

      <div className="grid md:grid-cols-2 gap-4">
        <div>
          <label className="text-xs font-medium text-muted-foreground mb-1 block">Opportunity</label>
          <select
            value={form.opportunity_id}
            onChange={(e) => setForm({ ...form, opportunity_id: e.target.value })}
            className="w-full bg-background border border-border rounded-md px-3 py-2 text-sm"
          >
            <option value="">Select opportunity...</option>
            {opportunities.map((o: any) => (
              <option key={o.id} value={o.id}>{o.title}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-xs font-medium text-muted-foreground mb-1 block">Simulation Name</label>
          <input
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            placeholder="e.g., Initial Gate Review — Q3 2026"
            className="w-full bg-background border border-border rounded-md px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="text-xs font-medium text-muted-foreground mb-1 block">Evaluation Methodology</label>
          <select
            value={form.evaluation_methodology}
            onChange={(e) => setForm({ ...form, evaluation_methodology: e.target.value })}
            className="w-full bg-background border border-border rounded-md px-3 py-2 text-sm"
          >
            <option value="BEST_VALUE_TRADEOFF">Best Value Tradeoff (FAR 15.101-1)</option>
            <option value="LPTA">LPTA (FAR 15.101-2)</option>
            <option value="BEST_VALUE_CONTINUUM">Best Value Continuum (DoD)</option>
            <option value="MEAT">MEAT (EU Directive 2014/24)</option>
            <option value="QCBS">QCBS (World Bank)</option>
          </select>
        </div>
      </div>

      <div className="space-y-3">
        <div className="text-xs font-medium text-muted-foreground">Proposal Content (optional — for pre-submission review)</div>
        <textarea
          value={form.proposal_content.technical}
          onChange={(e) => setForm({ ...form, proposal_content: { ...form.proposal_content, technical: e.target.value } })}
          placeholder="Technical approach summary or key sections..."
          className="w-full bg-background border border-border rounded-md px-3 py-2 text-sm h-24 resize-none"
        />
      </div>

      <div className="flex items-center gap-3">
        <button
          onClick={() => onSubmit(form)}
          disabled={isLoading || !form.opportunity_id || !form.name}
          className="flex items-center gap-2 bg-primary text-primary-foreground px-6 py-2 rounded-md text-sm font-medium hover:bg-primary/90 disabled:opacity-50 transition-colors"
        >
          {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Award className="w-4 h-4" />}
          Run Simulation
        </button>
        <button onClick={onCancel} className="text-sm text-muted-foreground hover:text-foreground transition-colors">
          Cancel
        </button>
      </div>
    </div>
  );
}

function EmptyState({ onNew }: { onNew: () => void }) {
  return (
    <div className="border border-dashed border-border rounded-xl p-12 text-center">
      <Award className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
      <h3 className="font-semibold text-lg mb-2">No simulations yet</h3>
      <p className="text-sm text-muted-foreground mb-6 max-w-sm mx-auto">
        Run your first award simulation to see how government evaluators would score your proposal.
      </p>
      <button
        onClick={onNew}
        className="bg-primary text-primary-foreground px-6 py-2 rounded-md text-sm font-medium hover:bg-primary/90 transition-colors"
      >
        Run First Simulation
      </button>
    </div>
  );
}
