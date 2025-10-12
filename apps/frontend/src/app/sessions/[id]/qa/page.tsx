import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { QAPageClient } from './QAPageClient';
import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Q&A | Requirements Bot',
  description: 'View questions and answers for your session',
};

interface PageProps {
  params: {
    id: string;
  };
}

export default function SessionQAPage({ params }: PageProps) {
  return (
    <ProtectedRoute redirectTo="/login">
      <QAPageClient sessionId={params.id} />
    </ProtectedRoute>
  );
}
