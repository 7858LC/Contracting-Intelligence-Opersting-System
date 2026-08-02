"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { ShieldAlert } from "lucide-react";
import { adminApi } from "@/lib/admin-api";
import { saveAdminTokens } from "@/lib/admin-auth";
import { getRequestErrorMessage } from "@/lib/utils";

export default function AdminLoginPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({ email: "", password: "" });

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      const data = await adminApi.login(form.email, form.password);
      saveAdminTokens(data);
      router.push("/admin");
    } catch (err: unknown) {
      toast.error(getRequestErrorMessage(err, "Invalid credentials"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="w-full max-w-sm bg-card border border-border rounded-2xl p-8 shadow-xl">
      <div className="flex items-center gap-2.5 mb-1">
        <div className="w-8 h-8 rounded-md bg-red-500/15 border border-red-500/30 flex items-center justify-center">
          <ShieldAlert className="w-4 h-4 text-red-500" />
        </div>
        <h2 className="text-xl font-bold">Landlord Console</h2>
      </div>
      <p className="text-sm text-muted-foreground mb-6">
        Platform-operator access only — not a tenant login.
      </p>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-1.5">Email</label>
          <input
            type="email"
            required
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-red-500/50 focus:border-transparent"
            placeholder="ops@cios.ai"
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1.5">Password</label>
          <input
            type="password"
            required
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-red-500/50 focus:border-transparent"
            placeholder="••••••••"
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full py-2.5 bg-red-500 text-white rounded-md text-sm font-medium hover:bg-red-500/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </div>
  );
}
