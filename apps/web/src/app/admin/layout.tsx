import type { Metadata } from "next";
import { AdminShell } from "@/components/layout/admin-shell";

export const metadata: Metadata = {
  title: "CIOS Landlord Console",
  robots: { index: false, follow: false },
};

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return <AdminShell>{children}</AdminShell>;
}
