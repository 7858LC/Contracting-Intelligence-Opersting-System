import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight, Check, Minus } from "lucide-react";
import { buildPageMetadata } from "@/lib/metadata";
import { breadcrumbSchema } from "@/lib/jsonld";

const BASE_URL = process.env.NEXT_PUBLIC_APP_URL || "https://uzimaamka.com";

export const metadata: Metadata = buildPageMetadata({
  title: "Pricing — Procurement Intelligence™ by Uzima Amka Ventures",
  description:
    "Four subscription tiers starting with Procurement Intelligence Radar™. Independently licensable modules with shared authentication, branding, and observability.",
  path: "/pricing",
});

type FeatureStatus = "yes" | "no" | string;

interface PricingTier {
  id: string;
  name: string;
  price: string;
  period: string;
  desc: string;
  cta: string;
  highlighted: boolean;
}

interface FeatureRow {
  label: string;
  category?: boolean;
  tiers: [FeatureStatus, FeatureStatus, FeatureStatus, FeatureStatus];
}

const TIERS: PricingTier[] = [
  {
    id: "radar",
    name: "Radar",
    price: "$399",
    period: "/month",
    desc: "Procurement Intelligence Radar™ standalone. Market surveillance and company intelligence without the full platform.",
    cta: "Start with Radar",
    highlighted: false,
  },
  {
    id: "professional",
    name: "Professional",
    price: "$1,299",
    period: "/month",
    desc: "Full intelligence suite for active capture teams. Radar, Diagnostics, PDQ™, Knowledge Vault, and Opportunities.",
    cta: "Start Professional",
    highlighted: true,
  },
  {
    id: "growth",
    name: "Growth",
    price: "$2,499",
    period: "/month",
    desc: "Expanded platform for organizations with mature capture programs and multiple active pursuits.",
    cta: "Start Growth",
    highlighted: false,
  },
  {
    id: "enterprise",
    name: "Enterprise",
    price: "Custom",
    period: "annual contract",
    desc: "Full platform with API access, bulk exports, SSO, custom integrations, and dedicated intelligence support.",
    cta: "Contact Sales",
    highlighted: false,
  },
];

const FEATURE_ROWS: FeatureRow[] = [
  { label: "Core Modules", category: true, tiers: ["", "", "", ""] },
  { label: "Procurement Intelligence Radar™", tiers: ["yes", "yes", "yes", "yes"] },
  { label: "Procurement Intelligence Diagnostics™", tiers: ["no", "yes", "yes", "yes"] },
  { label: "Pursuit Decision Quality™", tiers: ["no", "yes", "yes", "yes"] },
  { label: "Knowledge Vault™", tiers: ["no", "yes", "yes", "yes"] },
  { label: "Opportunities Module", tiers: ["no", "yes", "yes", "yes"] },
  { label: "Bid / No-Bid Engine", tiers: ["no", "yes", "yes", "yes"] },
  { label: "Award Simulation™", tiers: ["no", "no", "yes", "yes"] },
  { label: "Teaming Intelligence", tiers: ["no", "no", "yes", "yes"] },
  { label: "Competitive Intelligence", tiers: ["no", "no", "yes", "yes"] },
  { label: "Capabilities &amp; Gaps", tiers: ["no", "no", "yes", "yes"] },
  { label: "Executive Dashboard™", tiers: ["no", "no", "no", "yes"] },

  { label: "Radar — Usage Limits", category: true, tiers: ["", "", "", ""] },
  { label: "Tracked Companies", tiers: ["250", "1,000", "5,000", "Unlimited"] },
  { label: "Watchlist Slots", tiers: ["25", "100", "500", "Unlimited"] },
  { label: "Saved Searches", tiers: ["5", "25", "100", "Unlimited"] },
  { label: "AI Analysis Reports / month", tiers: ["10", "100", "500", "Unlimited"] },
  { label: "Bulk Scan Jobs / month", tiers: ["2", "20", "100", "Unlimited"] },

  { label: "Platform", category: true, tiers: ["", "", "", ""] },
  { label: "User Seats", tiers: ["3", "10", "25", "Unlimited"] },
  { label: "API Access", tiers: ["no", "no", "no", "yes"] },
  { label: "Bulk Data Export", tiers: ["no", "no", "no", "yes"] },
  { label: "SSO / SAML", tiers: ["no", "no", "no", "yes"] },
  { label: "Customer-Owned Encryption Keys", tiers: ["no", "no", "no", "yes"] },
  { label: "Custom Integrations", tiers: ["no", "no", "no", "yes"] },
  { label: "Dedicated Intelligence Analyst", tiers: ["no", "no", "no", "yes"] },
  { label: "SLA", tiers: ["no", "no", "99.5%", "99.9%"] },
];

function StatusCell({ value }: { value: FeatureStatus }) {
  if (value === "yes") return <Check className="w-4 h-4 text-primary mx-auto" aria-label="Included" />;
  if (value === "no") return <Minus className="w-4 h-4 text-muted-foreground/40 mx-auto" aria-label="Not included" />;
  if (value === "") return null;
  return <span className="font-mono text-xs text-muted-foreground">{value}</span>;
}

export default function PricingPage() {
  const crumbs = breadcrumbSchema([
    { name: "Home", url: BASE_URL },
    { name: "Pricing", url: `${BASE_URL}/pricing` },
  ]);

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(crumbs) }}
      />

      {/* Hero */}
      <section className="border-b border-border py-20 sm:py-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 text-center">
          <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground mb-5">
            Subscription Tiers
          </p>
          <h1 className="text-4xl sm:text-5xl font-bold tracking-tight mb-5">
            Start where you are.<br />Scale to where you need to be.
          </h1>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Every tier begins with Procurement Intelligence Radar™. Add modules as your intelligence
            program matures. All plans include shared authentication, branding, and observability.
          </p>
        </div>
      </section>

      {/* Tier cards */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-16">
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {TIERS.map((tier) => (
            <div
              key={tier.id}
              className={`border rounded-xl p-6 flex flex-col ${
                tier.highlighted
                  ? "border-primary bg-primary/5"
                  : "border-border bg-card"
              }`}
            >
              {tier.highlighted && (
                <div className="text-[10px] font-mono uppercase tracking-widest text-primary mb-4">
                  Most Popular
                </div>
              )}
              <div className="font-semibold text-sm text-muted-foreground mb-1">{tier.name}</div>
              <div className="flex items-baseline gap-1 mb-1">
                <span className="text-3xl font-bold">{tier.price}</span>
                <span className="text-sm text-muted-foreground">{tier.period}</span>
              </div>
              <p className="text-xs text-muted-foreground leading-relaxed mt-3 mb-6 flex-1">
                {tier.desc}
              </p>
              <Link
                href="/auth/register"
                className={`block text-center text-sm font-semibold py-2.5 rounded-md transition-colors ${
                  tier.highlighted
                    ? "bg-primary text-primary-foreground hover:bg-primary/90"
                    : "border border-border hover:bg-secondary text-foreground"
                }`}
              >
                {tier.cta}
              </Link>
            </div>
          ))}
        </div>
      </section>

      {/* Feature comparison table */}
      <section className="border-t border-border bg-card">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-16">
          <h2 className="text-2xl font-bold tracking-tight mb-10">Full Feature Comparison</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm min-w-[640px]">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left pb-4 pr-4 w-[40%] text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Feature
                  </th>
                  {TIERS.map((t) => (
                    <th key={t.id} className="text-center pb-4 px-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      {t.name}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {FEATURE_ROWS.map((row, i) => {
                  if (row.category) {
                    return (
                      <tr key={i} className="bg-background">
                        <td
                          colSpan={5}
                          className="pt-6 pb-2 px-2 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground"
                          dangerouslySetInnerHTML={{ __html: row.label }}
                        />
                      </tr>
                    );
                  }
                  return (
                    <tr key={i} className="border-b border-border/50 hover:bg-secondary/30 transition-colors">
                      <td className="py-3 pr-4 text-sm text-muted-foreground" dangerouslySetInnerHTML={{ __html: row.label }} />
                      {row.tiers.map((val, ti) => (
                        <td key={ti} className="py-3 px-2 text-center">
                          <StatusCell value={val} />
                        </td>
                      ))}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-20 sm:py-24">
        <div className="max-w-2xl mb-12">
          <h2 className="text-3xl font-bold tracking-tight mb-3">Frequently Asked Questions</h2>
        </div>
        <div className="max-w-2xl space-y-8">
          {[
            {
              q: "Can I start with Radar and upgrade later?",
              a: "Yes. Radar is designed as the entry point. All company data, signal history, watchlists, and AI analyses carry forward when you upgrade. There is no migration required.",
            },
            {
              q: "Is annual billing required?",
              a: "Month-to-month billing is available for Radar, Professional, and Growth. Enterprise subscriptions are annual contracts. Annual prepay for other tiers is available at a 15% discount.",
            },
            {
              q: "How does the Early Access Program work?",
              a: "Early access participants work directly with our intelligence team to configure the platform for their specific capture portfolio. Pricing during the pilot is at a preferred rate. Early access is limited to select organizations.",
            },
            {
              q: "What happens to my data if I cancel?",
              a: "You retain full data export rights for 90 days following cancellation. After 90 days, tenant data is permanently deleted from all systems including vector databases.",
            },
          ].map(({ q, a }) => (
            <div key={q}>
              <div className="font-semibold mb-2">{q}</div>
              <div className="text-sm text-muted-foreground leading-relaxed">{a}</div>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="border-t border-border bg-card">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-16">
          <div className="max-w-xl">
            <h2 className="text-2xl font-bold tracking-tight mb-3">
              Not sure where to start?
            </h2>
            <p className="text-muted-foreground leading-relaxed mb-6 text-sm">
              Most organizations begin with the Radar subscription to establish a market intelligence
              baseline before committing to the full platform. Contact us if you want help selecting
              the right tier for your capture program.
            </p>
            <Link
              href="/auth/register"
              className="inline-flex items-center gap-2 bg-primary text-primary-foreground px-6 py-3 rounded-md font-semibold hover:bg-primary/90 transition-colors text-sm"
            >
              Request Early Access <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
