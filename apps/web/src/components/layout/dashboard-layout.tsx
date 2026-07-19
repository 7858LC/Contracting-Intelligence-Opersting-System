"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Award,
  BarChart3,
  BookOpen,
  Brain,
  Building2,
  ChevronDown,
  Home,
  LogOut,
  Radar,
  Settings,
  Shield,
  Target,
  Users,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { cn } from "@/lib/utils";
import { clearTokens, getAccessToken } from "@/lib/auth";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Executive Dashboard", icon: Home },
  { href: "/dashboard/radar", label: "Procurement Radar", icon: Radar, badge: "NEW" },
  { href: "/dashboard/opportunities", label: "Opportunities", icon: Target },
  { href: "/dashboard/bid-decisions", label: "Bid / No-Bid", icon: BarChart3 },
  { href: "/dashboard/award-simulator", label: "Award Simulator", icon: Award, badge: "FLAGSHIP" },
  { href: "/dashboard/knowledge-vault", label: "Knowledge Vault", icon: BookOpen },
  { href: "/dashboard/capabilities", label: "Capabilities & Gaps", icon: Brain },
  { href: "/dashboard/teaming", label: "Teaming", icon: Users },
  { href: "/dashboard/competitors", label: "Competitors", icon: Building2 },
  { href: "/dashboard/settings", label: "Settings", icon: Settings },
];

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
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center shrink-0">
              <Brain className="w-4.5 h-4.5 text-primary-foreground" />
            </div>
            <div>
              <div className="font-bold text-[15px] tracking-tight leading-tight">UzimaAmka</div>
              <div className="text-[10px] text-muted-foreground leading-none tracking-wide uppercase">Intelligence Platform</div>
            </div>
          </div>
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
                {item.badge && (
                  <span className={cn(
                    "text-[10px] font-bold px-1.5 py-0.5 rounded",
                    active ? "bg-primary-foreground/20 text-primary-foreground" : "bg-primary/10 text-primary"
                  )}>
                    {item.badge}
                  </span>
                )}
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
