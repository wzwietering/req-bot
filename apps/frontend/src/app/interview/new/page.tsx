'use client';

import React from 'react';
import { InterviewProvider } from '@/components/interview/InterviewProvider';
import { InterviewSetup } from '@/components/interview/InterviewSetup';
import { InterviewChat } from '@/components/interview/InterviewChat';
import { useInterview } from '@/hooks/useInterview';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { Navigation } from '@/components/layout/Navigation';
import { Container } from '@/components/ui/Container';

function InterviewPageContent() {
  const { sessionId, startSession, isLoading } = useInterview();

  const handleStartInterview = async (projectName: string) => {
    await startSession(projectName);
  };

  return (
    <>
      <Navigation />
      <div className="min-h-screen bg-gradient-to-br from-deep-indigo-50 to-white py-12">
        <Container size="lg">
          {!sessionId ? (
            <InterviewSetup onStart={handleStartInterview} isLoading={isLoading} />
          ) : (
            <InterviewChat />
          )}
        </Container>
      </div>
    </>
  );
}

export default function NewInterviewPage() {
  return (
    <ProtectedRoute redirectTo="/login">
      <InterviewProvider>
        <InterviewPageContent />
      </InterviewProvider>
    </ProtectedRoute>
  );
}
