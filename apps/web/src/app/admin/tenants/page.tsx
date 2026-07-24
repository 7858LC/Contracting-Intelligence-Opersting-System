"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Search, ChevronLeft, ChevronRight } from "lucide-react";
import { adminApi } from "@/lib/admin-api";
import { canOperate } from "@/lib/admin-auth";

interface TenantRow {
  id: string;
  name: string;
  slug: string;
  plan: string;
  is_active: boolean;
  member_count: number;
  created_at: string | null;
}

const PAGE_SIZE = 20;

export default function AdminTenantsPage() {
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const queryClient = useQueryClient();
  const operator = canOperate();

  const { data, isLoading } = useQuery({
    queryKey: ["admin-tenants", q, page],
    queryFn: () => adminApi.listTenants({ q: q || undefined, page, page_size: PAGE_SIZE }),
  });

  const suspend = useMutation({
    mutationFn: (id: string) => adminApi.suspendTenant(id),
    onSuccess: () => {
      toast.success("Tenant suspended");
      queryClient.invalidateQueries({ queryKey: ["admin-tenants"] });
    },
    onError: () => toast.error("Failed to suspend tenant"),
  });

  const activate = useMutation({
    mutationFn: (id: string) => adminApi.activateTenant(id),
    onSuccess: () => {
      toast.success("Tenant activated");
      queryClient.invalidateQueries({ queryKey: ["admin-tenants"] });
    },
    onError: () => toast.error("Failed to activate tenant"),
  });

  const tenants: TenantRow[] = data?.items ?? [];
  const total: number = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Tenants</h1>
        <p className="text-sm text-muted-foreground mt-0.5">{total} tenant{total === 1 ? "" : "s"} on the platform</p>
      </div>

      <div className="relative max-w-sm">
        <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
        <input
          value={q}
          onChange={(e) => { setQ(e.target.value); setPage(1); }}
          placeholder="Search by name or slug…"
          className="w-full pl-9 pr-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
        />
      </div>

      <div className="bg-card border border-border rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-secondary/50 text-muted-foreground text-xs uppercase tracking-wide">
            <tr>
              <th className="text-left px-5 py-3 font-medium">Tenant</th>
              <th className="text-left px-5 py-3 font-medium">Plan</th>
              <th className="text-left px-5 py-3 font-medium">Members</th>
              <th className="text-left px-5 py-3 font-medium">Status</th>
              <th className="text-right px-5 py-3 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {isLoading && (
              <tr><td colSpan={5} className="px-5 py-6 text-center text-muted-foreground">Loading…</td></tr>
            )}
            {!isLoading && tenants.length === 0 && (
              <tr><td colSpan={5} className="px-5 py-6 text-center text-muted-foreground">No tenants found.</td></tr>
            )}
            {tenants.map((t) => (
              <tr key={t.id} className="hover:bg-secondary/30 transition-colors">
                <td className="px-5 py-3">
                  <Link href={`/admin/tenants/${t.id}`} className="font-medium hover:underline">{t.name}</Link>
                  <div className="text-xs text-muted-foreground">{t.slug}</div>
                </td>
                <td className="px-5 py-3">
                  <span className="px-2 py-0.5 rounded-full bg-secondary text-secondary-foreground text-xs uppercase tracking-wide">
                    {t.plan}
                  </span>
                </td>
                <td className="px-5 py-3">{t.member_count}</td>
                <td className="px-5 py-3">
                  <span
                    className={
                      t.is_active
                        ? "px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-500 text-xs"
                        : "px-2 py-0.5 rounded-full bg-red-500/15 text-red-500 text-xs"
                    }
                  >
                    {t.is_active ? "active" : "suspended"}
                  </span>
                </td>
                <td className="px-5 py-3 text-right">
                  {operator ? (
                    t.is_active ? (
                      <button
                        onClick={() => suspend.mutate(t.id)}
                        disabled={suspend.isPending}
                        className="text-xs text-red-500 hover:underline disabled:opacity-50"
                      >
                        Suspend
                      </button>
                    ) : (
                      <button
                        onClick={() => activate.mutate(t.id)}
                        disabled={activate.isPending}
                        className="text-xs text-emerald-500 hover:underline disabled:opacity-50"
                      >
                        Activate
                      </button>
                    )
                  ) : (
                    <span className="text-xs text-muted-foreground">read only</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-3 text-sm">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            className="p-1.5 rounded-md border border-border disabled:opacity-40 hover:bg-secondary transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <span className="text-muted-foreground">Page {page} of {totalPages}</span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
            className="p-1.5 rounded-md border border-border disabled:opacity-40 hover:bg-secondary transition-colors"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  );
}
