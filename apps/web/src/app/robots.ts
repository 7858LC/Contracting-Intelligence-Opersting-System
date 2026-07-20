import type { MetadataRoute } from "next";

const BASE_URL =
  process.env.NEXT_PUBLIC_APP_URL || "https://uzimaamka.com";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: ["/", "/platform", "/radar", "/diagnostics", "/pdq", "/simulation", "/research", "/executive-council", "/pricing", "/about"],
        disallow: ["/dashboard/", "/auth/", "/api/"],
      },
    ],
    sitemap: `${BASE_URL}/sitemap.xml`,
    host: BASE_URL,
  };
}
