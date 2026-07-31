"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Trash2 } from "lucide-react";
import { adminApi } from "@/lib/admin-api";
import { canOperate } from "@/lib/admin-auth";

interface ResearchReportRow {
  id: string;
  report_type: string;
  period_label: string;
  status: string;
  visibility: string;
  title: string;
  summary: string | null;
  published_at: string | null;
  created_at: string | null;
}

export default function AdminResearchPage() {
  const queryClient = useQueryClient();
  const operator = canOperate();

  const { data, isLoading } = useQuery({
    queryKey: ["admin-research-reports"],
    queryFn: () => adminApi.listResearchReports(),
  });

  const deleteReport = useMutation({
    mutationFn: (id: string) => adminApi.deleteResearchReport(id),
    onSuccess: () => {
      toast.success("Research report deleted");
      queryClient.invalidateQueries({ queryKey: ["admin-research-reports"] });
    },
    onError: () => toast.error("Failed to delete research report"),
  });

  const reports: ResearchReportRow[] = data?.items ?? [];
  const total: number = data?.total ?? 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Research Reports</h1>
        <p className="text-sm text-muted-foreground mt-0.5">
          {total} report{total === 1 ? "" : "s"} — Executive Council content, shared across every
          Council-member tenant. Deleting removes it from every tenant&rsquo;s view.
        </p>
      </div>

      <div className="bg-card border border-border rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-secondary/50 text-muted-foreground text-xs uppercase tracking-wide">
            <tr>
              <th className="text-left px-5 py-3 font-medium">Report</th>
              <th className="text-left px-5 py-3 font-medium">Period</th>
              <th className="text-left px-5 py-3 font-medium">Status</th>
              <th className="text-left px-5 py-3 font-medium">Published</th>
              <th className="text-right px-5 py-3 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {isLoading && (
              <tr><td colSpan={5} className="px-5 py-6 text-center text-muted-foreground">Loading…</td></tr>
            )}
            {!isLoading && reports.length === 0 && (
              <tr><td colSpan={5} className="px-5 py-6 text-center text-muted-foreground">No research reports found.</td></tr>
            )}
            {reports.map((r) => (
              <tr key={r.id} className="hover:bg-secondary/30 transition-colors">
                <td className="px-5 py-3">
                  <div className="font-medium">{r.title}</div>
                  {r.summary && (
                    <div className="text-xs text-muted-foreground mt-0.5 line-clamp-1">{r.summary}</div>
                  )}
                </td>
                <td className="px-5 py-3">{r.period_label}</td>
                <td className="px-5 py-3">
                  <span
                    className={
                      r.status === "published"
                        ? "px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-500 text-xs"
                        : "px-2 py-0.5 rounded-full bg-secondary text-secondary-foreground text-xs"
                    }
                  >
                    {r.status}
                  </span>
                </td>
                <td className="px-5 py-3 text-muted-foreground">
                  {r.published_at ? new Date(r.published_at).toLocaleDateString() : "—"}
                </td>
                <td className="px-5 py-3 text-right">
                  {operator ? (
                    <button
                      onClick={() => {
                        if (confirm(`Delete "${r.title}"? This removes it from every Council-member tenant's view.`)) {
                          deleteReport.mutate(r.id);
                        }
                      }}
                      disabled={deleteReport.isPending && deleteReport.variables === r.id}
                      className="inline-flex items-center gap-1.5 text-xs text-red-500 hover:underline disabled:opacity-50"
                      title="Delete this report"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                      Delete
                    </button>
                  ) : (
                    <span className="text-xs text-muted-foreground">read only</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
