import { Metadata } from "next";
import { ExecutiveDashboard } from "@/components/modules/dashboard/executive-dashboard";

export const metadata: Metadata = { title: "Executive Dashboard" };

export default function DashboardPage() {
  return <ExecutiveDashboard />;
}
