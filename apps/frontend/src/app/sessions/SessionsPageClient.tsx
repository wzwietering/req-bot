'use client';

import { useEffect } from 'react';
import { Navigation } from '@/components/layout/Navigation';
import { Container } from '@/components/ui/Container';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { ErrorDisplay } from '@/components/ui/ErrorDisplay';
import { useSessions } from '@/hooks/useSessions';
import { SessionsList } from './components/SessionsList';

export function SessionsPageClient() {
  const { sessions, isLoading, error, loadSessions, deleteSession } = useSessions();

  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-deep-indigo-50 to-white">
      <Navigation />
      <main className="py-12">
        <Container size="lg">
          {isLoading ? (
            <LoadingSpinner size="lg" label="Loading sessions..." />
          ) : error ? (
            <ErrorDisplay error={error} onRetry={loadSessions} />
          ) : (
            <SessionsList sessions={sessions} onDeleteSession={deleteSession} />
          )}
        </Container>
      </main>
    </div>
  );
}
