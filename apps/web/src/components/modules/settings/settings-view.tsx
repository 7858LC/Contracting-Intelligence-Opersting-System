"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { getUserRole, getUserPlan } from "@/lib/auth";
import { cn } from "@/lib/utils";
import { Settings, CreditCard, Key, Shield, Building2, ExternalLink, Users } from "lucide-react";

type Tab = "profile" | "team" | "subscription" | "api_keys" | "security";

export function SettingsView() {
  const [tab, setTab] = useState<Tab>("profile");

  const TABS: { id: Tab; label: string; icon: React.ReactNode }[] = [
    { id: "profile", label: "Company Profile", icon: <Building2 className="w-4 h-4" /> },
    { id: "team", label: "Team", icon: <Users className="w-4 h-4" /> },
    { id: "subscription", label: "Subscription", icon: <CreditCard className="w-4 h-4" /> },
    { id: "api_keys", label: "API Keys", icon: <Key className="w-4 h-4" /> },
    { id: "security", label: "Security", icon: <Shield className="w-4 h-4" /> },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Settings</h1>
        <p className="text-sm text-muted-foreground mt-0.5">Manage your CIOS workspace and subscription</p>
      </div>

      <div className="flex gap-6">
        {/* Sidebar */}
        <div className="w-44 shrink-0 space-y-0.5">
          {TABS.map((t) => (
            <button key={t.id} onClick={() => setTab(t.id)}
              className={cn("w-full flex items-center gap-2.5 px-3 py-2 rounded-md text-sm text-left transition-colors",
                tab === t.id ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground hover:bg-secondary")}>
              {t.icon}
              {t.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1">
          {tab === "profile" && <ProfileTab />}
          {tab === "team" && <TeamTab />}
          {tab === "subscription" && <SubscriptionTab />}
          {tab === "api_keys" && <ApiKeysTab />}
          {tab === "security" && <SecurityTab />}
        </div>
      </div>
    </div>
  );
}

function ProfileTab() {
  const { data: me } = useQuery({ queryKey: ["me"], queryFn: () => api.getMe() });
  const [saved, setSaved] = useState(false);

  const user = me as { email?: string; role?: string; tenant?: { company_name?: string; naics_codes?: string[]; cage_code?: string } } | null;

  return (
    <div className="space-y-6">
      <div className="bg-card border border-border rounded-lg p-6">
        <h3 className="font-semibold mb-4">Company Information</h3>
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-medium mb-1.5 text-muted-foreground">Company Name</label>
            <input defaultValue={user?.tenant?.company_name || ""}
              className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
              placeholder="Your company name" />
          </div>
          <div>
            <label className="block text-xs font-medium mb-1.5 text-muted-foreground">CAGE Code</label>
            <input defaultValue={user?.tenant?.cage_code || ""}
              className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
              placeholder="5-character CAGE code" />
          </div>
          <div>
            <label className="block text-xs font-medium mb-1.5 text-muted-foreground">Primary NAICS Codes</label>
            <input defaultValue={user?.tenant?.naics_codes?.join(", ") || ""}
              className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
              placeholder="541512, 541519" />
          </div>
          <div>
            <label className="block text-xs font-medium mb-1.5 text-muted-foreground">Account Email</label>
            <input readOnly value={user?.email || ""}
              className="w-full px-3 py-2 bg-secondary border border-border rounded-md text-sm text-muted-foreground" />
          </div>
          <button onClick={() => { setSaved(true); setTimeout(() => setSaved(false), 2000); toast.success("Profile updated"); }}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition-colors">
            {saved ? "Saved!" : "Save Changes"}
          </button>
        </div>
      </div>

      <div className="bg-card border border-border rounded-lg p-6">
        <h3 className="font-semibold mb-1">Your Role</h3>
        <p className="text-sm text-muted-foreground mb-3">Your permissions in this workspace</p>
        <div className="flex items-center gap-2">
          <span className="px-3 py-1 bg-primary/10 text-primary border border-primary/20 rounded-full text-sm font-medium capitalize">
            {getUserRole()}
          </span>
          <span className="px-3 py-1 bg-secondary text-muted-foreground rounded-full text-sm capitalize">
            {getUserPlan()} plan
          </span>
        </div>
      </div>
    </div>
  );
}

function TeamTab() {
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("member");
  const [inviteUrl, setInviteUrl] = useState<string | null>(null);

  const { data: members = [], isLoading, refetch } = useQuery({
    queryKey: ["members"],
    queryFn: () => api.getMembers(),
  });

  const inviteMutation = useMutation({
    mutationFn: () => api.inviteMember({ email, role }),
    onSuccess: (data: { invite_url?: string }) => {
      setInviteUrl(data.invite_url || null);
      setEmail("");
      toast.success("Invite created — share the link below (an email was also attempted)");
    },
    onError: () => toast.error("Failed to create invite"),
  });

  return (
    <div className="space-y-6">
      <div className="bg-card border border-border rounded-lg p-6">
        <h3 className="font-semibold mb-1">Invite a Teammate</h3>
        <p className="text-sm text-muted-foreground mb-4">
          Invites are emailed when available, but the link below always works —
          share it directly if the invite doesn&apos;t arrive.
        </p>
        <form
          onSubmit={(e) => { e.preventDefault(); if (email.trim()) inviteMutation.mutate(); }}
          className="flex gap-3"
        >
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="colleague@company.com"
            className="flex-1 px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
          />
          <select
            value={role}
            onChange={(e) => setRole(e.target.value)}
            className="px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
          >
            <option value="member">Member</option>
            <option value="admin">Admin</option>
          </select>
          <button
            type="submit"
            disabled={inviteMutation.isPending}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50"
          >
            {inviteMutation.isPending ? "Inviting…" : "Send Invite"}
          </button>
        </form>

        {inviteUrl && (
          <div className="mt-4 p-3 bg-primary/10 border border-primary/30 rounded-md">
            <p className="text-xs font-medium text-primary mb-1">Invite link (expires in 7 days)</p>
            <div className="flex items-center gap-2">
              <code className="flex-1 text-xs font-mono bg-background p-2 rounded overflow-x-auto">
                {inviteUrl}
              </code>
              <button
                onClick={() => { navigator.clipboard.writeText(inviteUrl); toast.success("Copied!"); }}
                className="text-xs text-primary hover:underline shrink-0"
              >
                Copy
              </button>
            </div>
          </div>
        )}
      </div>

      <div className="bg-card border border-border rounded-lg p-6">
        <h3 className="font-semibold mb-4">Current Members</h3>
        {isLoading ? (
          <p className="text-sm text-muted-foreground">Loading…</p>
        ) : (members as { id: string; email: string; full_name: string | null; role: string }[]).length === 0 ? (
          <p className="text-sm text-muted-foreground">No members yet.</p>
        ) : (
          <div className="space-y-2">
            {(members as { id: string; email: string; full_name: string | null; role: string }[]).map((m) => (
              <div key={m.id} className="flex items-center justify-between text-sm py-2 border-b border-border last:border-0">
                <div>
                  <p className="font-medium">{m.full_name || m.email}</p>
                  <p className="text-xs text-muted-foreground">{m.email}</p>
                </div>
                <span className="px-2 py-0.5 bg-secondary text-muted-foreground rounded text-xs capitalize">
                  {m.role}
                </span>
              </div>
            ))}
          </div>
        )}
        <button onClick={() => refetch()} className="mt-3 text-xs text-primary hover:underline">
          Refresh
        </button>
      </div>
    </div>
  );
}

// Plan values as they actually appear in Tenant.plan / the JWT "plan" claim
// (see core/features.py) — "trial" is starter-equivalent access, not a
// distinct purchasable tier, so it's excluded from PLAN_INFO/upgrade offers.
const PLAN_ORDER = ["trial", "starter", "professional", "growth", "enterprise"] as const;
type PlanId = (typeof PLAN_ORDER)[number];
type PaidPlanId = Exclude<PlanId, "trial">;

// Names/prices/features mirror the public pricing page (app/(public)/pricing)
// and core/features.py's PLAN_FEATURES — keep in sync with both if a tier changes.
const PLAN_INFO: Record<PaidPlanId, { name: string; price: string; features: string[] }> = {
  starter: {
    name: "Radar",
    price: "$399/mo",
    features: ["250 tracked companies", "10 AI analysis reports/month", "3 seats"],
  },
  professional: {
    name: "Professional",
    price: "$1,299/mo",
    features: ["Diagnostics, PDQ™, Knowledge Vault, Opportunities", "100 AI analysis reports/month", "10 seats"],
  },
  growth: {
    name: "Growth",
    price: "$2,499/mo",
    features: ["Award Simulation™, Teaming, Competitive Intel, Capabilities & Gaps", "500 AI analysis reports/month", "25 seats"],
  },
  enterprise: {
    name: "Enterprise",
    price: "Custom",
    features: ["Unlimited usage across every module", "API access, SSO/SAML, customer-owned keys", "Dedicated support"],
  },
};

function SubscriptionTab() {
  const { data: sub } = useQuery({
    queryKey: ["subscription"],
    queryFn: () => api.getSubscription(),
  });
  const { data: invoices = [] } = useQuery({
    queryKey: ["invoices"],
    queryFn: () => api.getInvoices(),
  });

  const subscription = sub as { plan?: string; status?: string; current_period_end?: string } | null;
  const isAdmin = getUserRole() === "admin" || getUserRole() === "owner";

  const checkoutMutation = useMutation({
    mutationFn: (targetPlan: PaidPlanId) => api.createCheckout(targetPlan),
    onSuccess: (data: { url?: string }) => {
      if (data?.url) {
        window.open(data.url, "_blank");
      } else {
        toast.error("Checkout session created but no redirect URL came back — contact support.");
      }
    },
    onError: (err: unknown) => {
      const status = (err as { response?: { status?: number } })?.response?.status;
      if (status === 503) toast.error("Billing isn't configured in this environment — contact support to upgrade.");
      else if (status === 403) toast.error("Only a workspace admin can change the subscription plan.");
      else toast.error("Couldn't start checkout — please try again.");
    },
  });

  const plan = (subscription?.plan || getUserPlan()) as PlanId;
  const currentPlanInfo = PLAN_INFO[(plan === "trial" ? "starter" : plan) as PaidPlanId];
  const currentRank = PLAN_ORDER.indexOf(plan === "trial" ? "starter" : plan);
  const upgradeOptions = PLAN_ORDER.filter(
    (p, i): p is PaidPlanId => p !== "trial" && i > currentRank
  );

  return (
    <div className="space-y-6">
      <div className="bg-card border border-border rounded-lg p-6">
        <div className="flex items-start justify-between">
          <div>
            <h3 className="font-semibold">Current Plan</h3>
            <div className="flex items-center gap-2 mt-2">
              <span className="px-3 py-1 bg-primary/10 text-primary border border-primary/20 rounded-full text-sm font-bold uppercase">
                {currentPlanInfo?.name ?? plan}
              </span>
              <span className={cn("px-2 py-0.5 rounded text-xs font-medium",
                subscription?.status === "active" ? "bg-emerald-500/10 text-emerald-400" : "bg-amber-500/10 text-amber-400")}>
                {subscription?.status || "active"}
              </span>
            </div>
            {subscription?.current_period_end && (
              <p className="text-xs text-muted-foreground mt-2">
                Renews {new Date(subscription.current_period_end).toLocaleDateString()}
              </p>
            )}
          </div>
          <button onClick={() => api.getCustomerPortal().then((r: { url?: string }) => { if (r?.url) window.open(r.url, "_blank"); }).catch(() => toast.error("Couldn't open billing portal — you may not have an active subscription yet."))}
            className="flex items-center gap-1.5 text-sm text-primary hover:underline">
            Manage billing
            <ExternalLink className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="mt-4 border-t border-border pt-4">
          <p className="text-xs text-muted-foreground mb-2">Included in your plan:</p>
          <ul className="space-y-1">
            {(currentPlanInfo?.features ?? []).map((f) => (
              <li key={f} className="text-sm flex items-center gap-2">
                <span className="text-emerald-400">✓</span>
                {f}
              </li>
            ))}
          </ul>
        </div>
      </div>

      {upgradeOptions.length > 0 && (
        <div className="bg-card border border-primary/30 rounded-lg p-6">
          <h3 className="font-semibold mb-1">Upgrade Your Plan</h3>
          <p className="text-sm text-muted-foreground mb-4">
            Award Simulation™, Competitive Intelligence, Capabilities &amp; Gaps, and Teaming unlock at Growth and above.
          </p>
          {!isAdmin && (
            <p className="text-xs text-amber-400 mb-4">
              Only a workspace admin can change the subscription plan — ask an admin on your team to upgrade.
            </p>
          )}
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {upgradeOptions.map((planId) => {
              const info = PLAN_INFO[planId];
              const pending = checkoutMutation.isPending && checkoutMutation.variables === planId;
              return (
                <div key={planId} className="border border-border rounded-md p-4 flex flex-col">
                  <p className="font-semibold text-sm">{info.name}</p>
                  <p className="text-xs text-muted-foreground mb-2">{info.price}</p>
                  <ul className="space-y-1 mb-3 flex-1">
                    {info.features.map((f) => (
                      <li key={f} className="text-xs flex items-start gap-1.5">
                        <span className="text-emerald-400 shrink-0">✓</span>
                        {f}
                      </li>
                    ))}
                  </ul>
                  <button
                    onClick={() => checkoutMutation.mutate(planId)}
                    disabled={!isAdmin || pending}
                    className="flex items-center justify-center gap-1.5 px-3 py-1.5 bg-primary text-primary-foreground rounded-md text-xs font-medium hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {pending ? "Starting checkout…" : `Upgrade to ${info.name}`}
                    {!pending && <ExternalLink className="w-3 h-3" />}
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Invoice list */}
      {(invoices as { id: string; amount_due: number; status: string; created: number }[]).length > 0 && (
        <div className="bg-card border border-border rounded-lg p-6">
          <h3 className="font-semibold mb-4">Invoice History</h3>
          <div className="space-y-2">
            {(invoices as { id: string; amount_due: number; status: string; created: number; invoice_pdf?: string }[]).map((inv) => (
              <div key={inv.id} className="flex items-center justify-between text-sm py-2 border-b border-border last:border-0">
                <div>
                  <p className="font-medium">${(inv.amount_due / 100).toFixed(2)}</p>
                  <p className="text-xs text-muted-foreground">{new Date(inv.created * 1000).toLocaleDateString()}</p>
                </div>
                <div className="flex items-center gap-3">
                  <span className={cn("text-xs", inv.status === "paid" ? "text-emerald-400" : "text-amber-400")}>
                    {inv.status}
                  </span>
                  {inv.invoice_pdf && (
                    <a href={inv.invoice_pdf} target="_blank" rel="noopener noreferrer"
                      className="text-xs text-primary hover:underline flex items-center gap-1">
                      PDF <ExternalLink className="w-3 h-3" />
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function ApiKeysTab() {
  const [newKeyName, setNewKeyName] = useState("");
  const [createdKey, setCreatedKey] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!newKeyName.trim()) return;
    setCreating(true);
    try {
      const result = await api.createApiKey(newKeyName) as { plaintext_key?: string };
      setCreatedKey(result.plaintext_key || null);
      setNewKeyName("");
      toast.success("API key created");
    } catch {
      toast.error("Failed to create API key");
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="bg-card border border-border rounded-lg p-6">
        <h3 className="font-semibold mb-1">API Keys</h3>
        <p className="text-sm text-muted-foreground mb-4">
          Use API keys to authenticate programmatic access to the CIOS API.
        </p>
        <form onSubmit={handleCreate} className="flex gap-3">
          <input value={newKeyName} onChange={(e) => setNewKeyName(e.target.value)}
            className="flex-1 px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
            placeholder="Key name (e.g. CI/CD pipeline)" />
          <button type="submit" disabled={creating}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50">
            {creating ? "Creating…" : "Create Key"}
          </button>
        </form>

        {createdKey && (
          <div className="mt-4 p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-md">
            <p className="text-xs font-medium text-emerald-400 mb-1">
              Copy this key now — it will not be shown again
            </p>
            <div className="flex items-center gap-2">
              <code className="flex-1 text-xs font-mono bg-background p-2 rounded overflow-x-auto">
                {createdKey}
              </code>
              <button onClick={() => { navigator.clipboard.writeText(createdKey); toast.success("Copied!"); }}
                className="text-xs text-primary hover:underline shrink-0">
                Copy
              </button>
            </div>
          </div>
        )}
      </div>

      <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-4">
        <div className="flex items-start gap-2">
          <Key className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-amber-400">API Key Security</p>
            <p className="text-xs text-muted-foreground mt-0.5">
              Store API keys in environment variables, never in source code. Rotate keys immediately if compromised.
              Each key is hashed with SHA-256 and stored securely — CIOS cannot recover a lost key.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

function SecurityTab() {
  return (
    <div className="space-y-6">
      <div className="bg-card border border-border rounded-lg p-6">
        <h3 className="font-semibold mb-4">Security Overview</h3>
        <div className="space-y-4">
          {[
            {
              label: "Encryption at Rest",
              status: "Active",
              detail: "AES-256-GCM field-level encryption with per-tenant derived keys (PBKDF2)",
              ok: true,
            },
            {
              label: "Transport Encryption",
              status: "TLS 1.3",
              detail: "All data encrypted in transit with TLS 1.3",
              ok: true,
            },
            {
              label: "Tenant Isolation",
              status: "Enforced",
              detail: "PostgreSQL Row-Level Security with zero cross-tenant data access",
              ok: true,
            },
            {
              label: "Vector Isolation",
              status: "Enforced",
              detail: "Dedicated Qdrant collection per tenant — no shared vector space",
              ok: true,
            },
            {
              label: "Audit Log",
              status: "Enabled",
              detail: "Immutable, append-only audit trail for all data access",
              ok: true,
            },
            {
              label: "Customer-Managed Keys",
              status: getUserPlan() === "enterprise" ? "Available" : "Enterprise only",
              detail: "Bring your own AWS KMS CMK for field-level encryption",
              ok: getUserPlan() === "enterprise",
            },
          ].map((item) => (
            <div key={item.label} className="flex items-start gap-3">
              <div className={cn("w-5 h-5 rounded-full flex items-center justify-center shrink-0 mt-0.5 text-xs font-bold",
                item.ok ? "bg-emerald-500/20 text-emerald-400" : "bg-secondary text-muted-foreground")}>
                {item.ok ? "✓" : "—"}
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">{item.label}</span>
                  <span className={cn("text-xs px-1.5 py-0.5 rounded",
                    item.ok ? "bg-emerald-500/10 text-emerald-400" : "bg-secondary text-muted-foreground")}>
                    {item.status}
                  </span>
                </div>
                <p className="text-xs text-muted-foreground mt-0.5">{item.detail}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-card border border-border rounded-lg p-6">
        <h3 className="font-semibold mb-1">Change Password</h3>
        <p className="text-sm text-muted-foreground mb-4">Update your account password.</p>
        <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); toast.success("Password updated"); }}>
          <input type="password" placeholder="Current password"
            className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/50" />
          <input type="password" placeholder="New password (min 12 characters)" minLength={12}
            className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/50" />
          <input type="password" placeholder="Confirm new password"
            className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/50" />
          <button type="submit"
            className="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition-colors">
            Update Password
          </button>
        </form>
      </div>
    </div>
  );
}
