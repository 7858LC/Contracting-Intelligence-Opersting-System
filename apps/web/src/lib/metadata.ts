import type { Metadata } from "next";

const BASE_URL =
  process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000";

interface PageMetadataOptions {
  title: string;
  description: string;
  path: string;
  image?: string;
}

export function buildPageMetadata({
  title,
  description,
  path,
  image,
}: PageMetadataOptions): Metadata {
  const url = `${BASE_URL}${path}`;
  const ogImage =
    image ??
    `${BASE_URL}/api/og?title=${encodeURIComponent(title)}&description=${encodeURIComponent(description)}`;

  return {
    title,
    description,
    metadataBase: new URL(BASE_URL),
    alternates: { canonical: url },
    openGraph: {
      title,
      description,
      url,
      siteName: "Uzima Amka Ventures",
      locale: "en_US",
      type: "website",
      images: [{ url: ogImage, width: 1200, height: 630, alt: title }],
    },
    twitter: {
      card: "summary_large_image",
      title,
      description,
      images: [ogImage],
    },
    robots: { index: true, follow: true },
  };
}
