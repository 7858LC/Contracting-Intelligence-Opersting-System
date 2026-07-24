const BASE_URL =
  process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000";

export const organizationSchema = {
  "@context": "https://schema.org",
  "@type": "Organization",
  name: "Uzima Amka Ventures",
  url: BASE_URL,
  logo: `${BASE_URL}/favicon.svg`,
  description:
    "The company delivering Procurement Intelligence™ — the analytical discipline for executive decision support in public sector contracting.",
  foundingDate: "2024",
  knowsAbout: [
    "Procurement Intelligence",
    "Government Contracting",
    "Federal Acquisition",
    "Competitive Intelligence",
  ],
};

export const softwareApplicationSchema = {
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  name: "CIOS™",
  alternateName: "Contract Intelligence Operating System",
  applicationCategory: "BusinessApplication",
  operatingSystem: "Web",
  description:
    "The operating system powering Procurement Intelligence™. CIOS aggregates signals from federal data sources, applies structured analysis across six intelligence dimensions, and delivers decision-ready briefs to executive capture teams.",
  offers: {
    "@type": "AggregateOffer",
    priceCurrency: "USD",
    offerCount: 4,
    lowPrice: "399",
  },
  publisher: {
    "@type": "Organization",
    name: "Uzima Amka Ventures",
  },
};

export function breadcrumbSchema(items: { name: string; url: string }[]) {
  return {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: items.map((item, index) => ({
      "@type": "ListItem",
      position: index + 1,
      name: item.name,
      item: item.url,
    })),
  };
}

export function productSchema(opts: {
  name: string;
  description: string;
  url: string;
}) {
  return {
    "@context": "https://schema.org",
    "@type": "Product",
    name: opts.name,
    description: opts.description,
    url: opts.url,
    brand: {
      "@type": "Brand",
      name: "Uzima Amka Ventures",
    },
    offers: {
      "@type": "Offer",
      availability: "https://schema.org/PreOrder",
      priceCurrency: "USD",
    },
  };
}
