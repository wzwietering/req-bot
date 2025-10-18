import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { SessionsPageClient } from './SessionsPageClient';
import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'My Sessions | SpecScribe',
  description: 'View and manage your requirements gathering sessions',
};

export default function SessionsPage() {
  return (
    <ProtectedRoute redirectTo="/login">
      <SessionsPageClient />
    </ProtectedRoute>
  );
}
