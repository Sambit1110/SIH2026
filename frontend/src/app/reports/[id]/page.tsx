import { ReportView } from "./detail";

export default async function ReportDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <ReportView reportId={id} />;
}
