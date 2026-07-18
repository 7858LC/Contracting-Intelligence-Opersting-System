import { Metadata } from "next";
import { AwardSimulatorView } from "@/components/modules/simulation/award-simulator-view";

export const metadata: Metadata = { title: "Award Simulator" };

export default function AwardSimulatorPage() {
  return <AwardSimulatorView />;
}
