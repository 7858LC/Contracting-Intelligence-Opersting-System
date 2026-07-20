"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, X } from "lucide-react";
import { cn } from "@/lib/utils";

const NAV_LINKS = [
  { href: "/", label: "Home" },
  { href: "/platform", label: "Platform" },
  { href: "/radar", label: "Radar" },
  { href: "/diagnostics", label: "Diagnostics" },
  { href: "/pdq", label: "PDQ™" },
  { href: "/simulation", label: "Simulation" },
  { href: "/research", label: "Research" },
  { href: "/executive-council", label: "Executive Council" },
  { href: "/pricing", label: "Pricing" },
  { href: "/about", label: "About" },
  { href: "/#ventures", label: "Ventures" },
];

export function PublicNav() {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();

  const isActive = (href: string) =>
    href === "/" ? pathname === "/" : pathname.startsWith(href);

  return (
    <header className="sticky top-0 z-50 border-b border-border/60 bg-background/90 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-3 shrink-0">
          <svg viewBox="0 0 28 28" fill="none" className="w-7 h-7 shrink-0" aria-hidden="true">
            <rect width="28" height="28" rx="6" fill="hsl(162,72%,36%)" />
            <circle cx="14" cy="15" r="8.5" stroke="white" strokeWidth="1" strokeOpacity="0.25" />
            <circle cx="14" cy="15" r="5.5" stroke="white" strokeWidth="1" strokeOpacity="0.4" />
            <circle cx="14" cy="15" r="2.5" stroke="white" strokeWidth="1" strokeOpacity="0.6" />
            <line x1="14" y1="6.5" x2="14" y2="15" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeOpacity="0.9" />
            <circle cx="18.5" cy="9.5" r="1.5" fill="hsl(38,95%,52%)" />
          </svg>
          <div className="leading-none">
            <div className="font-bold text-[14px] tracking-tight">Uzima Amka</div>
            <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-[0.12em] mt-0.5">
              Procurement Intelligence™
            </div>
          </div>
        </Link>

        {/* Desktop nav — overflow scroll on medium screens */}
        <nav className="hidden lg:flex items-center gap-0.5 min-w-0 overflow-x-auto">
          {NAV_LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={cn(
                "whitespace-nowrap px-2.5 py-1.5 text-[13px] rounded-md transition-colors",
                isActive(link.href)
                  ? "text-foreground font-medium"
                  : "text-muted-foreground hover:text-foreground hover:bg-secondary"
              )}
            >
              {link.label}
            </Link>
          ))}
        </nav>

        {/* Right actions */}
        <div className="flex items-center gap-2 shrink-0">
          <Link
            href="/auth/login"
            className="hidden sm:inline-flex text-[13px] text-muted-foreground hover:text-foreground transition-colors border border-border px-3 py-1.5 rounded-md"
          >
            Login
          </Link>
          <Link
            href="/auth/register"
            className="hidden sm:inline-flex text-[13px] bg-primary text-primary-foreground px-3.5 py-1.5 rounded-md font-semibold hover:bg-primary/90 transition-colors"
          >
            Request Access
          </Link>
          <button
            className="lg:hidden p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
            onClick={() => setOpen(!open)}
            aria-label="Toggle menu"
          >
            {open ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      {open && (
        <div className="lg:hidden border-t border-border bg-background/97 backdrop-blur-sm">
          <nav className="max-w-7xl mx-auto px-4 sm:px-6 py-4 space-y-0.5">
            {NAV_LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setOpen(false)}
                className={cn(
                  "block px-3 py-2.5 text-sm rounded-md transition-colors",
                  isActive(link.href)
                    ? "bg-primary/10 text-primary font-medium"
                    : "text-muted-foreground hover:text-foreground hover:bg-secondary"
                )}
              >
                {link.label}
              </Link>
            ))}
            <div className="pt-4 border-t border-border flex gap-3 mt-2">
              <Link
                href="/auth/login"
                onClick={() => setOpen(false)}
                className="flex-1 text-center text-sm border border-border py-2.5 rounded-md text-muted-foreground hover:text-foreground transition-colors"
              >
                Login
              </Link>
              <Link
                href="/auth/register"
                onClick={() => setOpen(false)}
                className="flex-1 text-center text-sm bg-primary text-primary-foreground py-2.5 rounded-md font-semibold hover:bg-primary/90 transition-colors"
              >
                Request Access
              </Link>
            </div>
          </nav>
        </div>
      )}
    </header>
  );
}
