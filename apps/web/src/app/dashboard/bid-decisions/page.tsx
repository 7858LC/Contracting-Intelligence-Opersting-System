import type { Metadata } from "next";
import { BidDecisionView } from "@/components/modules/bid-decision/bid-decision-view";

export const metadata: Metadata = { title: "Bid / No-Bid" };

export default function BidDecisionsPage() {
  return <BidDecisionView />;
}
