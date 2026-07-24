"use client";

import type { ComponentType } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Award,
  BarChart3,
  BookOpen,
  Brain,
  Building2,
  Crosshair,
  Home,
  LogOut,
  Radio,
  Settings,
  Shield,
  Target,
  Users,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { cn } from "@/lib/utils";
import { clearTokens, getAccessToken } from "@/lib/auth";
import {
  Feature,
  SubscriptionTier,
  hasFeature,
} from "@/lib/feature-flags";

// TODO: Replace with subscription tier from user profile API once endpoint is available.
// Currently defaults to Enterprise so no existing functionality is gated.
const ACTIVE_TIER: SubscriptionTier = SubscriptionTier.Enterprise;

interface NavItem {
  href: string;
  label: string;
  icon: ComponentType<{ className?: string }>;
  feature: Feature | null;
}

const ALL_NAV_ITEMS: NavItem[] = [
  { href: "/dashboard", label: "Executive Dashboard", icon: Home, feature: Feature.ExecutiveDashboard },
  { href: "/dashboard/radar", label: "Procurement Radar™", icon: Radio, feature: Feature.ProcurementIntelligenceRadar },
  { href: "/dashboard/winning-profile", label: "Winning Profile™", icon: Crosshair, feature: Feature.WinningProfileHypothesis },
  { href: "/dashboard/opportunities", label: "Opportunities", icon: Target, feature: Feature.Opportunities },
  { href: "/dashboard/bid-decisions", label: "Pursuit Decision Quality™", icon: BarChart3, feature: Feature.BidDecisions },
  { href: "/dashboard/award-simulator", label: "Award Simulation™", icon: Award, feature: Feature.AwardSimulation },
  { href: "/dashboard/knowledge-vault", label: "Knowledge Vault™", icon: BookOpen, feature: Feature.KnowledgeVault },
  { href: "/dashboard/capabilities", label: "Capabilities & Gaps", icon: Brain, feature: Feature.Capabilities },
  { href: "/dashboard/teaming", label: "Teaming", icon: Users, feature: Feature.Teaming },
  { href: "/dashboard/competitors", label: "Competitors", icon: Building2, feature: Feature.Competitors },
  { href: "/dashboard/settings", label: "Settings", icon: Settings, feature: null },
];

const NAV_ITEMS = ALL_NAV_ITEMS.filter(
  (item) => item.feature === null || hasFeature(ACTIVE_TIER, item.feature)
);

export function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    if (!getAccessToken()) {
      router.replace("/auth/login");
    }
  }, [router]);

  return (
    <div className="flex h-screen bg-background overflow-hidden">
      {/* Sidebar */}
      <aside className="w-64 border-r border-border bg-card flex flex-col shrink-0">
        {/* Logo */}
        <div className="h-16 flex items-center px-5 border-b border-border">
          <Link href="/" className="flex items-center gap-3">
            <svg viewBox="0 0 28 28" fill="none" className="w-7 h-7 shrink-0" aria-hidden="true">
              <rect width="28" height="28" rx="6" fill="hsl(162,72%,36%)" />
              <circle cx="14" cy="15" r="8.5" stroke="white" strokeWidth="1" strokeOpacity="0.25" />
              <circle cx="14" cy="15" r="5.5" stroke="white" strokeWidth="1" strokeOpacity="0.4" />
              <circle cx="14" cy="15" r="2.5" stroke="white" strokeWidth="1" strokeOpacity="0.6" />
              <line x1="14" y1="6.5" x2="14" y2="15" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeOpacity="0.9" />
              <circle cx="18.5" cy="9.5" r="1.5" fill="hsl(38,95%,52%)" />
            </svg>
            <div>
              <div className="font-bold text-[14px] tracking-tight leading-tight">CIOS™</div>
              <div className="text-[9px] text-muted-foreground leading-none tracking-[0.1em] uppercase mt-0.5">
                Procurement Intelligence™
              </div>
            </div>
          </Link>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-3 space-y-0.5 overflow-y-auto">
          {NAV_ITEMS.map((item) => {
            const active = pathname === item.href || (item.href !== "/dashboard" && pathname.startsWith(item.href));
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors",
                  active
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:text-foreground hover:bg-secondary"
                )}
              >
                <item.icon className="w-4 h-4 shrink-0" />
                <span className="flex-1">{item.label}</span>
              </Link>
            );
          })}
        </nav>

        {/* Security indicator */}
        <div className="p-3 border-t border-border">
          <div className="flex items-center gap-2 px-3 py-2 text-xs text-muted-foreground">
            <Shield className="w-3.5 h-3.5 text-emerald-500" />
            <span>Encrypted · Zero Trust</span>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Top bar */}
        <header className="h-16 border-b border-border bg-card px-6 flex items-center justify-between shrink-0">
          <div className="text-sm text-muted-foreground">
            {NAV_ITEMS.find((i) => pathname.startsWith(i.href) && (i.href !== "/dashboard" || pathname === "/dashboard"))?.label}
          </div>
          <button
            onClick={() => { clearTokens(); window.location.href = "/auth/login"; }}
            className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            <LogOut className="w-4 h-4" />
            Sign out
          </button>
        </header>

        {/* Page content */}
        <div className="flex-1 overflow-y-auto p-6">
          {children}
        </div>
      </main>
    </div>
  );
}
