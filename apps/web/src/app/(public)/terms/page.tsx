import type { Metadata } from "next";
import { buildPageMetadata } from "@/lib/metadata";
import { LegalPage } from "@/components/layout/legal-page";

export const metadata: Metadata = buildPageMetadata({
  title: "Terms of Service — CIOS™",
  description: "The terms governing use of the CIOS™ Procurement Intelligence platform.",
  path: "/terms",
});

const LAST_UPDATED = "August 3, 2026";

export default function TermsPage() {
  return (
    <LegalPage title="Terms of Service" lastUpdated={LAST_UPDATED}>
      <p>
        These Terms of Service (&ldquo;Terms&rdquo;) govern access to and use of the CIOS™
        Contract Intelligence Operating System platform (the &ldquo;Service&rdquo;), operated by
        Uzima Amka Ventures (&ldquo;Company,&rdquo; &ldquo;we,&rdquo; &ldquo;us&rdquo;). By
        creating an account or otherwise using the Service, you (&ldquo;Customer,&rdquo;
        &ldquo;you&rdquo;) agree to these Terms. If you are entering into these Terms on behalf of
        an organization, you represent that you have authority to bind that organization.
      </p>

      <h2>1. The Service</h2>
      <p>
        CIOS is a commercial software-as-a-service platform for government-contracting
        intelligence. It aggregates and analyzes public procurement data (e.g. SAM.gov,
        USASpending.gov) alongside Customer-provided business inputs to produce decision-support
        outputs such as opportunity scoring, competitive signals, and AI-generated analysis.
      </p>
      <p>
        <strong>CIOS is not a government system of record.</strong> It does not store or transmit
        data on behalf of any government agency, and a subscription does not create any
        relationship between Customer and the government.
      </p>
      <p>
        Outputs from the Service — including AI-generated recommendations, scores, and
        analysis — are decision support, not a guarantee of any procurement outcome. Customer
        remains solely responsible for its own bid/no-bid, capture, and compliance decisions.
      </p>

      <h2>2. Accounts and Subscriptions</h2>
      <p>
        Customer is responsible for maintaining the confidentiality of its account credentials and
        for all activity under its account. Subscription plans, seat counts, and usage limits are
        as described at checkout or in an applicable order form, and are billed in advance on a
        recurring basis unless otherwise agreed. Fees are non-refundable except as required by law
        or expressly stated in an order form.
      </p>

      <h2>3. Acceptable Use</h2>
      <p>Customer will not, and will not permit any user of its account to:</p>
      <ul>
        <li>Use the Service to violate any applicable law or regulation;</li>
        <li>Attempt to circumvent tenant isolation, rate limits, or usage-based plan limits;</li>
        <li>
          Reverse engineer, scrape, or resell the Service or its underlying data or scoring
          methodology without written permission; or
        </li>
        <li>
          Use the Service to build a directly competing product using data or outputs obtained
          through the Service.
        </li>
      </ul>

      <h2>4. Prohibited Data</h2>
      <p>
        Customer shall not upload, transmit, input, or otherwise submit to the Service any of the
        following (&ldquo;Prohibited Data&rdquo;): (a) Controlled Unclassified Information as
        defined by 32 C.F.R. Part 2002 and any agency-specific CUI category; (b) classified
        national security information under Executive Order 13526 or any successor order; (c)
        technical data or information subject to the International Traffic in Arms Regulations
        (ITAR, 22 C.F.R. Parts 120–130) or the Export Administration Regulations (EAR, 15 C.F.R.
        Parts 730–774); or (d) any other data Customer is prohibited by law, regulation, or
        contract from disclosing to a third party or processing outside a government-accredited
        or specifically authorized system.
      </p>
      <p>
        The Service is not designed, accredited, or authorized to receive, store, or process
        Prohibited Data, including via the Service&rsquo;s use of third-party AI model providers
        to analyze Customer-submitted content (see Section 5). Customer is solely responsible for
        ensuring that content it submits to the Service does not constitute Prohibited Data, and
        shall indemnify, defend, and hold harmless the Company from and against any claim, loss,
        liability, fine, or regulatory action arising from Customer&rsquo;s breach of this
        provision.
      </p>
      <p>
        The Company reserves the right to (i) implement automated or manual screening for markings
        indicative of Prohibited Data and reject or quarantine content bearing such markings, (ii)
        suspend or terminate Customer&rsquo;s account for actual or suspected submission of
        Prohibited Data, and (iii) report suspected submissions of classified information to the
        appropriate government authority where legally required. The Knowledge Vault upload flow
        requires Customer to affirmatively attest, per document, that it does not contain
        Prohibited Data before that document is stored or processed.
      </p>

      <h2>5. Third-Party AI and Data Providers</h2>
      <p>
        The Service uses third-party subprocessors to operate, including large language model
        providers (for AI-generated analysis and recommendations) and vector-search infrastructure
        (for document retrieval within Customer&rsquo;s own tenant). See our{" "}
        <a href="/privacy" className="underline hover:text-foreground">
          Privacy Policy
        </a>{" "}
        for the current subprocessor list. Content Customer submits to the Service may be
        transmitted to these subprocessors solely to provide the Service to Customer, and is not
        used by the Company to train foundation models.
      </p>

      <h2>6. Intellectual Property</h2>
      <p>
        The Company retains all right, title, and interest in the Service, including its
        methodology, scoring models, and underlying software. Customer retains ownership of data
        and content it submits to the Service (&ldquo;Customer Data&rdquo;) and grants the Company
        a license to process Customer Data solely to provide the Service.
      </p>

      <h2>7. Disclaimers and Limitation of Liability</h2>
      <p>
        THE SERVICE IS PROVIDED &ldquo;AS IS&rdquo; WITHOUT WARRANTY OF ANY KIND. THE COMPANY DOES
        NOT WARRANT THAT PUBLIC PROCUREMENT DATA AGGREGATED BY THE SERVICE IS COMPLETE, CURRENT,
        OR ERROR-FREE, OR THAT ANY AI-GENERATED OUTPUT WILL BE ACCURATE. TO THE MAXIMUM EXTENT
        PERMITTED BY LAW, THE COMPANY&rsquo;S AGGREGATE LIABILITY UNDER THESE TERMS WILL NOT
        EXCEED THE FEES PAID BY CUSTOMER IN THE TWELVE MONTHS PRECEDING THE CLAIM.
      </p>

      <h2>8. Termination</h2>
      <p>
        Either party may terminate a subscription as described in the applicable order form or
        plan terms. The Company may suspend or terminate access immediately for a material breach
        of Section 3 or 4. Upon termination, Customer&rsquo;s right to access the Service ends;
        Customer Data is retained and deleted per our{" "}
        <a href="/privacy" className="underline hover:text-foreground">
          Privacy Policy
        </a>
        .
      </p>

      <h2>9. Changes to These Terms</h2>
      <p>
        We may update these Terms from time to time. Material changes will be notified via the
        Service or email to the account owner before taking effect. Continued use of the Service
        after changes take effect constitutes acceptance.
      </p>

      <h2>10. Contact</h2>
      <p>
        Questions about these Terms can be sent to{" "}
        <a href="mailto:legal@cios.ai" className="underline hover:text-foreground">
          legal@cios.ai
        </a>
        .
      </p>
    </LegalPage>
  );
}
