"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { saveTokens } from "@/lib/auth";

function AcceptInviteForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token") || "";
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({ full_name: "", password: "" });

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (form.password.length < 12) {
      toast.error("Password must be at least 12 characters");
      return;
    }
    if (!token) {
      toast.error("This invite link is missing its token");
      return;
    }
    setLoading(true);
    try {
      const data = await api.acceptInvite({
        token,
        full_name: form.full_name,
        password: form.password,
      });
      saveTokens(data);
      toast.success("You're in — welcome to the workspace.");
      router.push("/dashboard");
    } catch (err: unknown) {
      const message = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Could not accept this invite";
      toast.error(message);
    } finally {
      setLoading(false);
    }
  }

  if (!token) {
    return (
      <div className="bg-card border border-border rounded-xl p-8 shadow-lg text-center">
        <h2 className="text-xl font-semibold mb-2">Invalid invite link</h2>
        <p className="text-sm text-muted-foreground">
          This link is missing its invite token. Ask whoever invited you to send it again.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-card border border-border rounded-xl p-8 shadow-lg">
      <h2 className="text-xl font-semibold mb-1">Accept your invite</h2>
      <p className="text-sm text-muted-foreground mb-6">Set your name and password to join the workspace</p>

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
          {loading ? "Joining…" : "Join workspace"}
        </button>
      </form>
    </div>
  );
}

export default function AcceptInvitePage() {
  return (
    <Suspense fallback={null}>
      <AcceptInviteForm />
    </Suspense>
  );
}
