'use client';

import { useEffect } from 'react';
import { Button } from '@/components/ui/Button';
import { Container } from '@/components/ui/Container';
import { FiAlertCircle } from 'react-icons/fi';

export default function SessionsError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error('Sessions page error:', error);
  }, [error]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-deep-indigo-50 to-white flex items-center justify-center">
      <Container size="sm">
        <div className="text-center py-12">
          <FiAlertCircle className="w-16 h-16 text-jasper-red-500 mb-6 mx-auto" aria-hidden="true" />
          <h2 className="text-3xl font-bold text-deep-indigo-500 mb-4">Something went wrong</h2>
          <p className="text-base text-deep-indigo-400 mb-8 max-w-md mx-auto">
            {error.message || 'An unexpected error occurred while loading your sessions'}
          </p>
          <div className="flex gap-4 justify-center">
            <Button onClick={reset} variant="primary" size="lg">
              Try Again
            </Button>
            <Button onClick={() => (window.location.href = '/')} variant="secondary" size="lg">
              Go Home
            </Button>
          </div>
        </div>
      </Container>
    </div>
  );
}
