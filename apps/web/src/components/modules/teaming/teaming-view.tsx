"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Users, Plus, Star, Building2, ChevronDown, ChevronUp } from "lucide-react";

interface TeamingRecommendation {
  id: string;
  opportunity_id: string;
  opportunity_title: string;
  prime_or_sub: string;
  recommended_partners: Record<string, unknown>[];
  teaming_rationale: string | null;
  capability_gaps_addressed: string[];
  risk_assessment: Record<string, unknown> | null;
  confidence_score: number | null;
  created_at: string;
}

interface TeamingPartner {
  id: string;
  company_name: string;
  cage_code: string | null;
  sam_unique_id: string | null;
  naics_codes: string[];
  socioeconomic_status: string[];
  past_performance_rating: number | null;
  relationship_strength: number;
  notes: string | null;
  active_agreements: boolean;
}

export function TeamingView() {
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<"recommendations" | "partners">("recommendations");
  const [expanded, setExpanded] = useState<string | null>(null);
  const [showAddPartner, setShowAddPartner] = useState(false);

  const { data: recommendations = [], isLoading: loadingRecs } = useQuery({
    queryKey: ["teaming-recommendations"],
    queryFn: () => api.getTeamingRecommendations(),
  });

  const { data: partners = [], isLoading: loadingPartners } = useQuery({
    queryKey: ["teaming-partners"],
    queryFn: () => api.getTeamingPartners(),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Teaming Recommendation Engine</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            {(recommendations as TeamingRecommendation[]).length} recommendations · {(partners as TeamingPartner[]).length} partners in registry
          </p>
        </div>
        <button onClick={() => setShowAddPartner(true)}
          className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition-colors">
          <Plus className="w-4 h-4" />
          Add Partner
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-card border border-border rounded-md p-1 w-fit">
        {(["recommendations", "partners"] as const).map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={cn("px-4 py-1.5 rounded text-sm font-medium transition-colors",
              tab === t ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground")}>
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {tab === "recommendations" && (
        loadingRecs ? (
          <div className="space-y-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="h-20 bg-card border border-border rounded-lg animate-pulse" />
            ))}
          </div>
        ) : (recommendations as TeamingRecommendation[]).length === 0 ? (
          <div className="text-center py-16 text-muted-foreground">
            <Users className="w-12 h-12 mx-auto mb-3 opacity-20" />
            <p className="font-medium">No teaming recommendations yet</p>
            <p className="text-sm mt-1">Run AI analysis on an opportunity to generate teaming recommendations.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {(recommendations as TeamingRecommendation[]).map((rec) => (
              <div key={rec.id} className="bg-card border border-border rounded-lg overflow-hidden">
                <button onClick={() => setExpanded(expanded === rec.id ? null : rec.id)}
                  className="w-full text-left px-4 py-3">
                  <div className="flex items-center gap-3">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{rec.opportunity_title}</p>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className={cn("text-xs px-1.5 py-0.5 rounded",
                          rec.prime_or_sub === "prime" ? "bg-primary/20 text-primary" : "bg-secondary text-muted-foreground")}>
                          {rec.prime_or_sub === "prime" ? "Prime" : "Sub"}
                        </span>
                        <span className="text-xs text-muted-foreground">
                          {rec.recommended_partners?.length || 0} recommended partners
                        </span>
                        {rec.confidence_score != null && (
                          <span className="text-xs text-muted-foreground">
                            {(rec.confidence_score * 100).toFixed(0)}% confidence
                          </span>
                        )}
                      </div>
                    </div>
                    {expanded === rec.id
                      ? <ChevronUp className="w-4 h-4 text-muted-foreground" />
                      : <ChevronDown className="w-4 h-4 text-muted-foreground" />
                    }
                  </div>
                </button>

                {expanded === rec.id && (
                  <div className="px-4 pb-4 border-t border-border/50 pt-4 space-y-3">
                    {rec.teaming_rationale && (
                      <div className="bg-background/50 rounded-md p-3">
                        <p className="text-xs font-medium text-muted-foreground mb-1">Rationale</p>
                        <p className="text-sm">{rec.teaming_rationale}</p>
                      </div>
                    )}
                    {rec.capability_gaps_addressed?.length > 0 && (
                      <div>
                        <p className="text-xs text-muted-foreground mb-1.5">Gaps Addressed</p>
                        <div className="flex flex-wrap gap-1.5">
                          {rec.capability_gaps_addressed.map((g) => (
                            <span key={g} className="text-xs bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded-full">
                              {g}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                    {rec.recommended_partners?.length > 0 && (
                      <div>
                        <p className="text-xs text-muted-foreground mb-2">Recommended Partners</p>
                        <div className="space-y-2">
                          {rec.recommended_partners.map((p, i) => (
                            <div key={i} className="flex items-center gap-2 text-sm p-2 bg-background/50 rounded">
                              <Building2 className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
                              <span>{(p as { company_name?: string }).company_name || JSON.stringify(p)}</span>
                              {(p as { rationale?: string }).rationale && (
                                <span className="text-xs text-muted-foreground ml-auto max-w-xs truncate">
                                  {(p as { rationale: string }).rationale}
                                </span>
                              )}
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
        )
      )}

      {tab === "partners" && (
        loadingPartners ? (
          <div className="grid grid-cols-2 gap-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-28 bg-card border border-border rounded-lg animate-pulse" />
            ))}
          </div>
        ) : (partners as TeamingPartner[]).length === 0 ? (
          <div className="text-center py-16 text-muted-foreground">
            <Building2 className="w-12 h-12 mx-auto mb-3 opacity-20" />
            <p className="font-medium">No partners in registry</p>
            <p className="text-sm mt-1">Add teaming partners to build your network.</p>
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-3">
            {(partners as TeamingPartner[]).map((p) => (
              <div key={p.id} className="bg-card border border-border rounded-lg p-4">
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-sm">{p.company_name}</p>
                    {p.cage_code && <p className="text-xs text-muted-foreground mt-0.5">CAGE: {p.cage_code}</p>}
                  </div>
                  {p.active_agreements && (
                    <span className="text-xs bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-1.5 py-0.5 rounded shrink-0">
                      Active TAs
                    </span>
                  )}
                </div>
                <div className="mt-2 flex flex-wrap gap-1">
                  {p.socioeconomic_status?.map((s) => (
                    <span key={s} className="text-xs bg-blue-500/10 text-blue-400 px-1.5 py-0.5 rounded">{s}</span>
                  ))}
                </div>
                {p.past_performance_rating != null && (
                  <div className="flex items-center gap-1 mt-2">
                    {Array.from({ length: 5 }).map((_, i) => (
                      <Star key={i} className={cn("w-3 h-3", i < p.past_performance_rating! ? "text-amber-400 fill-amber-400" : "text-border")} />
                    ))}
                    <span className="text-xs text-muted-foreground ml-1">Past performance</span>
                  </div>
                )}
                {p.notes && <p className="text-xs text-muted-foreground mt-2 line-clamp-2">{p.notes}</p>}
              </div>
            ))}
          </div>
        )
      )}

      {showAddPartner && (
        <AddPartnerModal
          onClose={() => setShowAddPartner(false)}
          onCreated={() => { setShowAddPartner(false); queryClient.invalidateQueries({ queryKey: ["teaming-partners"] }); }}
        />
      )}
    </div>
  );
}

function AddPartnerModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    company_name: "", cage_code: "", naics_codes: "",
    socioeconomic_status: "", relationship_strength: "3", active_agreements: false, notes: "",
  });

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      await api.createTeamingPartner({
        company_name: form.company_name,
        cage_code: form.cage_code || null,
        naics_codes: form.naics_codes ? form.naics_codes.split(",").map((s) => s.trim()).filter(Boolean) : [],
        socioeconomic_status: form.socioeconomic_status ? form.socioeconomic_status.split(",").map((s) => s.trim()).filter(Boolean) : [],
        relationship_strength: parseInt(form.relationship_strength),
        active_agreements: form.active_agreements,
        notes: form.notes || null,
      });
      toast.success("Partner added to registry");
      onCreated();
    } catch {
      toast.error("Failed to add partner");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-card border border-border rounded-xl w-full max-w-lg p-6">
        <h2 className="font-semibold text-lg mb-4">Add Teaming Partner</h2>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium mb-1 text-muted-foreground">Company Name *</label>
              <input required value={form.company_name} onChange={(e) => setForm({ ...form, company_name: e.target.value })}
                className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                placeholder="Acme Tech Solutions" />
            </div>
            <div>
              <label className="block text-xs font-medium mb-1 text-muted-foreground">CAGE Code</label>
              <input value={form.cage_code} onChange={(e) => setForm({ ...form, cage_code: e.target.value })}
                className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                placeholder="1ABC2" />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium mb-1 text-muted-foreground">Socioeconomic Status (comma separated)</label>
            <input value={form.socioeconomic_status} onChange={(e) => setForm({ ...form, socioeconomic_status: e.target.value })}
              className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
              placeholder="8a, SDVOSB, Small Business" />
          </div>
          <div>
            <label className="block text-xs font-medium mb-1 text-muted-foreground">NAICS Codes</label>
            <input value={form.naics_codes} onChange={(e) => setForm({ ...form, naics_codes: e.target.value })}
              className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
              placeholder="541512, 541519" />
          </div>
          <div>
            <label className="block text-xs font-medium mb-1 text-muted-foreground">Relationship Strength (1–5)</label>
            <select value={form.relationship_strength} onChange={(e) => setForm({ ...form, relationship_strength: e.target.value })}
              className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none">
              {[1, 2, 3, 4, 5].map((n) => <option key={n} value={n}>{n} – {["", "Cold", "Warm", "Active", "Strong", "Strategic"][n]}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium mb-1 text-muted-foreground">Notes</label>
            <textarea value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })}
              rows={2} className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary/50"
              placeholder="Teaming history, point of contact, etc." />
          </div>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={form.active_agreements} onChange={(e) => setForm({ ...form, active_agreements: e.target.checked })} className="rounded" />
            Active teaming agreements in place
          </label>
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose}
              className="flex-1 py-2 border border-border rounded-md text-sm hover:bg-secondary transition-colors">
              Cancel
            </button>
            <button type="submit" disabled={loading}
              className="flex-1 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50">
              {loading ? "Adding…" : "Add Partner"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
