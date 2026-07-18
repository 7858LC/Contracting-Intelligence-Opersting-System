"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Building2, Plus, Shield, TrendingUp, AlertTriangle, ChevronDown, ChevronUp } from "lucide-react";

interface Competitor {
  id: string;
  company_name: string;
  cage_code: string | null;
  annual_contract_volume: number | null;
  primary_naics_codes: string[];
  strengths: string[];
  weaknesses: string[];
  typical_price_positioning: string | null;
  socioeconomic_statuses: string[];
  active_clearances: string[];
  certifications: string[];
  win_rate_estimate: number | null;
  threat_level: string | null;
  notes: string | null;
}

interface CompetitorIntel {
  id: string;
  competitor_id: string;
  intel_type: string;
  title: string;
  content: string;
  source: string | null;
  confidence: number | null;
  opportunity_id: string | null;
  created_at: string;
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
          {comps.map((comp) => (
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
                      {comp.typical_price_positioning && <span>{comp.typical_price_positioning}</span>}
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-1 max-w-[200px]">
                    {comp.socioeconomic_statuses?.slice(0, 2).map((s) => (
                      <span key={s} className="text-xs bg-blue-500/10 text-blue-400 px-1.5 py-0.5 rounded">{s}</span>
                    ))}
                    {comp.active_clearances?.slice(0, 2).map((c) => (
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
                    {comp.strengths?.length > 0 && (
                      <div>
                        <p className="text-xs text-muted-foreground mb-1.5 flex items-center gap-1">
                          <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />
                          Strengths
                        </p>
                        <ul className="space-y-1">
                          {comp.strengths.map((s) => (
                            <li key={s} className="text-xs flex items-start gap-1.5">
                              <span className="text-emerald-400 shrink-0">+</span>
                              {s}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {comp.weaknesses?.length > 0 && (
                      <div>
                        <p className="text-xs text-muted-foreground mb-1.5 flex items-center gap-1">
                          <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
                          Weaknesses
                        </p>
                        <ul className="space-y-1">
                          {comp.weaknesses.map((w) => (
                            <li key={w} className="text-xs flex items-start gap-1.5">
                              <span className="text-amber-400 shrink-0">−</span>
                              {w}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>

                  {comp.certifications?.length > 0 && (
                    <div>
                      <p className="text-xs text-muted-foreground mb-1.5">Certifications</p>
                      <div className="flex flex-wrap gap-1.5">
                        {comp.certifications.map((c) => (
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
          ))}
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

function AddCompetitorModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    company_name: "", cage_code: "", annual_contract_volume: "",
    strengths: "", weaknesses: "", typical_price_positioning: "",
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
        strengths: split(form.strengths),
        weaknesses: split(form.weaknesses),
        typical_price_positioning: form.typical_price_positioning || null,
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
            <input value={form.strengths} onChange={(e) => setForm({ ...form, strengths: e.target.value })}
              className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
              placeholder="Incumbent, strong past performance, low pricing" />
          </div>
          <div>
            <label className="block text-xs font-medium mb-1 text-muted-foreground">Weaknesses (comma separated)</label>
            <input value={form.weaknesses} onChange={(e) => setForm({ ...form, weaknesses: e.target.value })}
              className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
              placeholder="High overhead, staff turnover, limited clearances" />
          </div>
          <div>
            <label className="block text-xs font-medium mb-1 text-muted-foreground">Price Positioning</label>
            <select value={form.typical_price_positioning} onChange={(e) => setForm({ ...form, typical_price_positioning: e.target.value })}
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
