'use client';

import React from 'react';
import { useParams } from 'next/navigation';
import { InterviewProvider } from '@/components/interview/InterviewProvider';
import { InterviewChat } from '@/components/interview/InterviewChat';
import { useInterview } from '@/hooks/useInterview';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { Navigation } from '@/components/layout/Navigation';
import { Container } from '@/components/ui/Container';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { ErrorDisplay } from '@/components/ui/ErrorDisplay';

function InterviewPageContent() {
  const { isLoading, error } = useInterview();

  return (
    <>
      <Navigation />
      <div className="min-h-screen bg-gradient-to-br from-deep-indigo-50 to-white py-12">
        <Container size="lg">
          {isLoading ? (
            <LoadingSpinner size="lg" label="Loading session..." />
          ) : error ? (
            <ErrorDisplay error={error} title="Unable to load session" />
          ) : (
            <InterviewChat />
          )}
        </Container>
      </div>
    </>
  );
}

export default function SessionInterviewPage() {
  const params = useParams();
  const sessionId = params.sessionId as string;

  // Set the session ID in localStorage synchronously before rendering
  if (typeof window !== 'undefined' && sessionId) {
    localStorage.setItem('current-interview-session', sessionId);
  }

  return (
    <ProtectedRoute redirectTo="/login">
      <InterviewProvider>
        <InterviewPageContent />
      </InterviewProvider>
    </ProtectedRoute>
  );
}
