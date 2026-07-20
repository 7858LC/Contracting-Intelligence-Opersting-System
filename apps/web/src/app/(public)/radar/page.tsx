import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight, Radio } from "lucide-react";
import { buildPageMetadata } from "@/lib/metadata";
import { breadcrumbSchema, productSchema } from "@/lib/jsonld";

const BASE_URL = process.env.NEXT_PUBLIC_APP_URL || "https://uzimaamka.com";

export const metadata: Metadata = buildPageMetadata({
  title: "Procurement Intelligence Radar™ — Market Surveillance Before the Solicitation",
  description:
    "Detect procurement signals before solicitations publish. Procurement Intelligence Radar™ monitors 47 federal data sources and scores companies by capture priority.",
  path: "/radar",
});

const SIGNAL_CATEGORIES = [
  {
    category: "Hiring Signals",
    color: "text-purple-400",
    bg: "bg-purple-400/10",
    signals: [
      "Capture Manager / BD Director hiring",
      "Program Manager with agency experience",
      "Technical lead with clearance",
      "Proposal Manager posting",
    ],
  },
  {
    category: "Contract Signals",
    color: "text-emerald-400",
    bg: "bg-emerald-400/10",
    signals: [
      "IDIQ vehicle award",
      "GWAC on-ramp placement",
      "Federal prime contract award",
      "Subcontract in target agency",
    ],
  },
  {
    category: "Growth Signals",
    color: "text-amber-400",
    bg: "bg-amber-400/10",
    signals: [
      "Revenue growth >15% YoY",
      "Office opening in agency hub",
      "Strategic partnership announcement",
      "Merger or acquisition activity",
    ],
  },
  {
    category: "Certification Signals",
    color: "text-teal-400",
    bg: "bg-teal-400/10",
    signals: [
      "SAM.gov registration or renewal",
      "ISO / CMMC certification",
      "8(a), WOSB, HUBZone qualification",
      "Agency-specific clearance",
    ],
  },
];

const TIERS = [
  {
    tier: "A",
    label: "Priority Target",
    score: "Score ≥ 60",
    desc: "Immediate capture action warranted. High signal density, strong readiness indicators, and recent growth momentum. Engage within 30 days.",
    border: "border-emerald-500/40",
    bg: "bg-emerald-500/5",
    badge: "bg-emerald-500/15 text-emerald-400",
  },
  {
    tier: "B",
    label: "Active Monitor",
    score: "Score 30 – 59",
    desc: "Consistent signals without immediate urgency. Track for progression. Re-evaluate quarterly or when new signals appear.",
    border: "border-amber-500/40",
    bg: "bg-amber-500/5",
    badge: "bg-amber-500/15 text-amber-400",
  },
  {
    tier: "C",
    label: "Horizon Watch",
    score: "Score < 30",
    desc: "Emerging or sparse signals. Low immediate priority. System monitors automatically; escalates on threshold breach.",
    border: "border-border",
    bg: "bg-card",
    badge: "bg-secondary text-muted-foreground",
  },
];

const SCORES = [
  { label: "Overall Score", desc: "Composite tanh-weighted score capped at 100. Reflects total signal weight with recency decay applied.", example: "74.3" },
  { label: "Confidence Score", desc: "Signal volume, source diversity, recency, and verification rate. High confidence = broad corroboration.", example: "0.81" },
  { label: "Growth Momentum", desc: "Recency-weighted signal acceleration across 30/60/90-day windows.", example: "+22%" },
  { label: "Government Readiness", desc: "Certification and award indicators weighted by decay. Measures proximity to contract execution readiness.", example: "High" },
];

export default function RadarPage() {
  const crumbs = breadcrumbSchema([
    { name: "Home", url: BASE_URL },
    { name: "Procurement Intelligence Radar™", url: `${BASE_URL}/radar` },
  ]);
  const product = productSchema({
    name: "Procurement Intelligence Radar™",
    description: "Market surveillance and company intelligence for public sector contractors. Detect procurement signals before solicitations publish.",
    url: `${BASE_URL}/radar`,
  });

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(crumbs) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(product) }}
      />

      {/* Hero */}
      <section className="border-b border-border py-20 sm:py-28">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2 text-[11px] font-mono uppercase tracking-[0.18em] text-primary mb-6">
              <Radio className="w-3.5 h-3.5" />
              Module 00 — Independently Licensable
            </div>
            <h1 className="text-4xl sm:text-5xl md:text-6xl font-bold tracking-tight leading-[1.04] mb-5">
              Procurement Intelligence<br />Radar™
            </h1>
            <p className="text-xl sm:text-2xl text-muted-foreground font-medium mb-5">
              Know who is building before the solicitation drops.
            </p>
            <p className="text-base text-muted-foreground mb-10 max-w-2xl leading-relaxed">
              Radar continuously monitors 47 federal data sources for procurement signals — hiring patterns,
              contract activity, certifications, and growth indicators — then scores each company against a
              priority tier using exponential decay weighting. The result: a prioritized target list that
              captures competitive intelligence your BD team would otherwise spend weeks assembling manually.
            </p>
            <div className="flex flex-wrap gap-4">
              <Link
                href="/auth/register"
                className="inline-flex items-center gap-2 bg-primary text-primary-foreground px-6 py-3 rounded-md font-semibold hover:bg-primary/90 transition-colors text-sm"
              >
                License Radar <ArrowRight className="w-4 h-4" />
              </Link>
              <Link
                href="/pricing"
                className="inline-flex items-center gap-2 border border-border px-6 py-3 rounded-md font-semibold text-muted-foreground hover:text-foreground transition-colors text-sm"
              >
                Compare Plans
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="bg-card border-b border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-16">
          <div className="grid sm:grid-cols-3 gap-8">
            {[
              { step: "01", label: "Scan", desc: "Automated ingestion from SAM.gov, USASpending.gov, job boards, and agency procurement feeds. New signals detected within 72 hours of publication." },
              { step: "02", label: "Score", desc: "Each signal is weighted by type and decayed by age using a domain-specific half-life (hiring: 45d, contracts: 180d, certifications: 365d). Scores are recomputed nightly." },
              { step: "03", label: "Prioritize", desc: "Companies assigned to Tier A, B, or C based on composite score. AI analysis generates intelligence brief with recommended outreach, buying probability, and stakeholder mapping." },
            ].map((s) => (
              <div key={s.step} className="border border-border rounded-lg p-6 bg-background">
                <div className="font-mono text-3xl font-bold text-primary/30 mb-4">{s.step}</div>
                <div className="font-semibold mb-2">{s.label}</div>
                <div className="text-sm text-muted-foreground leading-relaxed">{s.desc}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Signal types */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-20 sm:py-24">
        <div className="max-w-2xl mb-14">
          <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground mb-5">
            Signal Detection
          </p>
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight mb-5">
            Four Signal Categories
          </h2>
          <p className="text-muted-foreground leading-relaxed">
            Radar monitors 31 distinct signal types across four categories. Each signal type carries
            an individually calibrated weight reflecting its predictive value for contract award probability.
          </p>
        </div>
        <div className="grid sm:grid-cols-2 gap-4">
          {SIGNAL_CATEGORIES.map((cat) => (
            <div key={cat.category} className="border border-border rounded-lg p-6 bg-card">
              <div className={`inline-flex text-xs font-semibold px-2.5 py-1 rounded-md mb-4 ${cat.bg} ${cat.color}`}>
                {cat.category}
              </div>
              <ul className="space-y-2">
                {cat.signals.map((s) => (
                  <li key={s} className="flex items-start gap-3 text-sm">
                    <div className={`w-1 h-1 rounded-full mt-2 shrink-0 ${cat.color.replace("text-", "bg-")}`} />
                    <span className="text-muted-foreground">{s}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </section>

      {/* Tier system */}
      <section className="border-t border-b border-border bg-card">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-20 sm:py-24">
          <div className="max-w-2xl mb-14">
            <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground mb-5">
              Priority Tier System
            </p>
            <h2 className="text-3xl sm:text-4xl font-bold tracking-tight mb-5">
              Three-Tier Classification
            </h2>
            <p className="text-muted-foreground leading-relaxed">
              Every company tracked by Radar is classified into one of three priority tiers based on
              composite score. Tiers drive capture queue prioritization and resource allocation recommendations.
            </p>
          </div>
          <div className="grid sm:grid-cols-3 gap-4">
            {TIERS.map((t) => (
              <div key={t.tier} className={`border rounded-lg p-6 ${t.border} ${t.bg}`}>
                <div className="flex items-center justify-between mb-4">
                  <span className={`inline-flex items-center justify-center w-8 h-8 rounded-md text-sm font-bold ${t.badge}`}>
                    {t.tier}
                  </span>
                  <span className="font-mono text-[10px] text-muted-foreground uppercase tracking-wider">
                    {t.score}
                  </span>
                </div>
                <div className="font-semibold text-sm mb-2">{t.label}</div>
                <div className="text-xs text-muted-foreground leading-relaxed">{t.desc}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Scoring methodology */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-20 sm:py-24">
        <div className="max-w-2xl mb-14">
          <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground mb-5">
            Scoring Methodology
          </p>
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight mb-5">
            Four Composite Scores
          </h2>
          <p className="text-muted-foreground leading-relaxed">
            Each company receives four composite scores updated nightly. Scores use an exponential
            decay model — recent signals carry full weight; older signals diminish by a domain-specific
            half-life. Overall score uses a tanh soft-cap to prevent stacking from inflating a permanent 100.
          </p>
        </div>
        <div className="grid sm:grid-cols-2 gap-4">
          {SCORES.map((s) => (
            <div key={s.label} className="border border-border rounded-lg p-6 bg-card flex items-start gap-5">
              <div className="font-mono text-xl font-bold text-primary shrink-0">{s.example}</div>
              <div>
                <div className="font-semibold text-sm mb-1.5">{s.label}</div>
                <div className="text-xs text-muted-foreground leading-relaxed">{s.desc}</div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Licensing */}
      <section className="border-t border-border bg-card">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-20 sm:py-24">
          <div className="grid lg:grid-cols-2 gap-12 items-start">
            <div>
              <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground mb-5">
                Licensing
              </p>
              <h2 className="text-3xl font-bold tracking-tight mb-5">
                Standalone or Bundled
              </h2>
              <p className="text-muted-foreground leading-relaxed mb-6">
                Procurement Intelligence Radar™ is available as an independent subscription — the only
                CIOS module that does not require the full platform. Organizations that need market
                surveillance without the full procurement intelligence suite can license Radar alone.
              </p>
              <p className="text-muted-foreground leading-relaxed mb-8">
                All Professional, Growth, and Enterprise subscribers receive Radar as part of their subscription.
                Upgrading from a Radar license to Professional or higher preserves all company data, signal history,
                and watchlists.
              </p>
              <Link
                href="/pricing"
                className="inline-flex items-center gap-2 text-sm text-primary font-medium hover:text-primary/80 transition-colors"
              >
                View Radar pricing <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
            <div className="border border-border rounded-xl p-8 bg-background font-mono text-sm">
              <div className="text-[10px] uppercase tracking-widest text-muted-foreground mb-6">
                Sample Company Intelligence Brief
              </div>
              <div className="space-y-3 mb-5">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Company</span>
                  <span className="font-semibold">Meridian Federal Inc.</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Tier</span>
                  <span className="text-emerald-400 font-bold">A — Priority</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Overall Score</span>
                  <span className="text-primary">74.3 / 100</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Confidence</span>
                  <span>0.81</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Momentum</span>
                  <span className="text-emerald-400">+22% (30d)</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Buying Probability</span>
                  <span className="text-primary font-bold">78%</span>
                </div>
              </div>
              <div className="border-t border-border pt-4">
                <div className="text-[10px] uppercase tracking-widest text-muted-foreground mb-3">
                  Recent Signals
                </div>
                <div className="space-y-2 text-xs">
                  <div className="flex gap-2">
                    <span className="text-purple-400 shrink-0">↑ HIRE</span>
                    <span className="text-muted-foreground">Capture Manager posted — DoD/IC focus</span>
                  </div>
                  <div className="flex gap-2">
                    <span className="text-emerald-400 shrink-0">↑ IDIQ</span>
                    <span className="text-muted-foreground">OASIS+ on-ramp — Professional Services</span>
                  </div>
                  <div className="flex gap-2">
                    <span className="text-teal-400 shrink-0">↑ CERT</span>
                    <span className="text-muted-foreground">CMMC Level 2 certification renewed</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
