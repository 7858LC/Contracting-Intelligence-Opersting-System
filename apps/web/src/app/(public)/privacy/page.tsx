import type { Metadata } from "next";
import { buildPageMetadata } from "@/lib/metadata";
import { LegalPage } from "@/components/layout/legal-page";

export const metadata: Metadata = buildPageMetadata({
  title: "Privacy Policy — CIOS™",
  description: "How Uzima Amka Ventures collects, uses, and protects data on the CIOS™ platform.",
  path: "/privacy",
});

const LAST_UPDATED = "August 3, 2026";

export default function PrivacyPage() {
  return (
    <LegalPage title="Privacy Policy" lastUpdated={LAST_UPDATED}>
      <p>
        This Privacy Policy describes how Uzima Amka Ventures (&ldquo;Company,&rdquo;
        &ldquo;we&rdquo;) collects, uses, and discloses information in connection with the CIOS™
        platform (the &ldquo;Service&rdquo;). It applies to Customer account data and to
        Customer&rsquo;s own end users who access the Service under a Customer account.
      </p>

      <h2>1. Information We Collect</h2>
      <h3>Account &amp; billing information</h3>
      <p>
        Name, work email, organization, and role, collected at registration; billing details
        (processed by our payment processor — we do not store full card numbers).
      </p>
      <h3>Customer content</h3>
      <p>
        Data Customer submits to the Service to use it — tracked companies, uploaded documents in
        the Knowledge Vault, competitive intelligence inputs, capture and proposal content, and
        similar business inputs (&ldquo;Customer Data&rdquo;). Customer Data is not sold, and is
        never shared with another tenant.
      </p>
      <h3>Usage &amp; log data</h3>
      <p>
        API request metadata, feature usage counts against plan limits, and audit-log entries
        (who did what, when) for security and support purposes. We deliberately avoid logging the
        contents of tenant data itself in application logs — only identifiers.
      </p>
      <h3>Public procurement data</h3>
      <p>
        The Service also aggregates data that is independently public — e.g. SAM.gov entity
        registrations and USASpending.gov award records — which is not personal data of Customer
        or its users.
      </p>

      <h2>2. How We Use Information</h2>
      <ul>
        <li>To provide, maintain, and secure the Service, including tenant-isolated storage;</li>
        <li>To generate AI-assisted analysis and recommendations Customer requests;</li>
        <li>To bill for subscriptions and enforce plan usage limits;</li>
        <li>To provide customer support and respond to inquiries; and</li>
        <li>
          To improve the Service — using aggregated, de-identified usage patterns, not the
          substance of Customer Data.
        </li>
      </ul>
      <p>
        We do not use Customer Data to train third-party foundation models, and we do not sell
        personal information.
      </p>

      <h2>3. Tenant Isolation</h2>
      <p>
        CIOS is built as a multi-tenant platform with per-tenant data isolation enforced at the
        database layer (PostgreSQL row-level security) and, for AI-searchable documents, a
        separate vector-search collection per tenant. One customer&rsquo;s data is never visible
        to, or searchable by, another customer&rsquo;s account.
      </p>

      <h2>4. Subprocessors</h2>
      <p>
        We use the following categories of subprocessor to operate the Service. Content is sent to
        these providers only as needed to deliver the specific feature Customer is using.
      </p>
      <ul>
        <li>
          <strong>AI model providers</strong> (e.g. Anthropic) — process Customer-submitted content
          to generate AI analysis, scoring, and recommendations Customer explicitly requests.
        </li>
        <li>
          <strong>Vector search / embeddings providers</strong> (e.g. Voyage AI, Qdrant) — power
          semantic search over documents Customer uploads to the Knowledge Vault, within
          Customer&rsquo;s own isolated collection.
        </li>
        <li>
          <strong>Payment processor</strong> (e.g. Stripe) — processes subscription billing; we do
          not receive or store full payment card numbers.
        </li>
        <li>
          <strong>Email delivery</strong> (e.g. SendGrid) — sends transactional email (invites,
          notifications, password resets).
        </li>
        <li>
          <strong>Infrastructure hosting</strong> — cloud hosting, managed database, and managed
          cache providers that store data at rest and process it in transit to run the Service.
        </li>
      </ul>
      <p>
        We do not submit Customer Data on the tenant&rsquo;s behalf to government systems; public
        procurement lookups (SAM.gov, USASpending.gov) are one-directional reads of already-public
        government data, not a channel through which Customer Data is transmitted to government
        systems.
      </p>

      <h2>5. Data We Will Not Accept</h2>
      <p>
        The Service is not designed or authorized to receive Controlled Unclassified Information,
        classified information, or export-controlled (ITAR/EAR) technical data. See Section 4 of
        our{" "}
        <a href="/terms" className="underline hover:text-foreground">
          Terms of Service
        </a>{" "}
        for the full prohibition and Customer&rsquo;s attestation obligations on upload.
      </p>

      <h2>6. Security</h2>
      <p>
        Data is encrypted in transit (TLS) and at rest, with tenant-scoped encryption keys.
        Platform-operator (landlord) accounts are a fully separate identity space from tenant
        accounts and cannot access tenant data through the ordinary application flow. Every
        sensitive data access or mutation is written to an audit log. Details are on our{" "}
        <a href="/security" className="underline hover:text-foreground">
          Security
        </a>{" "}
        page.
      </p>

      <h2>7. Data Retention &amp; Deletion</h2>
      <p>
        We retain Customer Data for as long as the account is active, plus a limited period after
        cancellation to allow reactivation or export, after which it is deleted. Customer may
        request deletion of specific records (e.g. a tracked company, an uploaded document) at any
        time within the product, or request full account data deletion by contacting us.
      </p>

      <h2>8. Your Rights</h2>
      <p>
        Depending on your jurisdiction, you may have rights to access, correct, export, or delete
        your personal information. To exercise these rights, contact{" "}
        <a href="mailto:privacy@cios.ai" className="underline hover:text-foreground">
          privacy@cios.ai
        </a>
        . For data submitted as part of a Customer&rsquo;s account (Customer Data), requests are
        generally directed to that Customer as the data controller, with us acting as processor.
      </p>

      <h2>9. Changes to This Policy</h2>
      <p>
        We may update this Privacy Policy from time to time. Material changes will be notified via
        the Service or email before taking effect.
      </p>

      <h2>10. Contact</h2>
      <p>
        Questions about this Privacy Policy can be sent to{" "}
        <a href="mailto:privacy@cios.ai" className="underline hover:text-foreground">
          privacy@cios.ai
        </a>
        .
      </p>
    </LegalPage>
  );
}
