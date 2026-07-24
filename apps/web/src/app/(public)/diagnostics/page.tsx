import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight, BarChart3 } from "lucide-react";
import { buildPageMetadata } from "@/lib/metadata";
import { breadcrumbSchema, productSchema } from "@/lib/jsonld";

const BASE_URL = process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000";

export const metadata: Metadata = buildPageMetadata({
  title: "Procurement Intelligence Diagnostics™ — Competitive Position Assessment",
  description:
    "Systematic assessment of competitive position across eight strategic dimensions. Identify structural weaknesses before they surface in source selection scoring.",
  path: "/diagnostics",
});

const DIMENSIONS = [
  { id: "D1", label: "Past Performance Proximity", desc: "Relevance scoring of past performance against the target opportunity's NAICS code, scope, and agency type." },
  { id: "D2", label: "Technical Capability Alignment", desc: "Gap analysis between stated requirements and demonstrated capabilities from past contracts and personnel." },
  { id: "D3", label: "Incumbent Risk", desc: "Assessment of incumbent strength, relationship tenure, and re-compete risk. Quantifies the friction required to displace a seated contractor." },
  { id: "D4", label: "Relationship Depth", desc: "Scoring of documented agency relationships relative to known competitors. COR/CO access, program office familiarity, and referral chains." },
  { id: "D5", label: "Pricing Position", desc: "Competitive price banding based on similar awards in the target NAICS/agency. Identifies where you are likely to land on a price-to-win basis." },
  { id: "D6", label: "Team Strength", desc: "Assessment of proposed team against known competitor teaming patterns. Identifies partner gaps and redundancies." },
  { id: "D7", label: "Differentiation Clarity", desc: "Whether your discriminators are genuine, defensible, and relevant to the evaluation criteria — or generic and easily matched." },
  { id: "D8", label: "Pipeline Concentration", desc: "Whether over-pursuit of a single opportunity creates resource and risk concentration in the broader capture portfolio." },
];

export default function DiagnosticsPage() {
  const crumbs = breadcrumbSchema([
    { name: "Home", url: BASE_URL },
    { name: "Procurement Intelligence Diagnostics™", url: `${BASE_URL}/diagnostics` },
  ]);
  const product = productSchema({
    name: "Procurement Intelligence Diagnostics™",
    description: "Systematic competitive position assessment across eight strategic dimensions.",
    url: `${BASE_URL}/diagnostics`,
  });

  return (
    <>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(crumbs) }} />
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(product) }} />

      {/* Hero */}
      <section className="border-b border-border py-20 sm:py-28">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2 text-[11px] font-mono uppercase tracking-[0.18em] text-primary mb-6">
              <BarChart3 className="w-3.5 h-3.5" />
              Module 01 — Professional+
            </div>
            <h1 className="text-4xl sm:text-5xl font-bold tracking-tight leading-[1.06] mb-5">
              Procurement Intelligence<br />Diagnostics™
            </h1>
            <p className="text-xl text-muted-foreground font-medium mb-5">
              Identify your competitive weaknesses before the evaluator does.
            </p>
            <p className="text-base text-muted-foreground leading-relaxed mb-10 max-w-2xl">
              Diagnostics performs a systematic assessment of your competitive position across eight
              strategic dimensions. It surfaces structural weaknesses — capability gaps, relationship
              deficits, past performance misalignment — that are predictably exploited by incumbents
              and competitors in source selection scoring.
            </p>
            <div className="flex flex-wrap gap-4">
              <Link href="/auth/register" className="inline-flex items-center gap-2 bg-primary text-primary-foreground px-6 py-3 rounded-md font-semibold hover:bg-primary/90 transition-colors text-sm">
                Request Access <ArrowRight className="w-4 h-4" />
              </Link>
              <Link href="/pricing" className="inline-flex items-center gap-2 border border-border px-6 py-3 rounded-md font-semibold text-muted-foreground hover:text-foreground transition-colors text-sm">
                View Pricing
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Dimensions */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-20 sm:py-24">
        <div className="max-w-2xl mb-14">
          <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground mb-5">Assessment Framework</p>
          <h2 className="text-3xl font-bold tracking-tight mb-5">Eight Diagnostic Dimensions</h2>
          <p className="text-muted-foreground leading-relaxed">
            Each dimension is scored against a calibrated rubric derived from federal source selection patterns.
            Scores aggregate into an overall competitive position rating with dimension-level improvement priorities.
          </p>
        </div>
        <div className="grid sm:grid-cols-2 gap-4">
          {DIMENSIONS.map((d) => (
            <div key={d.id} className="border border-border rounded-lg p-5 bg-card flex gap-4">
              <span className="font-mono text-[10px] text-muted-foreground shrink-0 pt-0.5 w-8">{d.id}</span>
              <div>
                <div className="font-semibold text-sm mb-1.5">{d.label}</div>
                <div className="text-xs text-muted-foreground leading-relaxed">{d.desc}</div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Availability */}
      <section className="border-t border-border bg-card">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-16">
          <div className="max-w-xl">
            <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground mb-4">Availability</p>
            <h2 className="text-2xl font-bold tracking-tight mb-3">Included in Professional+</h2>
            <p className="text-sm text-muted-foreground leading-relaxed mb-6">
              Procurement Intelligence Diagnostics™ is available with Professional, Growth, and Enterprise subscriptions.
              Diagnostics requires Radar as its market intelligence input layer.
            </p>
            <Link href="/pricing" className="inline-flex items-center gap-2 text-sm text-primary font-medium hover:text-primary/80 transition-colors">
              Compare plans <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
