import type { Metadata, Viewport } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import { ThemeProvider } from "@/components/layout/theme-provider";
import { Toaster } from "sonner";
import { QueryProvider } from "@/lib/query-provider";
import "@/styles/globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const jetbrains = JetBrains_Mono({ subsets: ["latin"], variable: "--font-jetbrains" });

const BASE_URL = process.env.NEXT_PUBLIC_APP_URL || "https://uzimaamka.com";

export const metadata: Metadata = {
  title: {
    default: "Procurement Intelligence™ — Uzima Amka Ventures",
    template: "%s | Uzima Amka Ventures",
  },
  description:
    "Executive decision support for public sector growth. CIOS™ — the Contract Intelligence Operating System — delivers Procurement Intelligence™ across six analytical modules.",
  keywords: [
    "procurement intelligence",
    "government contracting",
    "federal acquisition",
    "capture management",
    "bid decision",
    "award probability",
    "CIOS",
    "Uzima Amka Ventures",
  ],
  metadataBase: new URL(BASE_URL),
  robots: { index: true, follow: true },
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
    apple: "/favicon.svg",
  },
  manifest: "/site.webmanifest",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.variable} ${jetbrains.variable} font-sans antialiased`}>
        <ThemeProvider attribute="class" defaultTheme="dark" enableSystem>
          <QueryProvider>
            {children}
            <Toaster position="top-right" richColors />
          </QueryProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
