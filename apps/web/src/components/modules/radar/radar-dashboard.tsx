"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import {
  Activity,
  AlertCircle,
  BarChart3,
  Building2,
  ChevronRight,
  Filter,
  Loader2,
  Plus,
  Radar,
  RefreshCw,
  Search,
  Star,
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
  industry: string | null;
  headquarters_state: string | null;
  overall_signal_score: number;
  confidence_score: number;
  growth_momentum_score: number;
  government_readiness_score: number;
  priority_tier: "A" | "B" | "C";
  is_watched: boolean;
  signal_count: number;
  last_scanned_at: string | null;
  naics_codes: string[];
  set_aside_types: string[];
}

interface DashboardStats {
  total_companies: number;
  tier_a_count: number;
  tier_b_count: number;
  tier_c_count: number;
  watched_count: number;
  signals_last_7d: number;
  avg_signal_score: number;
  top_signal_types: { signal_type: string; count: number }[];
  scan_jobs_running: number;
}

// ── Tier badge ─────────────────────────────────────────────────────────────

function TierBadge({ tier }: { tier: "A" | "B" | "C" }) {
  return (
    <span
      className={cn(
        "inline-flex items-center justify-center w-6 h-6 rounded-full text-[11px] font-bold",
        tier === "A" && "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400",
        tier === "B" && "bg-amber-500/15 text-amber-600 dark:text-amber-400",
        tier === "C" && "bg-slate-200 text-slate-500 dark:bg-slate-700 dark:text-slate-400"
      )}
    >
      {tier}
    </span>
  );
}

// ── Score bar ──────────────────────────────────────────────────────────────

function ScoreBar({ value, tier }: { value: number; tier: "A" | "B" | "C" }) {
  const color =
    tier === "A" ? "bg-emerald-500"
    : tier === "B" ? "bg-amber-500"
    : "bg-slate-400";
  return (
    <div className="w-16 bg-secondary rounded-full h-1.5">
      <div
        className={cn("h-1.5 rounded-full transition-all", color)}
        style={{ width: `${Math.min(100, value)}%` }}
      />
    </div>
  );
}

// ── KPI tile ───────────────────────────────────────────────────────────────

function KpiTile({
  label,
  value,
  sub,
  icon: Icon,
  color = "text-foreground",
}: {
  label: string;
  value: string | number;
  sub?: string;
  icon: React.ElementType;
  color?: string;
}) {
  return (
    <div className="bg-card border border-border rounded-lg p-4 flex gap-3 items-start">
      <div className="w-9 h-9 rounded-md bg-secondary flex items-center justify-center shrink-0">
        <Icon className={cn("w-4.5 h-4.5", color)} />
      </div>
      <div>
        <div className={cn("text-2xl font-bold tracking-tight", color)}>{value}</div>
        <div className="text-xs text-muted-foreground leading-tight">{label}</div>
        {sub && <div className="text-[10px] text-muted-foreground/70 mt-0.5">{sub}</div>}
      </div>
    </div>
  );
}

// ── Signal type label ──────────────────────────────────────────────────────

function signalLabel(raw: string): string {
  return raw.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

// ── Add company modal ──────────────────────────────────────────────────────

function AddCompanyModal({
  onClose,
  onSaved,
}: {
  onClose: () => void;
  onSaved: () => void;
}) {
  const [name, setName] = useState("");
  const [domain, setDomain] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await api.createCompany({ name: name.trim(), domain: domain.trim() || undefined });
      onSaved();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to add company";
      setError(msg);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-card border border-border rounded-xl shadow-2xl w-full max-w-md p-6">
        <h2 className="text-lg font-semibold mb-4">Add Company to Radar</h2>
        <form onSubmit={submit} className="space-y-3">
          <div>
            <label className="text-sm font-medium">Company Name *</label>
            <input
              autoFocus
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Acme Defense Systems"
              className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
          <div>
            <label className="text-sm font-medium">Domain (optional)</label>
            <input
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
              placeholder="acmedefense.com"
              className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
          {error && (
            <p className="text-sm text-destructive flex items-center gap-1">
              <AlertCircle className="w-3.5 h-3.5" /> {error}
            </p>
          )}
          <div className="flex gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 rounded-md border border-border text-sm hover:bg-secondary transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving || !name.trim()}
              className="flex-1 px-4 py-2 rounded-md bg-primary text-primary-foreground text-sm font-medium disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {saving && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              Add Company
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Main dashboard ─────────────────────────────────────────────────────────

export function RadarDashboard() {
  const qc = useQueryClient();
  const [search, setSearch] = useState("");
  const [tierFilter, setTierFilter] = useState<"" | "A" | "B" | "C">("");
  const [showModal, setShowModal] = useState(false);

  const { data: stats, isLoading: statsLoading } = useQuery<DashboardStats>({
    queryKey: ["radar-stats"],
    queryFn: () => api.getRadarDashboard(),
    refetchInterval: 30_000,
  });

  const { data: companiesData, isLoading: companiesLoading, refetch } = useQuery({
    queryKey: ["radar-companies", search, tierFilter],
    queryFn: () =>
      api.listCompanies({
        search: search || undefined,
        tier: tierFilter || undefined,
        sort_by: "overall_signal_score",
        order: "desc",
        page_size: 50,
      }),
  });

  const companies: Company[] = companiesData?.items ?? [];

  const bulkScanMutation = useMutation({
    mutationFn: () => api.triggerBulkScan(60, false),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["radar-stats"] });
    },
  });

  function handleSaved() {
    setShowModal(false);
    qc.invalidateQueries({ queryKey: ["radar-companies"] });
    qc.invalidateQueries({ queryKey: ["radar-stats"] });
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <Radar className="w-5 h-5 text-primary" />
            <h1 className="text-xl font-bold tracking-tight">Procurement Intelligence Radar™</h1>
          </div>
          <p className="text-sm text-muted-foreground mt-0.5">
            Detect companies building GovCon capability before they compete against you.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => bulkScanMutation.mutate()}
            disabled={bulkScanMutation.isPending || (stats?.scan_jobs_running ?? 0) > 0}
            className="flex items-center gap-2 px-3 py-2 rounded-md border border-border text-sm hover:bg-secondary transition-colors disabled:opacity-50"
          >
            <RefreshCw className={cn("w-3.5 h-3.5", bulkScanMutation.isPending && "animate-spin")} />
            Scan All
          </button>
          <button
            onClick={() => setShowModal(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-md bg-primary text-primary-foreground text-sm font-medium"
          >
            <Plus className="w-3.5 h-3.5" />
            Add Company
          </button>
        </div>
      </div>

      {/* KPI tiles */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <KpiTile
          label="Total Companies"
          value={stats?.total_companies ?? "—"}
          icon={Building2}
          sub={`${stats?.watched_count ?? 0} watched`}
        />
        <KpiTile
          label="Tier A Prospects"
          value={stats?.tier_a_count ?? "—"}
          icon={TrendingUp}
          color="text-emerald-500"
          sub="Score ≥ 60"
        />
        <KpiTile
          label="Signals (7 days)"
          value={stats?.signals_last_7d ?? "—"}
          icon={Zap}
          color="text-amber-500"
        />
        <KpiTile
          label="Avg Signal Score"
          value={stats ? `${stats.avg_signal_score}/100` : "—"}
          icon={Activity}
          color="text-blue-500"
        />
      </div>

      {/* Top signal types */}
      {stats?.top_signal_types && stats.top_signal_types.length > 0 && (
        <div className="bg-card border border-border rounded-lg p-4">
          <div className="text-sm font-medium mb-3">Top Signal Types Detected</div>
          <div className="flex flex-wrap gap-2">
            {stats.top_signal_types.map((t) => (
              <span
                key={t.signal_type}
                className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs bg-secondary text-secondary-foreground"
              >
                <span className="w-1.5 h-1.5 rounded-full bg-primary" />
                {signalLabel(t.signal_type)}
                <span className="text-muted-foreground font-medium">{t.count}</span>
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search companies…"
            className="w-full pl-9 pr-3 py-2 text-sm rounded-md border border-border bg-background focus:outline-none focus:ring-2 focus:ring-primary"
          />
        </div>
        <div className="flex items-center gap-1">
          <Filter className="w-3.5 h-3.5 text-muted-foreground" />
          {(["", "A", "B", "C"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTierFilter(t)}
              className={cn(
                "px-3 py-1.5 rounded-md text-xs font-medium transition-colors",
                tierFilter === t
                  ? "bg-primary text-primary-foreground"
                  : "border border-border hover:bg-secondary text-muted-foreground"
              )}
            >
              {t || "All"}
            </button>
          ))}
        </div>
      </div>

      {/* Company table */}
      <div className="bg-card border border-border rounded-lg overflow-hidden">
        {companiesLoading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
          </div>
        ) : companies.length === 0 ? (
          <div className="text-center py-16 text-muted-foreground">
            <Radar className="w-10 h-10 mx-auto mb-3 opacity-20" />
            <p className="text-sm font-medium">No companies yet</p>
            <p className="text-xs mt-1">Add companies to start tracking procurement signals</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-secondary/40">
                <th className="text-left px-4 py-2.5 font-medium text-muted-foreground text-xs">Company</th>
                <th className="text-left px-3 py-2.5 font-medium text-muted-foreground text-xs">Tier</th>
                <th className="text-left px-3 py-2.5 font-medium text-muted-foreground text-xs hidden sm:table-cell">Score</th>
                <th className="text-left px-3 py-2.5 font-medium text-muted-foreground text-xs hidden md:table-cell">Signals</th>
                <th className="text-left px-3 py-2.5 font-medium text-muted-foreground text-xs hidden lg:table-cell">State</th>
                <th className="text-left px-3 py-2.5 font-medium text-muted-foreground text-xs hidden lg:table-cell">Certifications</th>
                <th className="w-8" />
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {companies.map((c) => (
                <tr
                  key={c.id}
                  className="hover:bg-secondary/30 transition-colors"
                >
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      {c.is_watched && <Star className="w-3 h-3 text-amber-400 shrink-0" />}
                      <div>
                        <div className="font-medium text-sm">{c.name}</div>
                        {c.domain && (
                          <div className="text-xs text-muted-foreground">{c.domain}</div>
                        )}
                      </div>
                    </div>
                  </td>
                  <td className="px-3 py-3">
                    <TierBadge tier={c.priority_tier} />
                  </td>
                  <td className="px-3 py-3 hidden sm:table-cell">
                    <div className="flex items-center gap-2">
                      <ScoreBar value={c.overall_signal_score} tier={c.priority_tier} />
                      <span className="text-xs text-muted-foreground w-8 text-right">
                        {Math.round(c.overall_signal_score)}
                      </span>
                    </div>
                  </td>
                  <td className="px-3 py-3 hidden md:table-cell">
                    <span className="text-xs font-medium">{c.signal_count}</span>
                  </td>
                  <td className="px-3 py-3 hidden lg:table-cell">
                    <span className="text-xs text-muted-foreground">
                      {c.headquarters_state ?? "—"}
                    </span>
                  </td>
                  <td className="px-3 py-3 hidden lg:table-cell">
                    <div className="flex flex-wrap gap-1">
                      {c.set_aside_types.slice(0, 2).map((s) => (
                        <span
                          key={s}
                          className="px-1.5 py-0.5 rounded text-[10px] bg-blue-500/10 text-blue-600 dark:text-blue-400 font-medium"
                        >
                          {s}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="pr-3 py-3">
                    <Link
                      href={`/dashboard/radar/${c.id}`}
                      className="flex items-center justify-center w-7 h-7 rounded-md hover:bg-secondary transition-colors text-muted-foreground hover:text-foreground"
                    >
                      <ChevronRight className="w-3.5 h-3.5" />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showModal && (
        <AddCompanyModal onClose={() => setShowModal(false)} onSaved={handleSaved} />
      )}
    </div>
  );
}
