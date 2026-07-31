import type { Metadata } from "next";
import { ResearchView } from "@/components/modules/research/research-view";

export const metadata: Metadata = { title: "Executive Council Research" };

export default function ResearchPage() {
  return <ResearchView />;
}
