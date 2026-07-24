"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Building2, CreditCard, Users, ArrowRight } from "lucide-react";
import { adminApi } from "@/lib/admin-api";

interface PlatformStats {
  tenants: number;
  active_tenants: number;
  active_subscriptions: number;
  total_members: number;
  platform_version: string;
}

interface TenantRow {
  id: string;
  name: string;
  slug: string;
  plan: string;
  is_active: boolean;
  member_count: number;
  created_at: string | null;
}

export default function AdminOverviewPage() {
  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ["admin-stats"],
    queryFn: () => adminApi.getStats() as Promise<PlatformStats>,
  });

  const { data: tenantsPage, isLoading: tenantsLoading } = useQuery({
    queryKey: ["admin-tenants", "recent"],
    queryFn: () => adminApi.listTenants({ page: 1, page_size: 5 }),
  });

  const recentTenants: TenantRow[] = tenantsPage?.items ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Platform Overview</h1>
        <p className="text-sm text-muted-foreground mt-0.5">
          Cross-tenant visibility for platform operators. Every action here is audit-logged.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatCard
          icon={Building2}
          label="Tenants"
          value={statsLoading ? "…" : `${stats?.active_tenants ?? 0} / ${stats?.tenants ?? 0}`}
          sublabel="active / total"
        />
        <StatCard
          icon={CreditCard}
          label="Active Subscriptions"
          value={statsLoading ? "…" : String(stats?.active_subscriptions ?? 0)}
          sublabel={`v${stats?.platform_version ?? "—"}`}
        />
        <StatCard
          icon={Users}
          label="Total Members"
          value={statsLoading ? "…" : String(stats?.total_members ?? 0)}
          sublabel="across all tenants"
        />
      </div>

      <div className="bg-card border border-border rounded-lg">
        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
          <h3 className="font-semibold text-sm">Recently onboarded tenants</h3>
          <Link
            href="/admin/tenants"
            className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1 transition-colors"
          >
            View all <ArrowRight className="w-3 h-3" />
          </Link>
        </div>
        <div className="divide-y divide-border">
          {tenantsLoading && <div className="px-5 py-4 text-sm text-muted-foreground">Loading…</div>}
          {!tenantsLoading && recentTenants.length === 0 && (
            <div className="px-5 py-4 text-sm text-muted-foreground">No tenants yet.</div>
          )}
          {recentTenants.map((t) => (
            <Link
              key={t.id}
              href={`/admin/tenants/${t.id}`}
              className="flex items-center justify-between px-5 py-3 hover:bg-secondary/50 transition-colors"
            >
              <div>
                <div className="text-sm font-medium">{t.name}</div>
                <div className="text-xs text-muted-foreground">{t.slug}</div>
              </div>
              <div className="flex items-center gap-3 text-xs">
                <span className="text-muted-foreground">{t.member_count} member{t.member_count === 1 ? "" : "s"}</span>
                <span className="px-2 py-0.5 rounded-full bg-secondary text-secondary-foreground uppercase tracking-wide">
                  {t.plan}
                </span>
                <span
                  className={
                    t.is_active
                      ? "px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-500"
                      : "px-2 py-0.5 rounded-full bg-red-500/15 text-red-500"
                  }
                >
                  {t.is_active ? "active" : "suspended"}
                </span>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
  sublabel,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
  sublabel: string;
}) {
  return (
    <div className="bg-card border border-border rounded-lg p-5">
      <div className="flex items-center gap-2 text-muted-foreground text-xs uppercase tracking-wide mb-3">
        <Icon className="w-3.5 h-3.5" />
        {label}
      </div>
      <div className="text-2xl font-bold">{value}</div>
      <div className="text-xs text-muted-foreground mt-1">{sublabel}</div>
    </div>
  );
}
