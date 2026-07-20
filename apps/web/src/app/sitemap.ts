import type { MetadataRoute } from "next";

const BASE_URL =
  process.env.NEXT_PUBLIC_APP_URL || "https://uzimaamka.com";

const PUBLIC_ROUTES: { url: string; changeFrequency: MetadataRoute.Sitemap[number]["changeFrequency"]; priority: number }[] = [
  { url: "/", changeFrequency: "weekly", priority: 1.0 },
  { url: "/platform", changeFrequency: "monthly", priority: 0.9 },
  { url: "/radar", changeFrequency: "monthly", priority: 0.9 },
  { url: "/diagnostics", changeFrequency: "monthly", priority: 0.8 },
  { url: "/pdq", changeFrequency: "monthly", priority: 0.8 },
  { url: "/simulation", changeFrequency: "monthly", priority: 0.8 },
  { url: "/research", changeFrequency: "weekly", priority: 0.7 },
  { url: "/executive-council", changeFrequency: "monthly", priority: 0.7 },
  { url: "/pricing", changeFrequency: "monthly", priority: 0.8 },
  { url: "/about", changeFrequency: "monthly", priority: 0.6 },
];

export default function sitemap(): MetadataRoute.Sitemap {
  const now = new Date();
  return PUBLIC_ROUTES.map(({ url, changeFrequency, priority }) => ({
    url: `${BASE_URL}${url}`,
    lastModified: now,
    changeFrequency,
    priority,
  }));
}
