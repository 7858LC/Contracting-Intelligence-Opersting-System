"use client";

import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ArrowLeft, Target, FileText, Users, Clock } from "lucide-react";
import { adminApi } from "@/lib/admin-api";
import { canOperate } from "@/lib/admin-auth";

interface TenantDetail {
  tenant: {
    id: string;
    name: string;
    slug: string;
    plan: string;
    is_active: boolean;
    created_at: string;
  };
  usage: {
    member_count: number;
    opportunity_count: number;
    solicitation_count: number;
    last_activity_at: string | null;
  };
  subscription: { plan: string; status: string; current_period_end: string | null } | null;
  members: {
    id: string;
    email: string;
    full_name: string | null;
    role: string;
    is_active: boolean;
    last_seen_at: string | null;
  }[];
}

interface AuditEntry {
  id: string;
  action: string;
  resource_type: string;
  resource_id: string | null;
  extra_metadata: Record<string, unknown> | null;
  created_at: string | null;
}

export default function TenantDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const operator = canOperate();

  const { data, isLoading } = useQuery({
    queryKey: ["admin-tenant", id],
    queryFn: () => adminApi.getTenant(id) as Promise<TenantDetail>,
  });

  const { data: auditData } = useQuery({
    queryKey: ["admin-tenant-audit", id],
    queryFn: () => adminApi.getTenantAuditLog(id, { page: 1, page_size: 20 }),
  });

  const suspend = useMutation({
    mutationFn: () => adminApi.suspendTenant(id),
    onSuccess: () => {
      toast.success("Tenant suspended");
      queryClient.invalidateQueries({ queryKey: ["admin-tenant", id] });
      queryClient.invalidateQueries({ queryKey: ["admin-tenant-audit", id] });
    },
    onError: () => toast.error("Failed to suspend tenant"),
  });

  const activate = useMutation({
    mutationFn: () => adminApi.activateTenant(id),
    onSuccess: () => {
      toast.success("Tenant activated");
      queryClient.invalidateQueries({ queryKey: ["admin-tenant", id] });
      queryClient.invalidateQueries({ queryKey: ["admin-tenant-audit", id] });
    },
    onError: () => toast.error("Failed to activate tenant"),
  });

  if (isLoading || !data) {
    return <div className="text-sm text-muted-foreground">Loading…</div>;
  }

  const auditEntries: AuditEntry[] = auditData?.items ?? [];

  return (
    <div className="space-y-6">
      <button
        onClick={() => router.push("/admin/tenants")}
        className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        <ArrowLeft className="w-4 h-4" /> Back to tenants
      </button>

      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold">{data.tenant.name}</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            {data.tenant.slug} · {data.tenant.plan} plan
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span
            className={
              data.tenant.is_active
                ? "px-2.5 py-1 rounded-full bg-emerald-500/15 text-emerald-500 text-xs"
                : "px-2.5 py-1 rounded-full bg-red-500/15 text-red-500 text-xs"
            }
          >
            {data.tenant.is_active ? "active" : "suspended"}
          </span>
          {operator &&
            (data.tenant.is_active ? (
              <button
                onClick={() => suspend.mutate()}
                disabled={suspend.isPending}
                className="px-3 py-1.5 text-sm rounded-md border border-red-500/30 text-red-500 hover:bg-red-500/10 transition-colors disabled:opacity-50"
              >
                Suspend
              </button>
            ) : (
              <button
                onClick={() => activate.mutate()}
                disabled={activate.isPending}
                className="px-3 py-1.5 text-sm rounded-md border border-emerald-500/30 text-emerald-500 hover:bg-emerald-500/10 transition-colors disabled:opacity-50"
              >
                Activate
              </button>
            ))}
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <MetricCard icon={Users} label="Members" value={String(data.usage.member_count)} />
        <MetricCard icon={Target} label="Opportunities" value={String(data.usage.opportunity_count)} />
        <MetricCard icon={FileText} label="Solicitations" value={String(data.usage.solicitation_count)} />
        <MetricCard
          icon={Clock}
          label="Last activity"
          value={data.usage.last_activity_at ? new Date(data.usage.last_activity_at).toLocaleDateString() : "—"}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-card border border-border rounded-lg">
          <div className="px-5 py-4 border-b border-border">
            <h3 className="font-semibold text-sm">Members</h3>
          </div>
          <div className="divide-y divide-border">
            {data.members.length === 0 && (
              <div className="px-5 py-4 text-sm text-muted-foreground">No members.</div>
            )}
            {data.members.map((m) => (
              <div key={m.id} className="flex items-center justify-between px-5 py-3">
                <div>
                  <div className="text-sm font-medium">{m.full_name || m.email}</div>
                  <div className="text-xs text-muted-foreground">{m.email}</div>
                </div>
                <span className="text-xs text-muted-foreground uppercase tracking-wide">{m.role}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-card border border-border rounded-lg">
          <div className="px-5 py-4 border-b border-border">
            <h3 className="font-semibold text-sm">Audit trail</h3>
          </div>
          <div className="divide-y divide-border max-h-[420px] overflow-y-auto">
            {auditEntries.length === 0 && (
              <div className="px-5 py-4 text-sm text-muted-foreground">No recorded activity yet.</div>
            )}
            {auditEntries.map((entry) => (
              <div key={entry.id} className="px-5 py-3">
                <div className="text-sm font-medium">{entry.action}</div>
                <div className="text-xs text-muted-foreground">
                  {entry.created_at ? new Date(entry.created_at).toLocaleString() : ""}
                  {typeof entry.extra_metadata?.platform_admin_email === "string" &&
                    ` · by ${entry.extra_metadata.platform_admin_email}`}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function MetricCard({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
}) {
  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <div className="flex items-center gap-2 text-muted-foreground text-xs uppercase tracking-wide mb-2">
        <Icon className="w-3.5 h-3.5" />
        {label}
      </div>
      <div className="text-xl font-bold">{value}</div>
    </div>
  );
}
