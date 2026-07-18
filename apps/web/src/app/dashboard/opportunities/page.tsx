import type { Metadata } from "next";
import { OpportunityView } from "@/components/modules/opportunity/opportunity-view";

export const metadata: Metadata = { title: "Opportunities" };

export default function OpportunitiesPage() {
  return <OpportunityView />;
}
