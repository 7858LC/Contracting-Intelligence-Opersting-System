import type { Metadata } from "next";
import { WinningProfileView } from "@/components/modules/winning-profile/winning-profile-view";

export const metadata: Metadata = { title: "Winning Profile Hypothesis™" };

export default function WinningProfilePage() {
  return <WinningProfileView />;
}
