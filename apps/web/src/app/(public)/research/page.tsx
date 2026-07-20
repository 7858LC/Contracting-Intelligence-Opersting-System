import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight, BookOpen } from "lucide-react";
import { buildPageMetadata } from "@/lib/metadata";
import { breadcrumbSchema } from "@/lib/jsonld";

const BASE_URL = process.env.NEXT_PUBLIC_APP_URL || "https://uzimaamka.com";

export const metadata: Metadata = buildPageMetadata({
  title: "Knowledge Vault™ & Research — Procurement Intelligence™ by Uzima Amka Ventures",
  description:
    "Institutional intelligence management and market research. Knowledge Vault™ structures past performance, capabilities, and teaming data for structured capture retrieval.",
  path: "/research",
});

const VAULT_CAPABILITIES = [
  { label: "Past Performance Library", desc: "Structured storage of contract references with NAICS tagging, scope summaries, performance ratings, and evaluator contacts." },
  { label: "Capability Evidence Repository", desc: "Organized capability evidence with gap analysis against active opportunities. Identifies where claims require additional documentation." },
  { label: "Teaming Network", desc: "Documented partner relationships with capability mapping, prior teaming history, and performance assessment from past contracts." },
  { label: "Semantic Search", desc: "Natural language search across the full vault. Retrieves relevant past performance and capabilities based on requirement description, not keyword match." },
  { label: "Capture Team Knowledge Base", desc: "Structured capture notes, agency research, and intelligence memos organized by agency, buyer, and pursuit." },
  { label: "Institutional Memory", desc: "Preserves intelligence from departing staff. Knowledge documented in the vault remains retrievable regardless of team composition." },
];

const RESEARCH_REPORTS = [
  { title: "Federal Contract Market Annual Review", cadence: "Annual", desc: "Comprehensive analysis of federal contract spending, award trends, and competitive dynamics across key NAICS sectors." },
  { title: "Procurement Intelligence Benchmark", cadence: "Semi-annual", desc: "Win rate, bid cost, and pipeline metrics benchmarked across organizations of similar size and sector focus." },
  { title: "Agency Intelligence Brief", cadence: "Quarterly", desc: "Agency-specific buying patterns, new program indicators, and relationship maps for ten priority agencies." },
  { title: "Competitive Landscape Monitor", cadence: "Monthly", desc: "Tracking report on competitor contract activity, teaming patterns, and market positioning across key NAICS codes." },
];

export default function ResearchPage() {
  const crumbs = breadcrumbSchema([
    { name: "Home", url: BASE_URL },
    { name: "Research & Knowledge Vault™", url: `${BASE_URL}/research` },
  ]);

  return (
    <>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(crumbs) }} />

      {/* Hero */}
      <section className="border-b border-border py-20 sm:py-28">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2 text-[11px] font-mono uppercase tracking-[0.18em] text-primary mb-6">
              <BookOpen className="w-3.5 h-3.5" />
              Module 04 — Professional+
            </div>
            <h1 className="text-4xl sm:text-5xl font-bold tracking-tight leading-[1.06] mb-5">
              Knowledge Vault™<br />
              <span className="text-muted-foreground font-normal">& Research</span>
            </h1>
            <p className="text-xl text-muted-foreground font-medium mb-5">
              Institutional intelligence. Structured for retrieval.
            </p>
            <p className="text-base text-muted-foreground leading-relaxed mb-10 max-w-2xl">
              Knowledge Vault™ is the institutional memory layer of CIOS™. It organizes your organization's
              past performance, capability evidence, teaming relationships, and capture intelligence into
              a searchable, structured repository that reduces capture ramp time and prevents institutional forgetting.
            </p>
            <div className="flex flex-wrap gap-4">
              <Link href="/auth/register" className="inline-flex items-center gap-2 bg-primary text-primary-foreground px-6 py-3 rounded-md font-semibold hover:bg-primary/90 transition-colors text-sm">
                Request Access <ArrowRight className="w-4 h-4" />
              </Link>
              <Link href="/executive-council" className="inline-flex items-center gap-2 border border-border px-6 py-3 rounded-md font-semibold text-muted-foreground hover:text-foreground transition-colors text-sm">
                Research Reports
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Vault capabilities */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-20 sm:py-24">
        <div className="max-w-2xl mb-14">
          <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground mb-5">Knowledge Vault™</p>
          <h2 className="text-3xl font-bold tracking-tight mb-5">Six Structured Knowledge Layers</h2>
          <p className="text-muted-foreground leading-relaxed">
            Each layer of the Knowledge Vault is purpose-built for a specific type of institutional knowledge.
            Per-tenant vector isolation ensures your data never co-mingles with other organizations.
          </p>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {VAULT_CAPABILITIES.map((c) => (
            <div key={c.label} className="border border-border rounded-lg p-5 bg-card">
              <div className="font-semibold text-sm mb-2">{c.label}</div>
              <div className="text-xs text-muted-foreground leading-relaxed">{c.desc}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Research reports */}
      <section className="border-t border-b border-border bg-card">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-20 sm:py-24">
          <div className="max-w-2xl mb-14">
            <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground mb-5">Research Program</p>
            <h2 className="text-3xl font-bold tracking-tight mb-5">Procurement Intelligence™ Research</h2>
            <p className="text-muted-foreground leading-relaxed">
              Uzima Amka Ventures publishes market intelligence research for the Procurement Intelligence™
              executive community. Executive Council members receive reports ahead of public release.
            </p>
          </div>
          <div className="grid sm:grid-cols-2 gap-4">
            {RESEARCH_REPORTS.map((r) => (
              <div key={r.title} className="border border-border rounded-lg p-6 bg-background">
                <div className="flex items-center justify-between mb-3">
                  <span className="font-semibold text-sm">{r.title}</span>
                  <span className="font-mono text-[10px] text-muted-foreground uppercase tracking-widest shrink-0 ml-3">
                    {r.cadence}
                  </span>
                </div>
                <div className="text-xs text-muted-foreground leading-relaxed">{r.desc}</div>
              </div>
            ))}
          </div>
          <div className="mt-8">
            <Link href="/executive-council" className="inline-flex items-center gap-2 text-sm text-primary font-medium hover:text-primary/80 transition-colors">
              Access research through the Executive Council <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      </section>

      {/* Availability */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-16">
        <div className="max-w-xl">
          <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground mb-4">Availability</p>
          <h2 className="text-2xl font-bold tracking-tight mb-3">Included in Professional+</h2>
          <p className="text-sm text-muted-foreground leading-relaxed mb-6">
            Knowledge Vault™ is available with Professional, Growth, and Enterprise subscriptions.
            Storage allocations scale with subscription tier; Enterprise offers unlimited storage with
            customer-owned encryption key option.
          </p>
          <Link href="/pricing" className="inline-flex items-center gap-2 text-sm text-primary font-medium hover:text-primary/80 transition-colors">
            Compare plans <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </section>
    </>
  );
}
