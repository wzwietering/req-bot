import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { QAPageClient } from './QAPageClient';
import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Q&A | Requirements Bot',
  description: 'View questions and answers for your session',
};

interface PageProps {
  params: Promise<{
    id: string;
  }>;
}

export default async function SessionQAPage({ params }: PageProps) {
  const { id } = await params;

  return (
    <ProtectedRoute redirectTo="/login">
      <QAPageClient sessionId={id} />
    </ProtectedRoute>
  );
}
