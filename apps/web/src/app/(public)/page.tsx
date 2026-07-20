import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight, BarChart3, BookOpen, Brain, Radio, Shield, Target, Users } from "lucide-react";
import { buildPageMetadata } from "@/lib/metadata";
import { organizationSchema, softwareApplicationSchema } from "@/lib/jsonld";

export const metadata: Metadata = buildPageMetadata({
  title: "Procurement Intelligence™ — Executive Decision Support for Public Sector Growth",
  description:
    "Uzima Amka Ventures delivers the analytical infrastructure and decision frameworks that transform public sector contracting into a managed intelligence discipline.",
  path: "/",
});

const MODULES = [
  {
    label: "Module 00",
    name: "Procurement Intelligence Radar™",
    desc: "Market surveillance and company intelligence. Detect procurement signals before solicitations publish.",
    href: "/radar",
    icon: Radio,
  },
  {
    label: "Module 01",
    name: "Procurement Intelligence Diagnostics™",
    desc: "Systemic assessment of competitive position. Identify structural weaknesses before they surface in source selection.",
    href: "/diagnostics",
    icon: BarChart3,
  },
  {
    label: "Module 02",
    name: "Pursuit Decision Quality™",
    desc: "Bid/no-bid analysis with institutional rigor. Eight-dimension scoring across strategic alignment and execution risk.",
    href: "/pdq",
    icon: Target,
  },
  {
    label: "Module 03",
    name: "Award Simulation™",
    desc: "Probabilistic award modeling before resource commitment. FAR 15.305-aligned source selection emulation.",
    href: "/simulation",
    icon: Shield,
  },
  {
    label: "Module 04",
    name: "Knowledge Vault™",
    desc: "Institutional intelligence and past performance management. Structured retrieval for capture teams.",
    href: "/research",
    icon: BookOpen,
  },
  {
    label: "Module 05",
    name: "Executive Dashboard™",
    desc: "Portfolio-level procurement analytics for executive leadership. Pipeline health, win rates, and resource allocation.",
    href: "/platform",
    icon: Brain,
  },
];

const PRINCIPLES = [
  {
    n: "01",
    title: "Intelligence Before Intent",
    body: "Know which buyers are building programs before solicitations publish. Market sensing, not calendar management.",
  },
  {
    n: "02",
    title: "Portfolio Discipline",
    body: "Pursue what you can win, not what appears on the calendar. Bid decisions as resource allocation, not opportunity reaction.",
  },
  {
    n: "03",
    title: "Evidence-Based Commitment",
    body: "Allocate capture resources based on scored opportunity quality. Every recommendation carries a confidence score and evidence trail.",
  },
];

const COUNCIL_BENEFITS = [
  "Quarterly Procurement Intelligence™ market report",
  "Pre-release access to new CIOS™ modules",
  "Direct input on the platform research agenda",
  "Executive roundtable access — four sessions per year",
  "Benchmark data from peer organizations",
  "Preferred pricing on enterprise contracts",
];

export default function HomePage() {
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(organizationSchema) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(softwareApplicationSchema) }}
      />

      {/* Hero */}
      <section className="border-b border-border py-20 sm:py-28">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="max-w-3xl">
            <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-primary mb-6">
              Uzima Amka Ventures
            </p>
            <h1 className="text-5xl sm:text-6xl md:text-7xl font-bold tracking-tight leading-[1.04] mb-5">
              Procurement<br />Intelligence™
            </h1>
            <p className="text-xl sm:text-2xl font-medium text-muted-foreground mb-5">
              Executive Decision Support for Public Sector Growth
            </p>
            <p className="text-base text-muted-foreground mb-10 max-w-2xl leading-relaxed">
              The systematic application of competitive intelligence, financial analysis, and regulatory expertise
              to public sector contracting decisions. Not proposal software. Not a CRM.
              An analytical discipline — delivered through CIOS™.
            </p>
            <div className="flex flex-wrap gap-4">
              <Link
                href="/auth/register"
                className="inline-flex items-center gap-2 bg-primary text-primary-foreground px-6 py-3 rounded-md font-semibold hover:bg-primary/90 transition-colors text-sm"
              >
                Request Early Access <ArrowRight className="w-4 h-4" />
              </Link>
              <Link
                href="/platform"
                className="inline-flex items-center gap-2 border border-border px-6 py-3 rounded-md font-semibold text-muted-foreground hover:text-foreground hover:border-foreground/30 transition-colors text-sm"
              >
                Explore the Platform
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Data bar */}
      <section className="border-b border-border bg-card">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-6 text-center divide-x divide-border">
            {[
              { value: "$762B", label: "Federal Contract Market (FY2024)" },
              { value: "47+", label: "Integrated Data Sources" },
              { value: "6", label: "Intelligence Dimensions" },
              { value: "<72h", label: "Signal Detection Latency" },
            ].map((stat) => (
              <div key={stat.label} className="py-2 px-4">
                <div className="font-mono text-2xl sm:text-3xl font-bold text-primary mb-1">
                  {stat.value}
                </div>
                <div className="text-xs text-muted-foreground leading-snug">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Category definition */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-20 sm:py-24">
        <div className="grid lg:grid-cols-2 gap-14 items-start">
          <div>
            <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground mb-5">
              A New Executive Discipline
            </p>
            <h2 className="text-3xl sm:text-4xl font-bold tracking-tight mb-6">
              What is<br />Procurement Intelligence™?
            </h2>
            <p className="text-muted-foreground leading-relaxed mb-5">
              The systematic acquisition, analysis, and application of competitive intelligence to public sector
              contracting decisions. It extends the rigor applied to commercial competitive analysis — market sizing,
              win probability modeling, relationship mapping — into a domain where most organizations still rely on
              bid calendars and BD pipelines.
            </p>
            <p className="text-muted-foreground leading-relaxed">
              The average federal contractor pursues 40% more opportunities than their win rate justifies.
              The result is diluted execution, inflated bid costs, and predictable loss rates that compound over time.
              Procurement Intelligence™ is the analytical framework that corrects this — positioning contracting as
              a portfolio management problem where intelligence, timing, and competitive positioning determine outcomes
              before the solicitation drops.
            </p>
          </div>
          <div className="space-y-3">
            {PRINCIPLES.map((p) => (
              <div key={p.n} className="border border-border rounded-lg p-5 bg-card">
                <div className="font-mono text-[10px] text-muted-foreground mb-2 uppercase tracking-widest">
                  {p.n}
                </div>
                <div className="font-semibold mb-2 text-sm">{p.title}</div>
                <div className="text-sm text-muted-foreground leading-relaxed">{p.body}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Platform section */}
      <section className="border-t border-b border-border bg-card">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-20 sm:py-24">
          <div className="max-w-2xl mb-14">
            <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground mb-5">
              The Operating System
            </p>
            <h2 className="text-3xl sm:text-4xl font-bold tracking-tight mb-5">
              CIOS™{" "}
              <span className="text-muted-foreground font-normal text-2xl sm:text-3xl">
                Contract Intelligence Operating System
              </span>
            </h2>
            <p className="text-muted-foreground leading-relaxed">
              Six analytical modules. One integrated platform. CIOS aggregates signals from 47 federal data sources,
              applies structured analysis across six intelligence dimensions, and delivers decision-ready briefs
              to executive capture teams.
            </p>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {MODULES.map((mod) => (
              <Link
                key={mod.name}
                href={mod.href}
                className="group border border-border rounded-lg p-5 bg-background hover:border-primary/40 transition-colors"
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="w-8 h-8 rounded-md bg-primary/10 flex items-center justify-center">
                    <mod.icon className="w-4 h-4 text-primary" />
                  </div>
                  <ArrowRight className="w-4 h-4 text-muted-foreground/30 group-hover:text-primary transition-colors" />
                </div>
                <div className="font-mono text-[10px] text-muted-foreground mb-2 uppercase tracking-widest">
                  {mod.label}
                </div>
                <div className="font-semibold text-sm mb-2">{mod.name}</div>
                <div className="text-xs text-muted-foreground leading-relaxed">{mod.desc}</div>
              </Link>
            ))}
          </div>
          <div className="mt-8">
            <Link
              href="/platform"
              className="inline-flex items-center gap-2 text-sm text-primary hover:text-primary/80 font-medium transition-colors"
            >
              Explore the CIOS™ platform <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      </section>

      {/* Executive Council */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-20 sm:py-24">
        <div className="grid lg:grid-cols-2 gap-14 items-start">
          <div>
            <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground mb-5">
              Advisory Community
            </p>
            <h2 className="text-3xl sm:text-4xl font-bold tracking-tight mb-5">
              Procurement Intelligence™ Executive Council
            </h2>
            <p className="text-muted-foreground leading-relaxed mb-5">
              A closed community of senior procurement executives defining Procurement Intelligence™ as a management
              discipline. Members shape the research agenda, advise on platform development, and access intelligence
              reports before public release.
            </p>
            <p className="text-muted-foreground leading-relaxed mb-8">
              Membership is by invitation. Current members represent organizations with cumulative federal contract
              portfolios exceeding $2.4B annually.
            </p>
            <Link
              href="/executive-council"
              className="inline-flex items-center gap-2 text-sm text-primary font-medium hover:text-primary/80 transition-colors"
            >
              Learn about the Executive Council <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
          <div className="border border-border rounded-xl p-8 bg-card">
            <div className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground mb-6">
              Council Member Benefits
            </div>
            <ul className="space-y-4">
              {COUNCIL_BENEFITS.map((b) => (
                <li key={b} className="flex items-start gap-3 text-sm">
                  <div className="w-px h-4 bg-primary rounded-full mt-0.5 shrink-0" />
                  <span className="text-muted-foreground">{b}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="border-t border-border bg-card">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-20 sm:py-24">
          <div className="max-w-2xl">
            <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground mb-5">
              Early Access Program
            </p>
            <h2 className="text-3xl sm:text-4xl font-bold tracking-tight mb-5">
              Request Early Access
            </h2>
            <p className="text-muted-foreground leading-relaxed mb-8">
              CIOS is in active pilot with select government contractors. Early access participants work directly
              with our intelligence team to configure the platform for their specific capture portfolio.
              No credit card required during the pilot period.
            </p>
            <div className="flex flex-wrap gap-4">
              <Link
                href="/auth/register"
                className="inline-flex items-center gap-2 bg-primary text-primary-foreground px-6 py-3 rounded-md font-semibold hover:bg-primary/90 transition-colors text-sm"
              >
                Request Early Access <ArrowRight className="w-4 h-4" />
              </Link>
              <Link
                href="/pricing"
                className="inline-flex items-center gap-2 border border-border px-6 py-3 rounded-md font-semibold text-muted-foreground hover:text-foreground transition-colors text-sm"
              >
                View Pricing
              </Link>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
