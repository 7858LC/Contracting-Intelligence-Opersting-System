import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight, Users } from "lucide-react";
import { buildPageMetadata } from "@/lib/metadata";
import { breadcrumbSchema } from "@/lib/jsonld";

const BASE_URL = process.env.NEXT_PUBLIC_APP_URL || "https://uzimaamka.com";

export const metadata: Metadata = buildPageMetadata({
  title: "Procurement Intelligence™ Executive Council — Uzima Amka Ventures",
  description:
    "A closed community of senior procurement executives defining Procurement Intelligence™ as a management discipline. Membership by invitation.",
  path: "/executive-council",
});

const MEMBER_BENEFITS = [
  { label: "Research Access", desc: "Quarterly Procurement Intelligence™ market report, semi-annual benchmark, and monthly agency brief — published ahead of public release." },
  { label: "Platform Influence", desc: "Direct input on the CIOS™ research agenda and module roadmap. Council members shape what gets built and in what sequence." },
  { label: "Pre-Release Access", desc: "Early access to new CIOS™ modules during the beta period, with direct access to the product team for feedback." },
  { label: "Executive Roundtables", desc: "Four closed-door sessions per year with senior practitioners across the Council membership. No vendors. Peer-only dialogue." },
  { label: "Benchmark Data", desc: "Access to aggregate performance benchmarks from peer organizations — win rates, bid costs, pipeline conversion, and resource allocation metrics." },
  { label: "Preferred Pricing", desc: "Council members receive preferred pricing on enterprise subscriptions and first access to new licensing tiers as they launch." },
];

const ELIGIBILITY = [
  "C-suite or equivalent responsibility for capture and business development",
  "Organization with active federal contracting portfolio exceeding $5M annually",
  "Commitment to the Procurement Intelligence™ methodology and discipline",
  "Willingness to share anonymized performance data for benchmark research",
  "Attendance at minimum two executive roundtables per year",
];

export default function ExecutiveCouncilPage() {
  const crumbs = breadcrumbSchema([
    { name: "Home", url: BASE_URL },
    { name: "Executive Council", url: `${BASE_URL}/executive-council` },
  ]);

  return (
    <>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(crumbs) }} />

      {/* Hero */}
      <section className="border-b border-border py-20 sm:py-28">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2 text-[11px] font-mono uppercase tracking-[0.18em] text-primary mb-6">
              <Users className="w-3.5 h-3.5" />
              Advisory Community — Membership by Invitation
            </div>
            <h1 className="text-4xl sm:text-5xl font-bold tracking-tight leading-[1.06] mb-5">
              Procurement Intelligence™<br />Executive Council
            </h1>
            <p className="text-xl text-muted-foreground font-medium mb-5">
              The executive community defining a new management discipline.
            </p>
            <p className="text-base text-muted-foreground leading-relaxed mb-10 max-w-2xl">
              The Procurement Intelligence™ Executive Council is a closed community of senior executives
              — VPs of Business Development, Chief Growth Officers, and sector Presidents — who are
              actively building Procurement Intelligence programs at their organizations and who shape
              the direction of the discipline through research, platform advisory, and peer exchange.
            </p>
            <div className="flex flex-wrap gap-4">
              <Link
                href="/auth/register"
                className="inline-flex items-center gap-2 bg-primary text-primary-foreground px-6 py-3 rounded-md font-semibold hover:bg-primary/90 transition-colors text-sm"
              >
                Request Membership Consideration <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* What the Council does */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-20 sm:py-24">
        <div className="grid lg:grid-cols-2 gap-14">
          <div>
            <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground mb-5">Purpose</p>
            <h2 className="text-3xl font-bold tracking-tight mb-6">Why the Council exists.</h2>
            <p className="text-muted-foreground leading-relaxed mb-5">
              Procurement Intelligence™ is being defined as a discipline right now — the frameworks,
              the metrics, the decision quality standards, the organizational structures that will characterize
              leading organizations in five years are being written today.
            </p>
            <p className="text-muted-foreground leading-relaxed mb-5">
              The Executive Council exists to ensure that definition is shaped by practitioners,
              not by software vendors. Council members provide the real-world validation that keeps
              CIOS grounded, the research inputs that keep our market intelligence relevant, and the
              peer relationships that make the membership itself valuable.
            </p>
            <p className="text-muted-foreground leading-relaxed">
              Current Council members represent organizations with combined annual federal contract
              portfolios exceeding $2.4B across defense, civilian, and intelligence community sectors.
            </p>
          </div>
          <div>
            <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground mb-5">Member Benefits</p>
            <h2 className="text-3xl font-bold tracking-tight mb-6">What membership provides.</h2>
            <div className="space-y-4">
              {MEMBER_BENEFITS.map((b) => (
                <div key={b.label} className="border border-border rounded-lg p-4 bg-card">
                  <div className="font-semibold text-sm mb-1.5">{b.label}</div>
                  <div className="text-xs text-muted-foreground leading-relaxed">{b.desc}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Eligibility */}
      <section className="border-t border-b border-border bg-card">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-20 sm:py-24">
          <div className="grid lg:grid-cols-2 gap-14 items-start">
            <div>
              <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground mb-5">Eligibility</p>
              <h2 className="text-3xl font-bold tracking-tight mb-6">Membership criteria.</h2>
              <p className="text-muted-foreground leading-relaxed mb-6">
                The Council is intentionally small and senior. We prioritize depth over breadth — a focused
                group of practitioners who can engage substantively on methodology, metrics, and market
                intelligence, rather than a broad networking forum.
              </p>
              <ul className="space-y-3">
                {ELIGIBILITY.map((e) => (
                  <li key={e} className="flex items-start gap-3 text-sm">
                    <div className="w-px h-4 bg-primary mt-0.5 shrink-0" />
                    <span className="text-muted-foreground">{e}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div className="border border-border rounded-xl p-8 bg-background">
              <div className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground mb-6">
                Request Membership Consideration
              </div>
              <p className="text-sm text-muted-foreground leading-relaxed mb-6">
                Membership consideration requests are reviewed quarterly. We respond to all requests within
                30 days of the review cycle close. Selection is based on eligibility criteria, sector diversity,
                and current Council composition.
              </p>
              <p className="text-sm text-muted-foreground leading-relaxed mb-8">
                There is no fee for Council membership. Members are expected to participate actively in
                research and roundtables, and to maintain a CIOS™ subscription at the Professional tier or higher.
              </p>
              <Link
                href="/auth/register"
                className="inline-flex w-full items-center justify-center gap-2 bg-primary text-primary-foreground px-6 py-3 rounded-md font-semibold hover:bg-primary/90 transition-colors text-sm"
              >
                Submit Membership Request <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
