"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { LogOut, ShieldAlert, Users, FileText } from "lucide-react";
import { cn } from "@/lib/utils";
import { clearAdminTokens, getAdminFullName, getAdminRole, isAdminAuthenticated } from "@/lib/admin-auth";

const NAV_ITEMS = [
  { href: "/admin", label: "Overview", icon: ShieldAlert },
  { href: "/admin/tenants", label: "Tenants", icon: Users },
  { href: "/admin/research", label: "Research Reports", icon: FileText },
];

export function AdminShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const isLoginPage = pathname === "/admin/login";

  useEffect(() => {
    if (!isLoginPage && !isAdminAuthenticated()) {
      router.replace("/admin/login");
    }
  }, [isLoginPage, router]);

  if (isLoginPage) {
    return <div className="min-h-screen flex items-center justify-center bg-background">{children}</div>;
  }

  return (
    <div className="flex h-screen bg-background overflow-hidden">
      <aside className="w-60 border-r border-border bg-card flex flex-col shrink-0">
        <div className="h-16 flex items-center px-5 border-b border-border">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-md bg-red-500/15 border border-red-500/30 flex items-center justify-center">
              <ShieldAlert className="w-4 h-4 text-red-500" />
            </div>
            <div>
              <div className="font-bold text-[13px] tracking-tight leading-tight">CIOS Landlord</div>
              <div className="text-[9px] text-muted-foreground leading-none tracking-[0.1em] uppercase mt-0.5">
                Platform Operations
              </div>
            </div>
          </div>
        </div>

        <nav className="flex-1 p-3 space-y-0.5">
          {NAV_ITEMS.map((item) => {
            const active = pathname === item.href || (item.href !== "/admin" && pathname.startsWith(item.href));
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors",
                  active ? "bg-red-500/15 text-red-500" : "text-muted-foreground hover:text-foreground hover:bg-secondary"
                )}
              >
                <item.icon className="w-4 h-4 shrink-0" />
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="p-3 border-t border-border space-y-2">
          <div className="px-3 text-xs">
            <div className="font-medium truncate">{getAdminFullName()}</div>
            <div className="text-muted-foreground uppercase tracking-wide text-[10px]">{getAdminRole()}</div>
          </div>
          <button
            onClick={() => { clearAdminTokens(); router.replace("/admin/login"); }}
            className="w-full flex items-center gap-2 px-3 py-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            <LogOut className="w-4 h-4" />
            Sign out
          </button>
        </div>
      </aside>

      <main className="flex-1 overflow-y-auto p-6">{children}</main>
    </div>
  );
}
