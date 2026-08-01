"use client";

import { useState } from "react";
import Link from "next/link";
import { toast } from "sonner";
import { api } from "@/lib/api";

export default function ForgotPasswordPage() {
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [email, setEmail] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      await api.forgotPassword(email);
      // Always show the same success state regardless of whether the email
      // matched an account — the API itself never reveals that either.
      setSent(true);
    } catch {
      toast.error("Something went wrong — please try again.");
    } finally {
      setLoading(false);
    }
  }

  if (sent) {
    return (
      <div className="bg-card border border-border rounded-2xl p-8 shadow-xl text-center">
        <h2 className="text-xl font-semibold mb-2">Check your email</h2>
        <p className="text-sm text-muted-foreground">
          If an account exists for <span className="text-foreground">{email}</span>, we&apos;ve sent
          a link to reset your password. It expires in 1 hour.
        </p>
        <Link href="/auth/login" className="inline-block mt-6 text-sm text-primary hover:underline">
          Back to sign in
        </Link>
      </div>
    );
  }

  return (
    <div className="bg-card border border-border rounded-2xl p-8 shadow-xl">
      <h2 className="text-2xl font-bold mb-1">Reset your password</h2>
      <p className="text-sm text-muted-foreground mb-6">
        Enter your account email and we&apos;ll send you a reset link.
      </p>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-1.5">Email</label>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
            placeholder="you@company.com"
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full py-2.5 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? "Sending…" : "Send reset link"}
        </button>
      </form>

      <div className="mt-4 text-center text-sm text-muted-foreground">
        <Link href="/auth/login" className="text-primary hover:underline">
          Back to sign in
        </Link>
      </div>
    </div>
  );
}
