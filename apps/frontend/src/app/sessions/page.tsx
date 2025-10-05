import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { SessionsPageClient } from './SessionsPageClient';

export default function SessionsPage() {
  return (
    <ProtectedRoute redirectTo="/login">
      <SessionsPageClient />
    </ProtectedRoute>
  );
}
