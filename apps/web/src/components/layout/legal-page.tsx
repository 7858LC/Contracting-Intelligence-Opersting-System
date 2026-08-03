import { AlertTriangle } from "lucide-react";

export function LegalPage({
  title,
  lastUpdated,
  children,
}: {
  title: string;
  lastUpdated: string;
  children: React.ReactNode;
}) {
  return (
    <section className="max-w-3xl mx-auto px-4 sm:px-6 py-16 sm:py-20">
      <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-primary mb-4">Legal</p>
      <h1 className="text-3xl sm:text-4xl font-bold tracking-tight mb-2">{title}</h1>
      <p className="text-sm text-muted-foreground mb-8">Last updated {lastUpdated}</p>

      <div className="flex gap-3 items-start rounded-lg border border-amber-500/30 bg-amber-500/5 px-4 py-3.5 mb-12">
        <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
        <p className="text-xs text-muted-foreground leading-relaxed">
          <span className="font-semibold text-foreground">Draft — pending legal review.</span> This
          page describes our current policy and platform practices in good faith, but has not yet
          been reviewed by outside counsel and is not a final, binding legal instrument. If you have
          questions before relying on it, contact{" "}
          <a href="mailto:legal@cios.ai" className="underline hover:text-foreground">
            legal@cios.ai
          </a>
          .
        </p>
      </div>

      <div className="prose-legal space-y-8 text-sm text-muted-foreground leading-relaxed [&_h2]:text-foreground [&_h2]:text-lg [&_h2]:font-semibold [&_h2]:tracking-tight [&_h2]:mb-3 [&_h3]:text-foreground [&_h3]:text-sm [&_h3]:font-semibold [&_h3]:mb-2 [&_p]:mb-3 [&_ul]:list-disc [&_ul]:pl-5 [&_ul]:space-y-1.5 [&_ul]:mb-3 [&_strong]:text-foreground [&_strong]:font-medium">
        {children}
      </div>
    </section>
  );
}
