import { ImageResponse } from "next/og";
import type { NextRequest } from "next/server";

export const runtime = "edge";

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const title = searchParams.get("title") || "Procurement Intelligence™";
  const description =
    searchParams.get("description") ||
    "Executive Decision Support for Public Sector Growth";

  return new ImageResponse(
    (
      <div
        style={{
          background: "#080d16",
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          padding: "60px 80px",
          fontFamily: "system-ui, -apple-system, sans-serif",
          position: "relative",
        }}
      >
        {/* Left accent bar */}
        <div
          style={{
            position: "absolute",
            left: 0,
            top: 0,
            width: 5,
            height: "100%",
            background: "hsl(162,72%,36%)",
          }}
        />

        {/* Eyebrow */}
        <div
          style={{
            fontSize: 13,
            color: "hsl(162,72%,46%)",
            letterSpacing: "0.2em",
            textTransform: "uppercase",
            marginBottom: 32,
          }}
        >
          UZIMA AMKA VENTURES
        </div>

        {/* Title */}
        <div
          style={{
            fontSize: title.length > 40 ? 48 : 62,
            fontWeight: 700,
            color: "white",
            lineHeight: 1.08,
            marginBottom: 24,
            maxWidth: 820,
          }}
        >
          {title}
        </div>

        {/* Description */}
        <div
          style={{
            fontSize: 22,
            color: "#6b7280",
            lineHeight: 1.4,
            maxWidth: 700,
            marginTop: "auto",
          }}
        >
          {description}
        </div>

        {/* Radar decoration */}
        <div
          style={{
            position: "absolute",
            right: 80,
            top: "50%",
            transform: "translateY(-50%)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <svg width="200" height="200" viewBox="0 0 200 200" fill="none">
            <circle cx="100" cy="100" r="90" stroke="hsl(162,72%,36%)" strokeWidth="1" opacity="0.2" />
            <circle cx="100" cy="100" r="60" stroke="hsl(162,72%,36%)" strokeWidth="1" opacity="0.3" />
            <circle cx="100" cy="100" r="30" stroke="hsl(162,72%,36%)" strokeWidth="1.5" opacity="0.5" />
            <line x1="100" y1="10" x2="100" y2="100" stroke="hsl(162,72%,36%)" strokeWidth="2" opacity="0.7" />
            <circle cx="140" cy="55" r="8" fill="hsl(38,95%,52%)" opacity="0.9" />
          </svg>
        </div>
      </div>
    ),
    { width: 1200, height: 630 }
  );
}
