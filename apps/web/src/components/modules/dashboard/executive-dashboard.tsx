"use client";

import { useQuery } from "@tanstack/react-query";
import { Award, BarChart3, Brain, FileText, Target, TrendingUp } from "lucide-react";
import { formatCurrency, formatProbability, getScoreColor } from "@/lib/utils";
import api from "@/lib/api";

export function ExecutiveDashboard() {
  const { data: opps } = useQuery({
    queryKey: ["opportunities"],
    queryFn: () => api.getOpportunities({ page_size: 5, sort_by: "award_probability_score", sort_dir: "desc" }),
  });

  const { data: sims } = useQuery({
    queryKey: ["simulations"],
    queryFn: () => api.getSimulations(),
  });

  const { data: subscription } = useQuery({
    queryKey: ["subscription"],
    queryFn: () => api.getSubscription(),
  });

  const opportunities = opps?.items || [];
  const simulations = sims?.items || [];
  const bidOpps = opportunities.filter((o: any) => o.bid_no_bid_recommendation === "BID");
  const avgProbability = opportunities.reduce((s: number, o: any) => s + (o.award_probability_score || 0), 0) / Math.max(opportunities.length, 1);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Executive Dashboard</h1>
        <p className="text-muted-foreground text-sm mt-1">Procurement intelligence at a glance</p>
      </div>

      {/* KPI Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KPICard
          label="Active Opportunities"
          value={String(opps?.total || 0)}
          icon={Target}
          description="In pipeline"
        />
        <KPICard
          label="Avg Award Probability"
          value={formatProbability(avgProbability / 100)}
          icon={TrendingUp}
          description="Across active opps"
          valueClass={getScoreColor(avgProbability)}
        />
        <KPICard
          label="AI Recommends BID"
          value={String(bidOpps.length)}
          icon={Brain}
          description="Of active opportunities"
        />
        <KPICard
          label="Award Simulations"
          value={String(sims?.items?.length || 0)}
          icon={Award}
          description="This cycle"
        />
      </div>

      {/* Top Opportunities */}
      <div className="grid md:grid-cols-2 gap-6">
        <div className="border border-border rounded-xl bg-card">
          <div className="px-6 py-4 border-b border-border flex items-center justify-between">
            <h2 className="font-semibold">Top Opportunities by Win Probability</h2>
            <a href="/dashboard/opportunities" className="text-xs text-primary hover:underline">View all</a>
          </div>
          <div className="divide-y divide-border">
            {opportunities.slice(0, 5).map((opp: any) => (
              <OpportunityRow key={opp.id} opp={opp} />
            ))}
            {opportunities.length === 0 && (
              <div className="px-6 py-8 text-center text-sm text-muted-foreground">
                No opportunities yet. <a href="/dashboard/opportunities" className="text-primary hover:underline">Add your first opportunity</a>
              </div>
            )}
          </div>
        </div>

        {/* Recent Simulations */}
        <div className="border border-border rounded-xl bg-card">
          <div className="px-6 py-4 border-b border-border flex items-center justify-between">
            <h2 className="font-semibold">Recent Award Simulations</h2>
            <a href="/dashboard/award-simulator" className="text-xs text-primary hover:underline">View all</a>
          </div>
          <div className="divide-y divide-border">
            {simulations.slice(0, 5).map((sim: any) => (
              <SimulationRow key={sim.id} sim={sim} />
            ))}
            {simulations.length === 0 && (
              <div className="px-6 py-8 text-center text-sm text-muted-foreground">
                No simulations yet. <a href="/dashboard/award-simulator" className="text-primary hover:underline">Run your first simulation</a>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Plan indicator */}
      {subscription && (
        <div className="border border-border rounded-xl bg-card px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <FileText className="w-5 h-5 text-primary" />
            <div>
              <div className="text-sm font-medium capitalize">{subscription.plan} Plan</div>
              <div className="text-xs text-muted-foreground">{subscription.status}</div>
            </div>
          </div>
          <a href="/dashboard/settings" className="text-xs text-primary hover:underline">Manage</a>
        </div>
      )}
    </div>
  );
}

function KPICard({ label, value, icon: Icon, description, valueClass }: {
  label: string; value: string; icon: any; description: string; valueClass?: string;
}) {
  return (
    <div className="border border-border rounded-xl bg-card p-5">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs text-muted-foreground font-medium">{label}</span>
        <Icon className="w-4 h-4 text-muted-foreground" />
      </div>
      <div className={`text-3xl font-bold ${valueClass || ""}`}>{value}</div>
      <div className="text-xs text-muted-foreground mt-1">{description}</div>
    </div>
  );
}

function OpportunityRow({ opp }: { opp: any }) {
  const prob = opp.award_probability_score;
  return (
    <div className="px-6 py-3 flex items-center justify-between hover:bg-secondary/50 transition-colors">
      <div className="min-w-0">
        <div className="text-sm font-medium truncate max-w-xs">{opp.title}</div>
        <div className="text-xs text-muted-foreground">{opp.agency} · {formatCurrency(opp.estimated_value_max)}</div>
      </div>
      <div className="ml-4 text-right shrink-0">
        <div className={`text-sm font-semibold ${getScoreColor(prob)}`}>
          {prob ? `${Math.round(prob)}%` : "—"}
        </div>
        <div className={`text-xs ${opp.bid_no_bid_recommendation === "BID" ? "text-emerald-500" : opp.bid_no_bid_recommendation === "NO-BID" ? "text-red-500" : "text-muted-foreground"}`}>
          {opp.bid_no_bid_recommendation || "Pending"}
        </div>
      </div>
    </div>
  );
}

function SimulationRow({ sim }: { sim: any }) {
  return (
    <div className="px-6 py-3 flex items-center justify-between hover:bg-secondary/50 transition-colors">
      <div className="min-w-0">
        <div className="text-sm font-medium truncate max-w-xs">{sim.name}</div>
        <div className="text-xs text-muted-foreground">{sim.evaluation_methodology}</div>
      </div>
      <div className="ml-4 text-right shrink-0">
        {sim.award_probability != null ? (
          <div className={`text-sm font-semibold ${getScoreColor((sim.award_probability || 0) * 100)}`}>
            {Math.round((sim.award_probability || 0) * 100)}%
          </div>
        ) : (
          <div className="text-xs text-muted-foreground capitalize">{sim.status}</div>
        )}
        <div className={`text-xs ${
          sim.gate_review_recommendation === "SUBMIT" ? "text-emerald-500" :
          sim.gate_review_recommendation === "WITHDRAW" ? "text-red-500" :
          "text-amber-500"
        }`}>
          {sim.gate_review_recommendation || "Processing"}
        </div>
      </div>
    </div>
  );
}
