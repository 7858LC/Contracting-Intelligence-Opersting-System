"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AxiosError } from "axios";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { ChevronDown, ChevronUp, Landmark, Lock, FileText } from "lucide-react";

interface ReportSummary {
  id: string;
  report_type: string;
  period_label: string;
  title: string;
  summary: string | null;
  published_at: string | null;
}

interface AgencyBrief {
  executive_summary: string;
  key_findings: string[];
  priority_sectors: { naics: string; rationale: string }[];
  capture_implications: string;
  data_limitations: string;
  confidence_explanation: string;
}

interface ReportDetail extends ReportSummary {
  content: { agency: string; brief: AgencyBrief }[];
}

export function ResearchView() {
  const [openReportId, setOpenReportId] = useState<string | null>(null);
  const [openAgency, setOpenAgency] = useState<string | null>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ["research-reports"],
    queryFn: () => api.getResearchReports() as Promise<{ items: ReportSummary[]; total: number }>,
  });

  const forbidden = (error as AxiosError)?.response?.status === 403;

  const { data: detail } = useQuery({
    queryKey: ["research-report", openReportId],
    queryFn: () => api.getResearchReport(openReportId as string) as Promise<ReportDetail>,
    enabled: !!openReportId,
  });

  if (forbidden) {
    return (
      <div className="text-center py-16 text-muted-foreground">
        <Lock className="w-12 h-12 mx-auto mb-3 opacity-20" />
        <p className="font-medium">Executive Council access required</p>
        <p className="text-sm mt-1">
          Ask your platform administrator to grant Executive Council access to your organization.
        </p>
      </div>
    );
  }

  const reports = data?.items ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Executive Council Research</h1>
        <p className="text-sm text-muted-foreground mt-0.5">
          Agency Intelligence Briefs — public procurement data, curated for Council members
        </p>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 2 }).map((_, i) => (
            <div key={i} className="h-20 bg-card border border-border rounded-lg animate-pulse" />
          ))}
        </div>
      ) : reports.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground">
          <FileText className="w-12 h-12 mx-auto mb-3 opacity-20" />
          <p className="font-medium">No reports published yet</p>
          <p className="text-sm mt-1">Agency Intelligence Briefs are generated quarterly.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {reports.map((report) => {
            const isOpen = openReportId === report.id;
            return (
              <div key={report.id} className="border border-border rounded-lg overflow-hidden bg-card">
                <button
                  onClick={() => { setOpenReportId(isOpen ? null : report.id); setOpenAgency(null); }}
                  className="w-full text-left px-4 py-3 flex items-center gap-3"
                >
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium">{report.title}</p>
                    <div className="flex items-center gap-3 mt-0.5 text-xs text-muted-foreground">
                      <span>{report.period_label}</span>
                      {report.published_at && (
                        <span>Published {new Date(report.published_at).toLocaleDateString()}</span>
                      )}
                    </div>
                  </div>
                  {isOpen ? (
                    <ChevronUp className="w-4 h-4 text-muted-foreground shrink-0" />
                  ) : (
                    <ChevronDown className="w-4 h-4 text-muted-foreground shrink-0" />
                  )}
                </button>

                {isOpen && (
                  <div className="px-4 pb-4 border-t border-border/50 pt-4 space-y-2">
                    {!detail ? (
                      <div className="h-16 bg-background/50 rounded-md animate-pulse" />
                    ) : (
                      detail.content.map((section) => {
                        const sectionOpen = openAgency === section.agency;
                        return (
                          <div key={section.agency} className="border border-border/60 rounded-md overflow-hidden">
                            <button
                              onClick={() => setOpenAgency(sectionOpen ? null : section.agency)}
                              className="w-full text-left px-3 py-2.5 flex items-center gap-2 bg-background/30"
                            >
                              <Landmark className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
                              <span className="text-sm font-medium flex-1">{section.agency}</span>
                              {sectionOpen ? (
                                <ChevronUp className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
                              ) : (
                                <ChevronDown className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
                              )}
                            </button>

                            {sectionOpen && (
                              <div className="px-3 pb-3 pt-1 space-y-3">
                                <div>
                                  <p className="text-xs text-muted-foreground mb-1">Executive Summary</p>
                                  <p className="text-sm">{section.brief.executive_summary}</p>
                                </div>

                                {section.brief.key_findings?.length > 0 && (
                                  <div>
                                    <p className="text-xs text-muted-foreground mb-1">Key Findings</p>
                                    <ul className="space-y-1">
                                      {section.brief.key_findings.map((f, i) => (
                                        <li key={i} className="text-sm flex items-start gap-1.5">
                                          <span className="text-primary shrink-0">•</span>
                                          {f}
                                        </li>
                                      ))}
                                    </ul>
                                  </div>
                                )}

                                {section.brief.priority_sectors?.length > 0 && (
                                  <div>
                                    <p className="text-xs text-muted-foreground mb-1">Priority Sectors</p>
                                    <div className="space-y-1.5">
                                      {section.brief.priority_sectors.map((s, i) => (
                                        <div key={i} className="text-sm">
                                          <span className={cn(
                                            "text-xs px-1.5 py-0.5 rounded font-mono mr-1.5",
                                            "bg-secondary text-muted-foreground"
                                          )}>
                                            {s.naics}
                                          </span>
                                          {s.rationale}
                                        </div>
                                      ))}
                                    </div>
                                  </div>
                                )}

                                <div>
                                  <p className="text-xs text-muted-foreground mb-1">Capture Implications</p>
                                  <p className="text-sm">{section.brief.capture_implications}</p>
                                </div>

                                <div className="bg-background/50 rounded-md p-3">
                                  <p className="text-xs font-medium text-muted-foreground mb-1">Data Limitations</p>
                                  <p className="text-xs text-muted-foreground">{section.brief.data_limitations}</p>
                                  <p className="text-xs font-medium text-muted-foreground mb-1 mt-2">Confidence</p>
                                  <p className="text-xs text-muted-foreground">{section.brief.confidence_explanation}</p>
                                </div>
                              </div>
                            )}
                          </div>
                        );
                      })
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
