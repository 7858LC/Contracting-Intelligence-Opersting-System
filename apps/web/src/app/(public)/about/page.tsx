import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { buildPageMetadata } from "@/lib/metadata";
import { breadcrumbSchema, organizationSchema } from "@/lib/jsonld";

const BASE_URL = process.env.NEXT_PUBLIC_APP_URL || "https://uzimaamka.com";

export const metadata: Metadata = buildPageMetadata({
  title: "About Uzima Amka Ventures — Defining Procurement Intelligence™",
  description:
    "Uzima Amka Ventures was founded on the thesis that public sector contracting deserves the same analytical rigor applied to commercial competitive strategy.",
  path: "/about",
});

const VALUES = [
  {
    title: "Evidence Over Assertion",
    desc: "Every CIOS recommendation carries a confidence score, evidence sources, regulatory citation, and a declared set of assumptions. Conclusions without evidence do not enter the system.",
  },
  {
    title: "Rigor Over Convenience",
    desc: "The analytical discipline of Procurement Intelligence™ is deliberate and structured. We do not optimize for speed at the expense of defensible analysis.",
  },
  {
    title: "Access Over Gatekeeping",
    desc: "The intelligence that sophisticated incumbents have accumulated through decades of relationship-building should be accessible to any organization willing to apply structured methodology.",
  },
  {
    title: "Structure Over Instinct",
    desc: "BD intuition is valuable. It is also inconsistent, non-transferable, and non-auditable. CIOS converts institutional knowledge into structured, reproducible intelligence frameworks.",
  },
];

export default function AboutPage() {
  const crumbs = breadcrumbSchema([
    { name: "Home", url: BASE_URL },
    { name: "About", url: `${BASE_URL}/about` },
  ]);

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(crumbs) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(organizationSchema) }}
      />

      {/* Hero */}
      <section className="border-b border-border py-20 sm:py-28">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="max-w-3xl">
            <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-primary mb-6">
              About Uzima Amka Ventures
            </p>
            <h1 className="text-4xl sm:text-5xl font-bold tracking-tight leading-[1.06] mb-6">
              Defining a new executive management discipline.
            </h1>
            <p className="text-lg text-muted-foreground leading-relaxed max-w-2xl">
              Uzima Amka Ventures was founded on a single thesis: the $762B federal contracting market warrants
              the same analytical infrastructure applied to commercial competitive strategy — and that no
              credible platform existed to deliver it.
            </p>
          </div>
        </div>
      </section>

      {/* Mission */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-20 sm:py-24">
        <div className="grid lg:grid-cols-2 gap-14">
          <div>
            <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground mb-5">
              Mission
            </p>
            <h2 className="text-3xl font-bold tracking-tight mb-6">
              Operationalize Procurement Intelligence™ as a management discipline.
            </h2>
            <p className="text-muted-foreground leading-relaxed mb-5">
              Procurement decisions in the public sector are made with less analytical infrastructure than
              commercial organizations apply to routine market entry decisions. Organizations that win
              government contracts at scale do so through institutional knowledge, relationship networks,
              and pattern recognition built over decades — none of which is transferable, auditable, or
              systematically improvable.
            </p>
            <p className="text-muted-foreground leading-relaxed mb-5">
              CIOS™ changes this. By aggregating public market data, applying structured scoring
              methodologies, and delivering decision-ready intelligence through a platform built for
              procurement practitioners, we transform contracting from an instinct-driven function
              into a managed, measurable discipline.
            </p>
            <p className="text-muted-foreground leading-relaxed">
              Procurement Intelligence™ is not a feature. It is a category we are creating — one that
              will define how serious organizations compete in the public sector over the next decade.
            </p>
          </div>
          <div>
            <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground mb-5">
              The Name
            </p>
            <h2 className="text-3xl font-bold tracking-tight mb-6">
              Uzima Amka
            </h2>
            <p className="text-muted-foreground leading-relaxed mb-5">
              Uzima Amka is Swahili for "wake to life" — a vital awakening. The name reflects the
              transformation we believe is available to procurement organizations that adopt structured
              intelligence as a core operating discipline.
            </p>
            <p className="text-muted-foreground leading-relaxed mb-5">
              Organizations that are currently reactive — responding to solicitations as they appear —
              can become anticipatory: building relationships, positioning capabilities, and structuring
              teams before RFPs drop. That transition, from reactive to strategic, is the awakening
              the company name describes.
            </p>
            <p className="text-muted-foreground leading-relaxed">
              Ventures signals our commitment to building the ecosystem around Procurement Intelligence™ —
              not just the platform, but the research, community, and management frameworks that
              define a durable category.
            </p>
          </div>
        </div>
      </section>

      {/* Values */}
      <section className="border-t border-b border-border bg-card">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-20 sm:py-24">
          <div className="max-w-2xl mb-14">
            <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground mb-5">
              Operating Principles
            </p>
            <h2 className="text-3xl font-bold tracking-tight">
              How we build and why it matters.
            </h2>
          </div>
          <div className="grid sm:grid-cols-2 gap-4">
            {VALUES.map((v) => (
              <div key={v.title} className="border border-border rounded-lg p-6 bg-background">
                <div className="font-semibold mb-2">{v.title}</div>
                <div className="text-sm text-muted-foreground leading-relaxed">{v.desc}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Investment thesis */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-20 sm:py-24">
        <div className="max-w-2xl">
          <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground mb-5">
            Market Thesis
          </p>
          <h2 className="text-3xl font-bold tracking-tight mb-6">
            The intelligence gap in public sector contracting.
          </h2>
          <div className="space-y-5 text-muted-foreground leading-relaxed">
            <p>
              The federal government awards approximately $762B in contracts annually. The top 100 prime
              contractors account for roughly 60% of that spend. The remaining 40% — over $300B — is
              competed by thousands of mid-market contractors who operate without the dedicated intelligence
              infrastructure that the major primes maintain.
            </p>
            <p>
              Mid-market federal contractors typically invest 2-4% of contract revenue in capture and
              proposal activities, yet achieve win rates between 15-25%. The gap between investment and
              outcome is not primarily a proposal writing problem — it is an intelligence problem.
              Organizations pursue the wrong opportunities, at the wrong time, with insufficient understanding
              of the competitive landscape.
            </p>
            <p>
              CIOS addresses this gap with infrastructure — the same kind of systematic market intelligence
              capability that top-tier contractors have built through decades of institutional investment,
              delivered as a subscription platform accessible to organizations at every scale.
            </p>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="border-t border-border bg-card">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-16">
          <div className="max-w-xl">
            <h2 className="text-2xl font-bold tracking-tight mb-3">
              Join the early access program.
            </h2>
            <p className="text-sm text-muted-foreground leading-relaxed mb-6">
              We are working directly with select organizations to configure CIOS for their specific
              capture portfolios. Early access participants shape the platform and receive preferred pricing.
            </p>
            <div className="flex flex-wrap gap-4">
              <Link
                href="/auth/register"
                className="inline-flex items-center gap-2 bg-primary text-primary-foreground px-6 py-3 rounded-md font-semibold hover:bg-primary/90 transition-colors text-sm"
              >
                Request Early Access <ArrowRight className="w-4 h-4" />
              </Link>
              <Link
                href="/executive-council"
                className="inline-flex items-center gap-2 border border-border px-6 py-3 rounded-md font-semibold text-muted-foreground hover:text-foreground transition-colors text-sm"
              >
                Executive Council
              </Link>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
