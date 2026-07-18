import Link from "next/link";
import { ArrowRight, Award, BarChart3, Brain, Lock, Shield, Zap } from "lucide-react";

export const metadata = { title: "UzimaAmka — Procurement Intelligence Platform" };

export default function MarketingPage() {
  return (
    <div className="min-h-screen bg-background">
      {/* Navigation */}
      <nav className="border-b border-border/50 backdrop-blur sticky top-0 z-50 bg-background/80">
        <div className="max-w-7xl mx-auto px-6 flex items-center justify-between h-16">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
              <Brain className="w-5 h-5 text-primary-foreground" />
            </div>
            <span className="font-bold text-xl tracking-tight">UzimaAmka</span>
          </div>
          <div className="hidden md:flex items-center gap-8 text-sm text-muted-foreground">
            <a href="#platform" className="hover:text-foreground transition-colors">Platform</a>
            <a href="#simulator" className="hover:text-foreground transition-colors">Award Simulator</a>
            <a href="#security" className="hover:text-foreground transition-colors">Security</a>
            <a href="#pricing" className="hover:text-foreground transition-colors">Pricing</a>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/auth/login" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
              Sign in
            </Link>
            <Link
              href="/auth/register"
              className="bg-primary text-primary-foreground px-4 py-2 rounded-md text-sm font-medium hover:bg-primary/90 transition-colors"
            >
              Start Free Trial
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative overflow-hidden bg-[#060d1a] text-white">
        <div
          className="absolute inset-0 opacity-[0.05]"
          style={{
            backgroundImage: "linear-gradient(#fff 1px,transparent 1px),linear-gradient(90deg,#fff 1px,transparent 1px)",
            backgroundSize: "56px 56px",
          }}
        />
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-primary/20 rounded-full blur-3xl pointer-events-none" />
        <div className="relative max-w-7xl mx-auto px-6 pt-28 pb-24 text-center">
          <div className="inline-flex items-center gap-2 border border-primary/30 bg-primary/10 text-primary px-4 py-1.5 rounded-full text-sm font-medium mb-8">
            <Zap className="w-3.5 h-3.5" />
            The Bloomberg Terminal of Procurement
          </div>
          <h1 className="text-5xl md:text-[4.5rem] font-bold tracking-tight mb-6 max-w-4xl mx-auto leading-[1.08]">
            Win more contracts<br />
            <span className="text-primary">before the proposal.</span>
          </h1>
          <p className="text-lg text-white/60 max-w-2xl mx-auto mb-10 leading-relaxed">
            UzimaAmka gives government contractors an intelligence advantage — automated opportunity analysis,
            award simulation, and AI-powered capture strategy in one platform.
          </p>
          <div className="flex items-center justify-center gap-4 flex-wrap">
            <Link
              href="/auth/register"
              className="bg-primary text-white px-8 py-3.5 rounded-xl font-semibold hover:bg-primary/90 transition-all shadow-lg shadow-primary/30 flex items-center gap-2"
            >
              Start Free Trial <ArrowRight className="w-4 h-4" />
            </Link>
            <a
              href="#simulator"
              className="border border-white/20 bg-white/5 text-white px-8 py-3.5 rounded-xl font-semibold hover:bg-white/10 transition-colors backdrop-blur-sm"
            >
              See Award Simulator
            </a>
          </div>
          <p className="text-white/30 text-sm mt-5">No credit card required · 14-day free trial</p>
        </div>
      </section>

      {/* Stats */}
      <section className="border-y border-border bg-card">
        <div className="max-w-7xl mx-auto px-6 py-12 grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
          {[
            { value: "15+", label: "Intelligence Modules" },
            { value: "9+", label: "AI Director Agents" },
            { value: "5+", label: "Procurement Rule Packs" },
            { value: "SOC 2", label: "Ready Architecture" },
          ].map((stat) => (
            <div key={stat.label}>
              <div className="text-4xl font-bold text-primary mb-1">{stat.value}</div>
              <div className="text-sm text-muted-foreground">{stat.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Modules */}
      <section id="platform" className="max-w-7xl mx-auto px-6 py-24">
        <div className="text-center mb-16">
          <h2 className="text-4xl font-bold mb-4">Complete Procurement Intelligence</h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            15 integrated modules, a hierarchical AI orchestration system, and your own private Knowledge Vault.
          </p>
        </div>
        <div className="grid md:grid-cols-3 gap-6">
          {MODULES.map((mod) => (
            <div key={mod.title} className="border border-border rounded-xl p-6 bg-card hover:border-primary/50 transition-colors">
              <div className="w-10 h-10 bg-primary/10 rounded-lg flex items-center justify-center mb-4">
                <mod.icon className="w-5 h-5 text-primary" />
              </div>
              <div className="text-xs font-mono text-muted-foreground mb-2">MODULE {mod.number}</div>
              <h3 className="font-semibold text-lg mb-2">{mod.title}</h3>
              <p className="text-sm text-muted-foreground">{mod.description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Award Simulator */}
      <section id="simulator" className="bg-card border-y border-border">
        <div className="max-w-7xl mx-auto px-6 py-24">
          <div className="grid md:grid-cols-2 gap-16 items-center">
            <div>
              <div className="text-xs font-mono text-primary mb-4">FLAGSHIP FEATURE</div>
              <h2 className="text-4xl font-bold mb-6">Award Simulator</h2>
              <p className="text-lg text-muted-foreground mb-8">
                Emulates government source selection evaluation before you submit. Identify
                weaknesses, deficiencies, and improvement opportunities — the same way
                government evaluators will.
              </p>
              <ul className="space-y-3">
                {[
                  "FAR 15.305 / DFARS source selection simulation",
                  "DOD color/adjectival ratings",
                  "Red team commentary from AI evaluators",
                  "Weaknesses, significant weaknesses, and deficiencies",
                  "Award probability with confidence score",
                  "Ranked improvement actions with expected score impact",
                ].map((item) => (
                  <li key={item} className="flex items-start gap-3 text-sm">
                    <div className="w-1.5 h-1.5 bg-primary rounded-full mt-2 shrink-0" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
            <div className="bg-background rounded-xl border border-border p-6 font-mono text-sm">
              <div className="text-xs text-muted-foreground mb-4">SIMULATION RESULT — SAMPLE</div>
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Technical Score</span>
                  <span className="text-emerald-400 font-medium">82 / Good</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Past Performance</span>
                  <span className="text-lime-400 font-medium">75 / Acceptable</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Price Competitiveness</span>
                  <span className="text-amber-400 font-medium">61 / Acceptable</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Compliance Score</span>
                  <span className="text-emerald-400 font-medium">94 / Outstanding</span>
                </div>
                <div className="border-t border-border my-3" />
                <div className="flex justify-between font-semibold">
                  <span>Award Probability</span>
                  <span className="text-primary text-lg">67%</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-muted-foreground">Gate Review</span>
                  <span className="text-amber-400">REVISE BEFORE SUBMIT</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Security */}
      <section id="security" className="max-w-7xl mx-auto px-6 py-24">
        <div className="text-center mb-16">
          <h2 className="text-4xl font-bold mb-4">Built for Government-Grade Security</h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Zero Trust architecture. SOC 2 ready. NIST 800-171 aligned. CMMC compatible.
          </p>
        </div>
        <div className="grid md:grid-cols-3 gap-6">
          {SECURITY_FEATURES.map((f) => (
            <div key={f.title} className="border border-border rounded-xl p-6 bg-card">
              <Shield className="w-8 h-8 text-primary mb-4" />
              <h3 className="font-semibold mb-2">{f.title}</h3>
              <p className="text-sm text-muted-foreground">{f.description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="bg-card border-y border-border">
        <div className="max-w-7xl mx-auto px-6 py-24">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold mb-4">Simple, Scalable Pricing</h2>
          </div>
          <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
            {PRICING_TIERS.map((tier) => (
              <div
                key={tier.name}
                className={`rounded-xl border p-8 ${
                  tier.highlighted
                    ? "border-primary bg-primary/5 relative"
                    : "border-border bg-background"
                }`}
              >
                {tier.highlighted && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-primary text-primary-foreground text-xs px-3 py-1 rounded-full font-medium">
                    Most Popular
                  </div>
                )}
                <div className="text-sm font-medium text-muted-foreground mb-2">{tier.name}</div>
                <div className="text-4xl font-bold mb-1">{tier.price}</div>
                <div className="text-sm text-muted-foreground mb-6">{tier.period}</div>
                <ul className="space-y-2 mb-8">
                  {tier.features.map((f) => (
                    <li key={f} className="flex items-center gap-2 text-sm">
                      <div className="w-4 h-4 text-primary">✓</div>
                      {f}
                    </li>
                  ))}
                </ul>
                <Link
                  href="/auth/register"
                  className={`w-full block text-center py-2 rounded-md text-sm font-medium transition-colors ${
                    tier.highlighted
                      ? "bg-primary text-primary-foreground hover:bg-primary/90"
                      : "border border-border hover:bg-secondary"
                  }`}
                >
                  {tier.cta}
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="max-w-7xl mx-auto px-6 py-12 flex items-center justify-between text-sm text-muted-foreground">
        <div className="flex items-center gap-2">
          <Brain className="w-4 h-4 text-primary" />
          <span>© 2026 UzimaAmka · <a href="https://uzimaAmka.com" className="hover:text-foreground transition-colors">uzimaAmka.com</a></span>
        </div>
        <div className="flex items-center gap-6">
          <a href="#" className="hover:text-foreground transition-colors">Privacy</a>
          <a href="#" className="hover:text-foreground transition-colors">Terms</a>
          <a href="#" className="hover:text-foreground transition-colors">Security</a>
        </div>
      </footer>
    </div>
  );
}

const MODULES = [
  { number: "01", title: "Opportunity Intelligence", description: "Automated ingestion and intelligence extraction from SAM.gov, state portals, and custom feeds.", icon: Zap },
  { number: "02", title: "Bid / No-Bid Engine", description: "Evidence-based bid decisions with weighted scoring across 8 strategic dimensions.", icon: BarChart3 },
  { number: "03", title: "Procurement Rule Engine", description: "Universal procurement concepts with jurisdiction-specific rule packs: FAR, DFARS, EU, World Bank.", icon: Shield },
  { number: "05", title: "Capability Gap Analysis", description: "Map requirements to capabilities. Identify gaps before they become disqualifiers.", icon: BarChart3 },
  { number: "06", title: "Past Performance Intelligence", description: "Smart relevance scoring of your past performance against new opportunities.", icon: Award },
  { number: "07", title: "Teaming Recommendation", description: "AI-powered teaming strategy based on capability gaps and relationship strength.", icon: Brain },
  { number: "08", title: "Competitive Intelligence", description: "Competitor profiling, incumbent analysis, and counter-strategy development.", icon: BarChart3 },
  { number: "12", title: "Award Probability Engine", description: "ML-powered win probability with full evidence trail and confidence intervals.", icon: Zap },
  { number: "13", title: "Award Simulator", description: "Emulate government source selection. Red-team your proposal before submission.", icon: Award },
];

const SECURITY_FEATURES = [
  { title: "Zero Trust Architecture", description: "Every request authenticated and authorized. No implicit trust. Row-level security on all data." },
  { title: "Private Knowledge Vault", description: "Your data is never shared. Per-tenant encrypted vector databases with customer-owned key option." },
  { title: "Immutable Audit Trail", description: "Every AI recommendation logged with evidence, model version, and human decision. Full reproducibility." },
  { title: "SOC 2 Ready", description: "Architecture designed for SOC 2 Type II certification from day one." },
  { title: "NIST 800-171 Aligned", description: "Security controls mapped to NIST 800-171 for defense contractor readiness." },
  { title: "FedRAMP Compatible", description: "Infrastructure patterns compatible with FedRAMP moderate authorization path." },
];

const PRICING_TIERS = [
  {
    name: "Starter",
    price: "$499",
    period: "/ month",
    highlighted: false,
    cta: "Start Free Trial",
    features: ["50 opportunities", "5 award simulations", "500MB knowledge vault", "3 seats", "Award Simulator", "Email support"],
  },
  {
    name: "Professional",
    price: "$1,499",
    period: "/ month",
    highlighted: true,
    cta: "Start Free Trial",
    features: ["500 opportunities", "50 award simulations", "5GB knowledge vault", "10 seats", "Competitive Intelligence", "API access", "Priority support"],
  },
  {
    name: "Enterprise",
    price: "Custom",
    period: "per year",
    highlighted: false,
    cta: "Contact Sales",
    features: ["Unlimited opportunities", "Unlimited simulations", "Unlimited storage", "Unlimited seats", "Customer-owned keys", "SSO / SAML", "Dedicated success manager"],
  },
];
