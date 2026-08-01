"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { isAuthenticated } from "@/lib/auth";
import { ArrowRight, Building2 } from "lucide-react";

const REVENUE_BANDS = ["<$1M", "$1M-$5M", "$5M-$25M", "$25M-$100M", "$100M+"];
const EMPLOYEE_BANDS = ["1-10", "11-50", "51-200", "201-1000", "1000+"];

export default function OnboardingPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    cage_code: "",
    duns_number: "",
    annual_revenue_band: "",
    employee_count_band: "",
    naics_codes: "",
    primary_jurisdictions: "",
  });

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/auth/login");
    }
  }, [router]);

  function splitList(s: string): string[] {
    return s ? s.split(",").map((x) => x.trim()).filter(Boolean) : [];
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      await api.completeOnboardingStep("company_profile", {
        cage_code: form.cage_code || undefined,
        duns_number: form.duns_number || undefined,
        annual_revenue_band: form.annual_revenue_band || undefined,
        employee_count_band: form.employee_count_band || undefined,
        primary_jurisdictions: splitList(form.primary_jurisdictions),
      });
      const naicsCodes = splitList(form.naics_codes);
      if (naicsCodes.length > 0) {
        await api.completeOnboardingStep("naics_codes", { naics_codes: naicsCodes });
      }
      await api.completeOnboarding();
      toast.success("Workspace set up");
      router.push("/dashboard");
    } catch {
      toast.error("Couldn't save your profile — you can finish this later from Settings");
      router.push("/dashboard");
    } finally {
      setLoading(false);
    }
  }

  async function handleSkip() {
    router.push("/dashboard");
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <div className="w-full max-w-lg bg-card border border-border rounded-xl p-8 shadow-lg">
        <div className="flex items-center gap-2 mb-1">
          <Building2 className="w-5 h-5 text-primary" />
          <h1 className="text-xl font-semibold">Tell us about your company</h1>
        </div>
        <p className="text-sm text-muted-foreground mb-6">
          This fills out your capture profile — you can change it anytime in Settings.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium mb-1.5 text-muted-foreground">CAGE Code</label>
              <input
                value={form.cage_code}
                onChange={(e) => setForm({ ...form, cage_code: e.target.value })}
                className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                placeholder="1A2B3"
              />
            </div>
            <div>
              <label className="block text-xs font-medium mb-1.5 text-muted-foreground">DUNS Number</label>
              <input
                value={form.duns_number}
                onChange={(e) => setForm({ ...form, duns_number: e.target.value })}
                className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                placeholder="123456789"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium mb-1.5 text-muted-foreground">Annual Revenue</label>
              <select
                value={form.annual_revenue_band}
                onChange={(e) => setForm({ ...form, annual_revenue_band: e.target.value })}
                className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
              >
                <option value="">Select…</option>
                {REVENUE_BANDS.map((b) => <option key={b} value={b}>{b}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium mb-1.5 text-muted-foreground">Employees</label>
              <select
                value={form.employee_count_band}
                onChange={(e) => setForm({ ...form, employee_count_band: e.target.value })}
                className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
              >
                <option value="">Select…</option>
                {EMPLOYEE_BANDS.map((b) => <option key={b} value={b}>{b}</option>)}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium mb-1.5 text-muted-foreground">
              Additional NAICS codes (comma separated)
            </label>
            <input
              value={form.naics_codes}
              onChange={(e) => setForm({ ...form, naics_codes: e.target.value })}
              className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
              placeholder="541511, 541611"
            />
          </div>

          <div>
            <label className="block text-xs font-medium mb-1.5 text-muted-foreground">
              Jurisdictions you pursue (comma separated)
            </label>
            <input
              value={form.primary_jurisdictions}
              onChange={(e) => setForm({ ...form, primary_jurisdictions: e.target.value })}
              className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
              placeholder="Federal, California, Texas"
            />
          </div>

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={handleSkip}
              className="flex-1 py-2.5 border border-border rounded-md text-sm hover:bg-secondary transition-colors"
            >
              Skip for now
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 flex items-center justify-center gap-2 py-2.5 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50"
            >
              {loading ? "Saving…" : "Continue to Dashboard"}
              {!loading && <ArrowRight className="w-4 h-4" />}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
