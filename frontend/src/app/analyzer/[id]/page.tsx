import { EmailAnalyzerDetail } from "./detail";

export default async function AnalyzerDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <EmailAnalyzerDetail emailId={id} />;
}
