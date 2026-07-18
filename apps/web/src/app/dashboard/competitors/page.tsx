import type { Metadata } from "next";
import { CompetitorView } from "@/components/modules/competitor/competitor-view";

export const metadata: Metadata = { title: "Competitive Intelligence" };

export default function CompetitorsPage() {
  return <CompetitorView />;
}
