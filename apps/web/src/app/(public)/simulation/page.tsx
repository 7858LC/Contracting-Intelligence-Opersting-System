import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight, Shield } from "lucide-react";
import { buildPageMetadata } from "@/lib/metadata";
import { breadcrumbSchema, productSchema } from "@/lib/jsonld";

const BASE_URL = process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000";

export const metadata: Metadata = buildPageMetadata({
  title: "Award Simulation™ — Source Selection Emulation Before You Commit",
  description:
    "Probabilistic award modeling aligned to FAR 15.305 and DFARS source selection procedures. Red team scoring, deficiency analysis, and win probability intervals.",
  path: "/simulation",
});

const SIMULATION_OUTPUTS = [
  { label: "Technical Score", desc: "Color/adjectival rating per DOD evaluation standards (Outstanding, Good, Acceptable, Marginal, Unacceptable). Sub-scores by PWS section." },
  { label: "Past Performance Score", desc: "Relevance and quality assessment. Evaluator-perspective scoring of your cited past performance against this opportunity's profile." },
  { label: "Price Competitiveness", desc: "Price-to-win band estimate based on similar awards. Whether your price is competitive, above-band, or potentially too low." },
  { label: "Weaknesses", desc: "Specific weaknesses in the proposed approach — items that reduce the government's confidence but don't disqualify." },
  { label: "Significant Weaknesses", desc: "Items that significantly increase risk to award. Requires explicit mitigation strategy before submission." },
  { label: "Deficiencies", desc: "Compliance failures or material omissions that would require clarification or may result in exclusion from competitive range." },
  { label: "Award Probability", desc: "Composite probability estimate with confidence interval. Derived from score projection, price competitiveness, and competitive field estimate." },
  { label: "Ranked Improvement Actions", desc: "Prioritized list of changes ordered by expected score impact. Each action includes an estimated point improvement." },
];

export default function SimulationPage() {
  const crumbs = breadcrumbSchema([
    { name: "Home", url: BASE_URL },
    { name: "Award Simulation™", url: `${BASE_URL}/simulation` },
  ]);
  const product = productSchema({
    name: "Award Simulation™",
    description: "FAR 15.305-aligned source selection emulation. Red team scoring, deficiency identification, and award probability modeling before resource commitment.",
    url: `${BASE_URL}/simulation`,
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
              <Shield className="w-3.5 h-3.5" />
              Module 03 — Growth+
            </div>
            <h1 className="text-4xl sm:text-5xl font-bold tracking-tight leading-[1.06] mb-5">
              Award Simulation™
            </h1>
            <p className="text-xl text-muted-foreground font-medium mb-5">
              Source selection emulation before you commit proposal resources.
            </p>
            <p className="text-base text-muted-foreground leading-relaxed mb-10 max-w-2xl">
              Award Simulation™ emulates the government source selection process — scoring your proposed
              approach the way an evaluator would under FAR 15.305 and DFARS procedures. The simulation
              identifies weaknesses, significant weaknesses, and deficiencies before you submit, along
              with ranked improvement actions and an updated award probability estimate.
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

      {/* Simulation outputs */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-20 sm:py-24">
        <div className="max-w-2xl mb-14">
          <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground mb-5">Simulation Outputs</p>
          <h2 className="text-3xl font-bold tracking-tight mb-5">Eight Structured Outputs Per Simulation</h2>
          <p className="text-muted-foreground leading-relaxed">
            Each simulation run produces a structured evaluation report aligned to the expected output
            of a government source selection evaluation board. The report is reproducible and comparable
            across multiple simulation runs as the proposal evolves.
          </p>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {SIMULATION_OUTPUTS.map((o, i) => (
            <div key={o.label} className="border border-border rounded-lg p-5 bg-card">
              <div className="font-mono text-[10px] text-muted-foreground mb-3 uppercase tracking-widest">
                {String(i + 1).padStart(2, "0")}
              </div>
              <div className="font-semibold text-sm mb-2">{o.label}</div>
              <div className="text-xs text-muted-foreground leading-relaxed">{o.desc}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Sample output */}
      <section className="border-t border-b border-border bg-card">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-16">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div>
              <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground mb-5">Evaluation Methodology</p>
              <h2 className="text-2xl font-bold tracking-tight mb-5">The same standards the government uses</h2>
              <p className="text-muted-foreground leading-relaxed mb-5">
                Award Simulation™ is calibrated to the evaluation criteria specified in the solicitation.
                The simulation applies FAR 15.305 evaluation standards — cost or price, past performance,
                and technical/management approach — using the specific weights from the RFP.
              </p>
              <p className="text-muted-foreground leading-relaxed">
                For DFARS acquisitions, the simulation uses the DOD Source Selection Procedures&apos; color
                and adjectival rating system. For non-DOD acquisitions, it adapts to the agency-specific
                evaluation framework defined in Section M of the solicitation.
              </p>
            </div>
            <div className="border border-border rounded-xl p-6 bg-background font-mono text-sm">
              <div className="text-[10px] uppercase tracking-widest text-muted-foreground mb-5">
                Simulation Result — Sample
              </div>
              <div className="space-y-3 mb-5">
                {[
                  { label: "Technical Approach", score: "82", rating: "Good", color: "text-emerald-400" },
                  { label: "Past Performance", score: "75", rating: "Acceptable", color: "text-lime-400" },
                  { label: "Price Competitiveness", score: "61", rating: "Marginal", color: "text-amber-400" },
                  { label: "Compliance", score: "94", rating: "Outstanding", color: "text-emerald-400" },
                ].map((r) => (
                  <div key={r.label} className="flex justify-between items-center">
                    <span className="text-muted-foreground text-xs">{r.label}</span>
                    <span className={`text-xs font-medium ${r.color}`}>{r.score} — {r.rating}</span>
                  </div>
                ))}
              </div>
              <div className="border-t border-border pt-4 space-y-2">
                <div className="flex justify-between">
                  <span className="text-muted-foreground text-xs">Weaknesses identified</span>
                  <span className="text-xs">2</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground text-xs">Significant Weaknesses</span>
                  <span className="text-amber-400 text-xs font-medium">1</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground text-xs">Deficiencies</span>
                  <span className="text-emerald-400 text-xs">0</span>
                </div>
                <div className="border-t border-border pt-3 flex justify-between items-center">
                  <span className="text-muted-foreground text-xs">Award Probability</span>
                  <span className="text-primary text-lg font-bold">67%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground text-xs">Gate Decision</span>
                  <span className="text-amber-400 text-xs font-semibold">REVISE BEFORE SUBMIT</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Availability */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-16">
        <div className="max-w-xl">
          <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground mb-4">Availability</p>
          <h2 className="text-2xl font-bold tracking-tight mb-3">Included in Growth+</h2>
          <p className="text-sm text-muted-foreground leading-relaxed mb-6">
            Award Simulation™ is available with Growth and Enterprise subscriptions. Each subscription
            tier includes a monthly simulation allocation; Enterprise subscribers receive unlimited simulations.
          </p>
          <Link href="/pricing" className="inline-flex items-center gap-2 text-sm text-primary font-medium hover:text-primary/80 transition-colors">
            Compare plans <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </section>
    </>
  );
}
