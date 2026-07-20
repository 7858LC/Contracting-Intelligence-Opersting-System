import Link from "next/link";

const PLATFORM_LINKS = [
  { href: "/platform", label: "CIOS™ Overview" },
  { href: "/radar", label: "Procurement Intelligence Radar™" },
  { href: "/diagnostics", label: "Procurement Intelligence Diagnostics™" },
  { href: "/pdq", label: "Pursuit Decision Quality™" },
  { href: "/simulation", label: "Award Simulation™" },
  { href: "/research", label: "Knowledge Vault™" },
];

const COMPANY_LINKS = [
  { href: "/about", label: "About Uzima Amka Ventures" },
  { href: "/executive-council", label: "Executive Council" },
  { href: "/research", label: "Research" },
  { href: "/pricing", label: "Pricing" },
];

const LEGAL_LINKS = [
  { href: "/privacy", label: "Privacy Policy" },
  { href: "/terms", label: "Terms of Service" },
  { href: "/security", label: "Security" },
];

export function PublicFooter() {
  return (
    <footer className="border-t border-border bg-card mt-auto">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-14">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-12">
          {/* Brand */}
          <div className="col-span-2 md:col-span-1">
            <div className="font-bold text-sm mb-0.5">Uzima Amka Ventures</div>
            <div className="text-xs text-primary mb-4">Procurement Intelligence™</div>
            <p className="text-xs text-muted-foreground leading-relaxed max-w-[200px]">
              The analytical infrastructure and decision frameworks for public sector contracting.
            </p>
          </div>

          {/* Platform */}
          <div>
            <div className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground mb-4">
              Platform
            </div>
            <ul className="space-y-2.5">
              {PLATFORM_LINKS.map((link) => (
                <li key={link.href}>
                  <Link
                    href={link.href}
                    className="text-xs text-muted-foreground hover:text-foreground transition-colors leading-snug"
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Company */}
          <div>
            <div className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground mb-4">
              Company
            </div>
            <ul className="space-y-2.5">
              {COMPANY_LINKS.map((link) => (
                <li key={link.href}>
                  <Link
                    href={link.href}
                    className="text-xs text-muted-foreground hover:text-foreground transition-colors"
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Legal */}
          <div>
            <div className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground mb-4">
              Legal
            </div>
            <ul className="space-y-2.5">
              {LEGAL_LINKS.map((link) => (
                <li key={link.href}>
                  <Link
                    href={link.href}
                    className="text-xs text-muted-foreground hover:text-foreground transition-colors"
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div className="border-t border-border pt-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="text-xs text-muted-foreground">
            © 2026 Uzima Amka Ventures. All rights reserved.
          </div>
          <div className="text-xs text-muted-foreground">
            Procurement Intelligence™ is a trademark of Uzima Amka Ventures.
          </div>
        </div>
      </div>
    </footer>
  );
}
