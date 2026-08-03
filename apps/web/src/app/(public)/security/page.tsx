import type { Metadata } from "next";
import { ShieldCheck, Lock, Users, ScrollText, ServerCog, Ban } from "lucide-react";
import { buildPageMetadata } from "@/lib/metadata";
import { LegalPage } from "@/components/layout/legal-page";

export const metadata: Metadata = buildPageMetadata({
  title: "Security — CIOS™",
  description: "How CIOS™ isolates tenant data, encrypts information, and controls access.",
  path: "/security",
});

const LAST_UPDATED = "August 3, 2026";

const PRINCIPLES = [
  {
    icon: Users,
    title: "Per-Tenant Data Isolation",
    desc: "Every tenant-scoped database table enforces PostgreSQL row-level security, keyed off the authenticated tenant on every request. Documents indexed for AI search live in a separate vector-search collection per tenant — never a shared index.",
  },
  {
    icon: Lock,
    title: "Encryption",
    desc: "Data is encrypted in transit (TLS) between your browser, our API, and every backing service. Data at rest is encrypted, with tenant-derived keys used for sensitive stored content rather than one shared platform key.",
  },
  {
    icon: ShieldCheck,
    title: "Authentication & Access Control",
    desc: "Every request is authenticated with a signed JWT, validated on every call. Platform-operator (landlord) accounts are a fully separate identity space from tenant accounts, issued a different token scope, and cannot authenticate as a tenant user.",
  },
  {
    icon: ScrollText,
    title: "Audit Logging",
    desc: "Data access and mutation is written to an audit log, attributed to the acting user or platform admin. We deliberately keep tenant data content out of application logs — logs record identifiers, not the substance of what was accessed.",
  },
  {
    icon: Ban,
    title: "Prohibited Data Screening",
    desc: "The Service is not designed to receive Controlled Unclassified Information, classified information, or export-controlled (ITAR/EAR) technical data. Document uploads require an explicit per-document attestation, and are automatically screened for common CUI/classification banner markings before storage.",
  },
  {
    icon: ServerCog,
    title: "Vendor Risk",
    desc: "Third-party subprocessors (AI model providers, vector search, payment processing, email, hosting) are used only where necessary to deliver a specific feature, and receive only the data required for that feature — see our Privacy Policy for the current list.",
  },
];

export default function SecurityPage() {
  return (
    <LegalPage title="Security" lastUpdated={LAST_UPDATED}>
      <p>
        CIOS handles government-contracting business intelligence for organizations that compete
        for the same opportunities, often in the same market. Tenant isolation is not a
        nice-to-have here — it is the load-bearing requirement the platform is built around. This
        page describes the technical and operational controls currently in place.
      </p>

      <div className="grid sm:grid-cols-2 gap-4 my-8">
        {PRINCIPLES.map((p) => (
          <div key={p.title} className="border border-border rounded-lg p-5 bg-card">
            <div className="w-8 h-8 rounded-md bg-primary/10 flex items-center justify-center mb-3">
              <p.icon className="w-4 h-4 text-primary" />
            </div>
            <div className="font-semibold text-sm mb-1.5">{p.title}</div>
            <div className="text-xs text-muted-foreground leading-relaxed">{p.desc}</div>
          </div>
        ))}
      </div>

      <h2>What CIOS Is — and Is Not — Authorized to Handle</h2>
      <p>
        CIOS is a commercial SaaS platform for government contractors, not a government system of
        record. It derives intelligence from public procurement data (SAM.gov, USASpending.gov)
        and Customer-owned business inputs only. It is not built, accredited, or authorized to
        store or process Controlled Unclassified Information (CUI), classified national security
        information, or export-controlled (ITAR/EAR) technical data — see our{" "}
        <a href="/terms" className="underline hover:text-foreground">
          Terms of Service
        </a>{" "}
        for the full contractual restriction. If your organization has meaningful CUI handling
        requirements around your use of the platform, contact us before uploading such content —
        CIOS's current posture is risk-reduction (attestation plus automated marking detection),
        not a NIST SP 800-171 / CMMC compliance program.
      </p>

      <h2>Landlord / Tenant Separation</h2>
      <p>
        Platform operators (who administer the CIOS platform itself) are a distinct identity space
        from tenant users (who use CIOS to run their business). Landlord accounts are provisioned
        directly by us, not through self-service signup, are never tenant-scoped, and are not
        subject to tenant row-level security because they operate outside it entirely — every
        tenant-affecting action a platform operator takes (e.g. suspending an account) is written
        to an audit log attributed to that operator.
      </p>

      <h2>Reporting a Security Issue</h2>
      <p>
        If you believe you&rsquo;ve found a security vulnerability in CIOS, please report it to{" "}
        <a href="mailto:security@cios.ai" className="underline hover:text-foreground">
          security@cios.ai
        </a>
        . We ask that you give us a reasonable opportunity to investigate and address a report
        before any public disclosure, and that you avoid accessing or modifying data that isn&rsquo;t
        your own while testing.
      </p>

      <h2>Contact</h2>
      <p>
        General security questions can be sent to{" "}
        <a href="mailto:security@cios.ai" className="underline hover:text-foreground">
          security@cios.ai
        </a>
        .
      </p>
    </LegalPage>
  );
}
