import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight, ArrowUpRight } from "lucide-react";
import { buildPageMetadata } from "@/lib/metadata";
import { organizationSchema } from "@/lib/jsonld";

export const metadata: Metadata = buildPageMetadata({
  title: "Uzima Amka — Intelligence Infrastructure for High-Stakes Decisions",
  description:
    "Uzima Amka builds precision intelligence tools for government contractors, trade professionals, and ministry leaders. Founded by a 40-year aerospace program management veteran.",
  path: "/",
});

const PILLARS = [
  {
    category: "Government Contracting",
    name: "CIOS™",
    full: "Contract Intelligence Operating System",
    desc: "The analytical infrastructure that transforms federal contracting from a pursuit exercise into a managed intelligence discipline. Competitive intelligence, bid/no-bid analysis, award simulation — before the solicitation drops.",
    href: "/platform",
    cta: "Explore the platform",
    internal: true,
    status: "live" as const,
  },
  {
    category: "Trades Operating System",
    name: "Fieldbook · AutoFlow · Leadflow",
    full: "The trade business that runs itself",
    desc: "Three interlocking tools for trade professionals. Quote at market rate. Automate the admin. Capture every lead the platform generates and return it as pre-qualified work.",
    href: "https://trades.uzimaamka.com",
    cta: "See the trades platform",
    internal: false,
    status: "soon" as const,
  },
  {
    category: "Ministerial Intelligence",
    name: "Unseen Layer™",
    full: "Textual intelligence for preachers",
    desc: "Nine narrative agents purpose-built for the craft of preaching. Pauline structure. Epistolary analysis. Literary framing. A research and writing intelligence system built by a preacher, for preachers.",
    href: "https://unseenlayer.uzimaamka.com",
    cta: "Learn more",
    internal: false,
    status: "live" as const,
  },
];

const PRINCIPLES = [
  {
    n: "01",
    title: "Built by practitioners, not observers",
    body: "Every tool Uzima Amka ships is built from the inside of the problem. CIOS was designed by a program manager with 40 years of federal acquisition experience. Unseen Layer was built by a preacher. The trades platform was built by someone who has operated a trades business. We do not build for markets. We build from experience.",
  },
  {
    n: "02",
    title: "Evidence over instinct",
    body: "The dominant mode of decision-making in government contracting, trades operations, and ministry practice is instinct and tribal knowledge. We build for the alternative — structured analysis, documented reasoning, reproducible decisions. Every recommendation carries its evidence chain.",
  },
  {
    n: "03",
    title: "Institutional rigor at individual scale",
    body: "The analytical infrastructure that primes and large enterprises use internally has never been accessible to the mid-market. Our entire purpose is to close that gap — delivering the same discipline that governs a $750M program portfolio to a 50-person firm making a $200K pursuit decision.",
  },
];

export default function HomePage() {
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(organizationSchema) }}
      />

      {/* Hero */}
      <section className="border-b border-border py-24 sm:py-32">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="max-w-4xl">
            <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-primary mb-6">
              Uzima Amka
            </p>
            <h1 className="text-5xl sm:text-6xl md:text-7xl font-bold tracking-tight leading-[1.04] mb-7">
              Intelligence infrastructure<br />
              for decisions that cannot<br />
              <span className="text-muted-foreground font-normal">afford to be wrong.</span>
            </h1>
            <p className="text-lg sm:text-xl text-muted-foreground leading-relaxed max-w-2xl mb-10">
              Founded by a 40-year aerospace program management veteran who spent three decades
              ensuring NASA and DoD programs met their objectives. Now building the analytical
              tools that bring the same discipline to government contracting, trades operations,
              and ministerial practice.
            </p>
            <div className="flex flex-wrap gap-4">
              <Link
                href="/platform"
                className="inline-flex items-center gap-2 bg-primary text-primary-foreground px-6 py-3 rounded-md font-semibold hover:bg-primary/90 transition-colors text-sm"
              >
                Explore CIOS™ <ArrowRight className="w-4 h-4" />
              </Link>
              <Link
                href="/about"
                className="inline-flex items-center gap-2 border border-border px-6 py-3 rounded-md font-semibold text-muted-foreground hover:text-foreground hover:border-foreground/30 transition-colors text-sm"
              >
                About the founder
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Founder */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-20 sm:py-28">
        <div className="grid lg:grid-cols-2 gap-14 items-start">
          <div>
            <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground mb-5">
              Why This Exists
            </p>
            <h2 className="text-3xl sm:text-4xl font-bold tracking-tight mb-6">
              Programs that cannot afford to fail require a different kind of discipline.
            </h2>
            <div className="space-y-5 text-muted-foreground leading-relaxed">
              <p>
                For 32 years at Raytheon, Larry Chase managed programs that operated at zero
                tolerance for failure — Space Shuttle, International Space Station, Artemis.
                Full P&L responsibility across NASA and DoD portfolios averaging $25M annually,
                consistently rated CPARS Excellent. Later, Senior Risk Manager for NASA&apos;s
                next-generation astronaut spacesuit program.
              </p>
              <p>
                The discipline that governed those programs — competitive analysis before
                commitment, structured risk identification, evidence-based decision frameworks,
                institutional knowledge that survives personnel changes — was simply not available
                to mid-market government contractors making the same category of decision at a
                fraction of the scale.
              </p>
              <p>
                Uzima Amka was founded to close that gap. Not with generic AI tools or rebranded
                CRMs — with the specific analytical infrastructure that has governed mission-critical
                program management for four decades, rebuilt for the firms that need it most.
              </p>
            </div>
          </div>

          {/* Career stats */}
          <div className="space-y-px">
            {[
              { value: "40+", label: "Years in aerospace program management", sub: "NASA, DoD, and commercial program leadership" },
              { value: "$750M+", label: "Program portfolio under management", sub: "P&L responsibility across five concurrent NASA/DoD contracts" },
              { value: "32 yrs", label: "Career at Raytheon Integrated Intelligence Systems", sub: "Houston Operations Business Area Executive" },
              { value: "4", label: "Human spaceflight programs", sub: "Space Shuttle · ISS · Artemis · xEVAS spacesuit development" },
              { value: "PMP", label: "Project Management Professional", sub: "PMI · Six Sigma · DAU Program and Cost Management certified" },
            ].map((s) => (
              <div key={s.label} className="border border-border bg-card rounded-lg p-5 flex gap-6 items-start">
                <div className="font-mono text-2xl font-bold text-primary shrink-0 w-20 tabular-nums leading-tight pt-0.5">
                  {s.value}
                </div>
                <div>
                  <div className="font-semibold text-sm mb-1">{s.label}</div>
                  <div className="text-xs text-muted-foreground">{s.sub}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* What we build */}
      <section className="border-t border-b border-border bg-card">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-20 sm:py-24">
          <div className="max-w-2xl mb-14">
            <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground mb-5">
              The Portfolio
            </p>
            <h2 className="text-3xl sm:text-4xl font-bold tracking-tight mb-5">
              Three domains. One discipline.
            </h2>
            <p className="text-muted-foreground leading-relaxed">
              Uzima Amka builds precision intelligence tools for professional domains where the
              cost of a wrong decision is measured in contracts lost, margins eroded, or
              opportunities permanently closed.
            </p>
          </div>

          <div className="grid lg:grid-cols-3 gap-6">
            {PILLARS.map((p) => (
              <div
                key={p.name}
                className="border border-border rounded-xl p-8 bg-background flex flex-col"
              >
                <div className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground mb-5">
                  {p.category}
                </div>
                <div className="font-bold text-xl mb-1">{p.name}</div>
                <div className="text-sm text-muted-foreground mb-5 italic">{p.full}</div>
                <p className="text-sm text-muted-foreground leading-relaxed flex-1 mb-8">
                  {p.desc}
                </p>
                <div className="flex items-center justify-between">
                  {p.status === "live" ? (
                    p.internal ? (
                      <Link
                        href={p.href}
                        className="inline-flex items-center gap-1.5 text-sm text-primary font-medium hover:text-primary/80 transition-colors"
                      >
                        {p.cta} <ArrowRight className="w-3.5 h-3.5" />
                      </Link>
                    ) : (
                      <a
                        href={p.href}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1.5 text-sm text-primary font-medium hover:text-primary/80 transition-colors"
                      >
                        {p.cta} <ArrowUpRight className="w-3.5 h-3.5" />
                      </a>
                    )
                  ) : (
                    <span className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground border border-border rounded px-2 py-1">
                      Coming soon
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Philosophy */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-20 sm:py-28">
        <div className="grid lg:grid-cols-2 gap-14 items-start">
          <div>
            <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground mb-5">
              The Name
            </p>
            <h2 className="text-3xl sm:text-4xl font-bold tracking-tight mb-6">
              Uzima Amka
            </h2>
            <p className="text-muted-foreground leading-relaxed mb-5">
              In Swahili, <em>uzima amka</em> means &ldquo;wake to life.&rdquo; It is the belief
              that every professional domain contains a latent capacity for transformation —
              waiting for the right tools, the right framework, and the right discipline to
              wake it up.
            </p>
            <p className="text-muted-foreground leading-relaxed">
              Government contractors who have accepted a 22% win rate as inevitable. Trade
              professionals who have absorbed the cost of under-priced jobs as a cost of doing
              business. Ministry leaders who carry the full research burden of weekly preaching
              alone. None of these are fixed conditions. They are the result of operating without
              the right intelligence infrastructure.
            </p>
          </div>

          <div className="space-y-4">
            {PRINCIPLES.map((p) => (
              <div key={p.n} className="border border-border rounded-lg p-6 bg-card">
                <div className="font-mono text-[10px] text-muted-foreground mb-3 uppercase tracking-widest">
                  {p.n}
                </div>
                <div className="font-semibold mb-3 text-sm">{p.title}</div>
                <div className="text-sm text-muted-foreground leading-relaxed">{p.body}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="border-t border-border bg-card">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-20 sm:py-24">
          <div className="grid lg:grid-cols-2 gap-14 items-center">
            <div>
              <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground mb-5">
                Start with CIOS™
              </p>
              <h2 className="text-3xl sm:text-4xl font-bold tracking-tight mb-5">
                The flagship platform is in active pilot.
              </h2>
              <p className="text-muted-foreground leading-relaxed mb-8">
                CIOS is currently in structured pilot with select government contracting organizations.
                Early access participants work directly with our intelligence team to configure
                the platform for their specific capture portfolio.
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
            <div className="border border-border rounded-xl p-8 bg-background">
              <div className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground mb-6">
                What early access includes
              </div>
              <ul className="space-y-4">
                {[
                  "Direct configuration support from the intelligence team",
                  "Custom integration with your existing capture pipeline",
                  "Dedicated onboarding across all six CIOS™ modules",
                  "Priority access to new module releases during pilot",
                  "No credit card required during the pilot period",
                  "Founding member pricing locked at close of pilot",
                ].map((item) => (
                  <li key={item} className="flex items-start gap-3 text-sm">
                    <div className="w-px h-4 bg-primary rounded-full mt-0.5 shrink-0" />
                    <span className="text-muted-foreground">{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
