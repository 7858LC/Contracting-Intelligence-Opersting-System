import type { Metadata } from "next";
import { CapabilityView } from "@/components/modules/capability/capability-view";

export const metadata: Metadata = { title: "Capabilities & Gaps" };

export default function CapabilitiesPage() {
  return <CapabilityView />;
}
