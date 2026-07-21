"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { saveTokens } from "@/lib/auth";

const NAICS_CODES = [
  { value: "541330", label: "541330 – Engineering Services" },
  { value: "541512", label: "541512 – Computer Systems Design" },
  { value: "541519", label: "541519 – Other Computer-Related Services" },
  { value: "541611", label: "541611 – Management Consulting" },
  { value: "541690", label: "541690 – Other Scientific & Technical Consulting" },
  { value: "561210", label: "561210 – Facilities Support Services" },
  { value: "561320", label: "561320 – Temporary Staffing" },
  { value: "611430", label: "611430 – Professional Development & Training" },
  { value: "336411", label: "336411 – Aircraft Manufacturing" },
  { value: "332992", label: "332992 – Small Arms Ammunition Manufacturing" },
];

export default function RegisterPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    full_name: "",
    email: "",
    password: "",
    company_name: "",
    naics_code: "",
  });

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (form.password.length < 12) {
      toast.error("Password must be at least 12 characters");
      return;
    }
    setLoading(true);
    try {
      const data = await api.register({
        full_name: form.full_name,
        email: form.email,
        password: form.password,
        company_name: form.company_name,
        naics_codes: form.naics_code ? [form.naics_code] : [],
      });
      saveTokens(data);
      toast.success("Welcome to CIOS! Your workspace is ready.");
      router.push("/dashboard");
    } catch (err: unknown) {
      const message = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Registration failed";
      toast.error(message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="bg-card border border-border rounded-xl p-8 shadow-lg">
      <h2 className="text-xl font-semibold mb-1">Start your free trial</h2>
      <p className="text-sm text-muted-foreground mb-6">14 days free · No credit card required</p>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-1.5">Your full name</label>
          <input
            type="text"
            required
            value={form.full_name}
            onChange={(e) => setForm({ ...form, full_name: e.target.value })}
            className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
            placeholder="Jordan Rivera"
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1.5">Company name</label>
          <input
            type="text"
            required
            value={form.company_name}
            onChange={(e) => setForm({ ...form, company_name: e.target.value })}
            className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
            placeholder="Acme Government Solutions"
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1.5">Primary NAICS code</label>
          <select
            value={form.naics_code}
            onChange={(e) => setForm({ ...form, naics_code: e.target.value })}
            className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
          >
            <option value="">Select a code…</option>
            {NAICS_CODES.map((c) => (
              <option key={c.value} value={c.value}>{c.label}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium mb-1.5">Work email</label>
          <input
            type="email"
            required
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
            placeholder="you@company.com"
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1.5">Password</label>
          <input
            type="password"
            required
            minLength={12}
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
            placeholder="Min 12 characters"
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full py-2.5 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? "Creating workspace…" : "Create free account"}
        </button>
      </form>

      <p className="mt-4 text-xs text-center text-muted-foreground">
        By registering you agree to the{" "}
        <a href="#" className="underline">Terms of Service</a>{" "}
        and{" "}
        <a href="#" className="underline">Privacy Policy</a>.
      </p>

      <div className="mt-3 text-center text-sm text-muted-foreground">
        Already have an account?{" "}
        <Link href="/auth/login" className="text-primary hover:underline">
          Sign in
        </Link>
      </div>
    </div>
  );
}
