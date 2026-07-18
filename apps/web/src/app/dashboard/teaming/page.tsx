import type { Metadata } from "next";
import { TeamingView } from "@/components/modules/teaming/teaming-view";

export const metadata: Metadata = { title: "Teaming" };

export default function TeamingPage() {
  return <TeamingView />;
}
