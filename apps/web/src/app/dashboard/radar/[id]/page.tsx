import { CompanyDetail } from "@/components/modules/radar/company-detail";

export const metadata = { title: "Company Intelligence — CIOS Radar" };

export default function CompanyDetailPage({ params }: { params: { id: string } }) {
  return <CompanyDetail companyId={params.id} />;
}
