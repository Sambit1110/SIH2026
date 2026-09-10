import { CaseDetailView } from "./detail";

export default async function CaseDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <CaseDetailView caseId={id} />;
}
