"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Brain, Plus, ChevronDown, ChevronUp, AlertTriangle, CheckCircle2, TrendingUp } from "lucide-react";

interface Capability {
  id: string;
  name: string;
  description: string | null;
  category: string;
  proficiency_level: number;
  is_certified: boolean;
  certifications: string[];
  gap_score: number | null;
  gap_analysis: Record<string, unknown> | null;
  improvement_plan: string | null;
  naics_codes: string[];
  created_at: string;
}

const CATEGORIES = [
  "technical", "management", "past_performance", "financial",
  "security_clearance", "compliance", "operational", "other"
];

const PROFICIENCY_LABELS = ["", "Beginner", "Basic", "Intermediate", "Advanced", "Expert"];

function ProficiencyBar({ level }: { level: number }) {
  const colors = ["", "bg-red-400", "bg-orange-400", "bg-amber-400", "bg-blue-400", "bg-emerald-400"];
  return (
    <div className="flex gap-0.5">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className={cn("h-2 w-5 rounded-sm", i < level ? colors[level] : "bg-secondary")} />
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
                      <p className="text-xs text-muted-foreground mt-0.5">{PROFICIENCY_LABELS[cap.proficiency_level]}</p>
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
                        {cap.certifications.map((cert) => (
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
