import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight, Target } from "lucide-react";
import { buildPageMetadata } from "@/lib/metadata";
import { breadcrumbSchema, productSchema } from "@/lib/jsonld";

const BASE_URL = process.env.NEXT_PUBLIC_APP_URL || "https://uzimaamka.com";

export const metadata: Metadata = buildPageMetadata({
  title: "Pursuit Decision Quality™ — Bid/No-Bid Analysis with Institutional Rigor",
  description:
    "Eight-dimension bid/no-bid scoring with full evidence trail. Pursuit Decision Quality™ converts BD instinct into structured, auditable pursuit decisions.",
  path: "/pdq",
});

const PDQ_DIMENSIONS = [
  { label: "Strategic Alignment", desc: "Does this opportunity advance a defined strategic objective — agency relationship, contract vehicle, NAICS expansion, or teaming partner positioning?" },
  { label: "Win Probability", desc: "Composite probability estimate drawing from Diagnostics dimension scores, Radar tier, and historical win rates in comparable opportunity profiles." },
  { label: "Technical Readiness", desc: "Can you propose credibly? Assessment of capability alignment, staffing availability, and required subcontracting risk." },
  { label: "Past Performance Match", desc: "Strength of past performance relevance to this specific opportunity's scope, scale, and agency type." },
  { label: "Resource Availability", desc: "Actual capture and proposal capacity available, accounting for competing pursuits in the pipeline." },
  { label: "Price Competitiveness", desc: "Estimated price-to-win position and margin capacity. Whether you can bid to win and still perform profitably." },
  { label: "Risk Exposure", desc: "Contractual, performance, and competitive risks. Weighting of concentration, teaming, and clearance requirements." },
  { label: "Pipeline Value", desc: "Portfolio-level impact. Whether winning this changes your competitive position, references, or vehicle access beyond the immediate contract value." },
];

export default function PDQPage() {
  const crumbs = breadcrumbSchema([
    { name: "Home", url: BASE_URL },
    { name: "Pursuit Decision Quality™", url: `${BASE_URL}/pdq` },
  ]);
  const product = productSchema({
    name: "Pursuit Decision Quality™",
    description: "Bid/no-bid analysis with institutional rigor. Eight-dimension scoring across strategic alignment, win probability, and execution risk.",
    url: `${BASE_URL}/pdq`,
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
              <Target className="w-3.5 h-3.5" />
              Module 02 — Professional+
            </div>
            <h1 className="text-4xl sm:text-5xl font-bold tracking-tight leading-[1.06] mb-5">
              Pursuit Decision<br />Quality™
            </h1>
            <p className="text-xl text-muted-foreground font-medium mb-5">
              Bid/no-bid analysis with institutional rigor.
            </p>
            <p className="text-base text-muted-foreground leading-relaxed mb-10 max-w-2xl">
              The majority of proposal losses are determined before the proposal begins — by the decision
              to pursue. PDQ™ converts the BD team's instinct-based pursuit decision into an eight-dimension
              scored analysis with full evidence trail. Every PDQ review is auditable, reproducible, and
              comparable across pursuits and reviewers.
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

      {/* Eight dimensions */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-20 sm:py-24">
        <div className="max-w-2xl mb-14">
          <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground mb-5">Scoring Framework</p>
          <h2 className="text-3xl font-bold tracking-tight mb-5">Eight Pursuit Dimensions</h2>
          <p className="text-muted-foreground leading-relaxed">
            Each dimension is scored on a calibrated 1–10 scale. Dimension weights are configurable by organization.
            PDQ produces a gate recommendation — Pursue, Hold, or No-Bid — with the reasoning behind each
            sub-score surfaced for review and challenge.
          </p>
        </div>
        <div className="grid sm:grid-cols-2 gap-4">
          {PDQ_DIMENSIONS.map((d, i) => (
            <div key={d.label} className="border border-border rounded-lg p-5 bg-card flex gap-4">
              <span className="font-mono text-muted-foreground/40 text-lg font-bold shrink-0 w-7 leading-none pt-0.5">
                {String(i + 1).padStart(2, "0")}
              </span>
              <div>
                <div className="font-semibold text-sm mb-1.5">{d.label}</div>
                <div className="text-xs text-muted-foreground leading-relaxed">{d.desc}</div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Sample output */}
      <section className="border-t border-b border-border bg-card">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-16">
          <div className="grid lg:grid-cols-2 gap-12 items-start">
            <div>
              <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground mb-5">Gate Review Output</p>
              <h2 className="text-2xl font-bold tracking-tight mb-5">A structured gate, not an opinion</h2>
              <p className="text-muted-foreground leading-relaxed mb-5">
                PDQ produces a gate recommendation with the full evidence chain. BD leadership can review,
                override, and annotate — all of which are logged for pattern analysis across the portfolio.
              </p>
              <p className="text-muted-foreground leading-relaxed">
                Over time, PDQ builds a library of scored pursuit decisions against their actual outcomes.
                This creates an organization-specific win prediction model derived from your own data,
                not industry averages.
              </p>
            </div>
            <div className="border border-border rounded-xl p-6 bg-background font-mono text-sm">
              <div className="text-[10px] uppercase tracking-widest text-muted-foreground mb-5">Sample PDQ Gate Review</div>
              <div className="space-y-2.5 mb-5">
                {[
                  { label: "Strategic Alignment", score: 8.2 },
                  { label: "Win Probability", score: 6.1 },
                  { label: "Technical Readiness", score: 7.8 },
                  { label: "Past Performance", score: 5.4 },
                  { label: "Resource Availability", score: 6.9 },
                  { label: "Price Competitiveness", score: 7.2 },
                  { label: "Risk Exposure", score: 6.6 },
                  { label: "Pipeline Value", score: 8.5 },
                ].map((row) => (
                  <div key={row.label} className="flex items-center justify-between gap-3">
                    <span className="text-muted-foreground text-xs">{row.label}</span>
                    <div className="flex items-center gap-3">
                      <div className="w-24 h-1.5 bg-border rounded-full overflow-hidden">
                        <div
                          className="h-full bg-primary rounded-full"
                          style={{ width: `${row.score * 10}%` }}
                        />
                      </div>
                      <span className="text-xs w-6 text-right">{row.score}</span>
                    </div>
                  </div>
                ))}
              </div>
              <div className="border-t border-border pt-4 flex items-center justify-between">
                <span className="text-muted-foreground text-xs">Gate Recommendation</span>
                <span className="text-amber-400 font-bold text-sm">PURSUE — CONDITIONAL</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Availability */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-16">
        <div className="max-w-xl">
          <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground mb-4">Availability</p>
          <h2 className="text-2xl font-bold tracking-tight mb-3">Included in Professional+</h2>
          <p className="text-sm text-muted-foreground leading-relaxed mb-6">
            PDQ™ is available with Professional, Growth, and Enterprise subscriptions. It integrates with
            Diagnostics for automatic dimension pre-population, reducing gate review time to under 20 minutes.
          </p>
          <Link href="/pricing" className="inline-flex items-center gap-2 text-sm text-primary font-medium hover:text-primary/80 transition-colors">
            Compare plans <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </section>
    </>
  );
}
