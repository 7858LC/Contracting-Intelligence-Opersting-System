import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight, BarChart3, BookOpen, Brain, Lock, Radio, Shield, Target, Zap } from "lucide-react";
import { buildPageMetadata } from "@/lib/metadata";
import { breadcrumbSchema, productSchema } from "@/lib/jsonld";

const BASE_URL = process.env.NEXT_PUBLIC_APP_URL || "https://uzimaamka.com";

export const metadata: Metadata = buildPageMetadata({
  title: "CIOS™ — Contract Intelligence Operating System",
  description:
    "The operating system powering Procurement Intelligence™. Six analytical modules, 47 data sources, and AI-assisted analysis across the full procurement lifecycle.",
  path: "/platform",
});

const DIMENSIONS = [
  {
    id: "D1",
    label: "Market Intelligence",
    desc: "Pre-solicitation signal detection across SAM.gov, USASpending, GSA schedules, and job board data. Identifies buyers building programs before RFPs publish.",
    icon: Radio,
  },
  {
    id: "D2",
    label: "Competitive Position",
    desc: "Systematic assessment of win factors: incumbent status, past performance proximity, team capability alignment, and relationship depth relative to known competitors.",
    icon: Target,
  },
  {
    id: "D3",
    label: "Pursuit Quality",
    desc: "Bid/no-bid analysis against eight strategic dimensions. Translates qualitative BD instinct into scored, auditable decisions with resource allocation implications.",
    icon: BarChart3,
  },
  {
    id: "D4",
    label: "Award Modeling",
    desc: "Source selection emulation aligned to FAR 15.305 and DFARS procedures. Red team scoring with color ratings, deficiency analysis, and probability intervals.",
    icon: Shield,
  },
  {
    id: "D5",
    label: "Institutional Knowledge",
    desc: "Structured retrieval of past performance, capability evidence, and teaming relationships. Reduces capture team ramp time and prevents institutional forgetting.",
    icon: BookOpen,
  },
  {
    id: "D6",
    label: "Portfolio Analytics",
    desc: "Executive-level visibility into pipeline health, resource utilization, win rate trends, and concentration risk across the full contract portfolio.",
    icon: Brain,
  },
];

const MODULES = [
  { name: "Procurement Intelligence Radar™", tier: "All tiers", href: "/radar" },
  { name: "Procurement Intelligence Diagnostics™", tier: "Professional+", href: "/diagnostics" },
  { name: "Pursuit Decision Quality™", tier: "Professional+", href: "/pdq" },
  { name: "Award Simulation™", tier: "Growth+", href: "/simulation" },
  { name: "Knowledge Vault™", tier: "Professional+", href: "/research" },
  { name: "Executive Dashboard™", tier: "Enterprise", href: "/platform#modules" },
];

const SECURITY_PROPS = [
  {
    title: "Row-Level Security",
    desc: "PostgreSQL RLS enforced on every tenant-scoped table. Data isolation guaranteed at the database layer, not only the application layer.",
  },
  {
    title: "Per-Tenant Encryption",
    desc: "All sensitive data encrypted with tenant-derived keys. No cross-tenant key reuse. Customer-owned key option available on Enterprise.",
  },
  {
    title: "Immutable Audit Log",
    desc: "Every data access and AI recommendation logged with timestamp, user, model version, and evidence. Full reproducibility for compliance review.",
  },
  {
    title: "Zero Trust Architecture",
    desc: "JWT validation on every request. No implicit trust. API gateway enforces authorization at every service boundary.",
  },
  {
    title: "Private Vector Isolation",
    desc: "Each tenant receives a private Qdrant collection. Embeddings are never shared or commingled. Zero cross-contamination by design.",
  },
  {
    title: "SOC 2 Ready",
    desc: "Architecture designed for SOC 2 Type II from day one. NIST 800-171 aligned. FedRAMP moderate-compatible infrastructure patterns.",
  },
];

export default function PlatformPage() {
  const crumbs = breadcrumbSchema([
    { name: "Home", url: BASE_URL },
    { name: "CIOS™ Platform", url: `${BASE_URL}/platform` },
  ]);
  const product = productSchema({
    name: "CIOS™ — Contract Intelligence Operating System",
    description: "The operating system powering Procurement Intelligence™.",
    url: `${BASE_URL}/platform`,
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
            <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-primary mb-6">
              The Platform
            </p>
            <h1 className="text-4xl sm:text-5xl md:text-6xl font-bold tracking-tight leading-[1.06] mb-5">
              CIOS™
            </h1>
            <p className="text-xl sm:text-2xl text-muted-foreground font-medium mb-5">
              Contract Intelligence Operating System
            </p>
            <p className="text-base text-muted-foreground mb-10 max-w-2xl leading-relaxed">
              The operating system powering Procurement Intelligence™. CIOS aggregates signals from 47 federal
              data sources, applies AI-assisted analysis across six intelligence dimensions, and delivers
              decision-ready briefs to executive capture teams across the full procurement lifecycle.
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

      {/* Six Dimensions */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-20 sm:py-24">
        <div className="max-w-2xl mb-14">
          <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground mb-5">
            Intelligence Architecture
          </p>
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight mb-5">
            Six Intelligence Dimensions
          </h2>
          <p className="text-muted-foreground leading-relaxed">
            CIOS structures procurement intelligence across six analytical dimensions that mirror how
            sophisticated buyers and evaluators assess competitive position. Each dimension feeds
            the next in a continuous intelligence cycle.
          </p>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {DIMENSIONS.map((d) => (
            <div key={d.id} className="border border-border rounded-lg p-6 bg-card">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-8 h-8 rounded-md bg-primary/10 flex items-center justify-center shrink-0">
                  <d.icon className="w-4 h-4 text-primary" />
                </div>
                <span className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
                  {d.id}
                </span>
              </div>
              <div className="font-semibold text-sm mb-2">{d.label}</div>
              <div className="text-xs text-muted-foreground leading-relaxed">{d.desc}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Modules */}
      <section id="modules" className="border-t border-b border-border bg-card">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-20 sm:py-24">
          <div className="max-w-2xl mb-14">
            <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground mb-5">
              Module Suite
            </p>
            <h2 className="text-3xl sm:text-4xl font-bold tracking-tight mb-5">
              Independently Licensable Modules
            </h2>
            <p className="text-muted-foreground leading-relaxed">
              Each CIOS module is independently licensable and incrementally composable. Start with
              Procurement Intelligence Radar™ and expand to the full platform as your intelligence
              program matures.
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left pb-3 pr-8 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Module
                  </th>
                  <th className="text-left pb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Available From
                  </th>
                  <th className="text-right pb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Details
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {MODULES.map((m) => (
                  <tr key={m.name} className="group">
                    <td className="py-4 pr-8 font-medium">{m.name}</td>
                    <td className="py-4 text-muted-foreground font-mono text-xs">{m.tier}</td>
                    <td className="py-4 text-right">
                      <Link
                        href={m.href}
                        className="text-primary text-xs hover:text-primary/80 transition-colors inline-flex items-center gap-1"
                      >
                        Learn more <ArrowRight className="w-3 h-3" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* Security */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-20 sm:py-24">
        <div className="max-w-2xl mb-14">
          <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground mb-5">
            Security &amp; Compliance
          </p>
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight mb-5">
            Government-Grade Security by Design
          </h2>
          <p className="text-muted-foreground leading-relaxed">
            CIOS was architected for the security requirements of defense contractors and federal agencies
            from day one. Security is structural, not a feature layer applied after the fact.
          </p>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {SECURITY_PROPS.map((s) => (
            <div key={s.title} className="border border-border rounded-lg p-6 bg-card">
              <Lock className="w-4 h-4 text-primary mb-4" />
              <div className="font-semibold text-sm mb-2">{s.title}</div>
              <div className="text-xs text-muted-foreground leading-relaxed">{s.desc}</div>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="border-t border-border bg-card">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-20 sm:py-24">
          <div className="max-w-2xl">
            <h2 className="text-3xl font-bold tracking-tight mb-5">
              Start with Radar. Scale to the full platform.
            </h2>
            <p className="text-muted-foreground leading-relaxed mb-8">
              Procurement Intelligence Radar™ is available as a standalone license and is included in all
              Professional, Growth, and Enterprise subscriptions. Begin building your intelligence program
              before committing to the full CIOS™ suite.
            </p>
            <div className="flex flex-wrap gap-4">
              <Link
                href="/radar"
                className="inline-flex items-center gap-2 bg-primary text-primary-foreground px-6 py-3 rounded-md font-semibold hover:bg-primary/90 transition-colors text-sm"
              >
                Explore Radar <ArrowRight className="w-4 h-4" />
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
    </>
  );
}
