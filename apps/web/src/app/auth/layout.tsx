import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Sign in — UzimaAmka",
};

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen flex">
      {/* Left brand panel */}
      <div className="hidden lg:flex lg:w-[52%] flex-col justify-between p-12 bg-[#0a1628] text-white relative overflow-hidden">
        {/* Subtle grid pattern */}
        <div
          className="absolute inset-0 opacity-[0.04]"
          style={{
            backgroundImage:
              "linear-gradient(#fff 1px, transparent 1px), linear-gradient(90deg, #fff 1px, transparent 1px)",
            backgroundSize: "48px 48px",
          }}
        />
        {/* Glow */}
        <div className="absolute top-1/3 -left-32 w-96 h-96 rounded-full bg-primary/20 blur-3xl pointer-events-none" />

        {/* Logo */}
        <div className="relative flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg flex items-center justify-center bg-primary/20 border border-primary/30">
            <svg className="w-5 h-5 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
          </div>
          <span className="font-semibold text-lg tracking-tight">UzimaAmka</span>
        </div>

        {/* Center copy */}
        <div className="relative max-w-sm">
          <div className="text-xs font-medium text-primary/80 tracking-widest uppercase mb-4">
            Procurement Intelligence Platform
          </div>
          <h2 className="text-4xl font-bold leading-tight mb-5 text-white">
            Win more contracts.<br />
            <span className="text-primary">Before the proposal.</span>
          </h2>
          <p className="text-white/60 text-sm leading-relaxed mb-10">
            UzimaAmka gives government contractors an unfair intelligence advantage — bid decisions,
            award simulation, competitive analysis, and knowledge management in one platform.
          </p>

          {/* Testimonial */}
          <div className="border border-white/10 rounded-xl p-5 bg-white/5 backdrop-blur-sm">
            <p className="text-white/80 text-sm leading-relaxed italic mb-3">
              "We went from a 22% win rate to 41% in two quarters. UzimaAmka showed us exactly why we were losing."
            </p>
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-full bg-primary/30 flex items-center justify-center text-xs font-bold text-primary">
                MK
              </div>
              <div>
                <div className="text-xs font-semibold text-white/90">Marcus K.</div>
                <div className="text-xs text-white/50">VP Capture, Federal Systems Integrator</div>
              </div>
            </div>
          </div>
        </div>

        {/* Stats row */}
        <div className="relative flex items-center gap-8 text-sm">
          {[["41%", "avg win rate lift"], ["9+", "AI director agents"], ["SOC 2", "ready"]].map(([val, label]) => (
            <div key={label}>
              <div className="font-bold text-white text-base">{val}</div>
              <div className="text-white/40 text-xs">{label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Right form panel */}
      <div className="flex-1 flex flex-col items-center justify-center p-8 bg-background">
        {/* Mobile logo */}
        <div className="lg:hidden mb-8 flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
            <svg className="w-4.5 h-4.5 text-primary-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
          </div>
          <span className="font-bold text-lg">UzimaAmka</span>
        </div>

        <div className="w-full max-w-sm">
          {children}
        </div>

        <p className="mt-8 text-xs text-muted-foreground text-center">
          © 2026 UzimaAmka · <a href="https://uzimaAmka.com" className="hover:text-foreground transition-colors">uzimaAmka.com</a>
        </p>
      </div>
    </div>
  );
}
