"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { toast } from "sonner";
import { api } from "@/lib/api";

function ResetPasswordForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token") || "";
  const [loading, setLoading] = useState(false);
  const [password, setPassword] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (password.length < 12) {
      toast.error("Password must be at least 12 characters");
      return;
    }
    if (!token) {
      toast.error("This reset link is missing its token");
      return;
    }
    setLoading(true);
    try {
      await api.resetPassword({ token, new_password: password });
      toast.success("Password updated — sign in with your new password.");
      router.push("/auth/login");
    } catch (err: unknown) {
      const message = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Could not reset your password";
      toast.error(message);
    } finally {
      setLoading(false);
    }
  }

  if (!token) {
    return (
      <div className="bg-card border border-border rounded-xl p-8 shadow-lg text-center">
        <h2 className="text-xl font-semibold mb-2">Invalid reset link</h2>
        <p className="text-sm text-muted-foreground mb-4">
          This link is missing its reset token. Request a new one below.
        </p>
        <Link href="/auth/forgot-password" className="text-sm text-primary hover:underline">
          Request a new reset link
        </Link>
      </div>
    );
  }

  return (
    <div className="bg-card border border-border rounded-xl p-8 shadow-lg">
      <h2 className="text-xl font-semibold mb-1">Set a new password</h2>
      <p className="text-sm text-muted-foreground mb-6">Choose a new password for your account</p>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-1.5">New password</label>
          <input
            type="password"
            required
            minLength={12}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
            placeholder="Min 12 characters"
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full py-2.5 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? "Updating…" : "Update password"}
        </button>
      </form>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={null}>
      <ResetPasswordForm />
    </Suspense>
  );
}
