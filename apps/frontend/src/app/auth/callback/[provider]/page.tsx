'use client';

import React, { useEffect, useRef, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '../../../../hooks/useAuth';
import { parseOAuthError } from '../../../../lib/auth/api';
import { OAuthProvider } from '../../../../lib/auth/types';
import { Navigation, Footer } from '../../../../components/layout';
import { Container } from '../../../../components/ui';

interface CallbackPageProps {
  params: Promise<{ provider: string }>;
}

export default function CallbackPage({ params }: CallbackPageProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { checkAuthStatus, clearError } = useAuth();
  const [status, setStatus] = useState<'processing' | 'success' | 'error'>('processing');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [provider, setProvider] = useState<string>('');
  const hasProcessedCallback = useRef(false);

  useEffect(() => {
    const handleCallback = async () => {
      // Prevent duplicate execution
      if (hasProcessedCallback.current) {
        return;
      }
      hasProcessedCallback.current = true;

      try {
        clearError();

        // Resolve params first
        const resolvedParams = await params;
        setProvider(resolvedParams.provider);

        // Validate provider
        const providerName = resolvedParams.provider as OAuthProvider;
        if (!['google', 'github', 'microsoft'].includes(providerName)) {
          setErrorMessage('Invalid OAuth provider');
          setStatus('error');
          return;
        }

        // Check for OAuth errors in URL
        const oauthError = parseOAuthError(searchParams);
        if (oauthError) {
          setErrorMessage(oauthError.message);
          setStatus('error');
          return;
        }

        // Check if callback was successful (backend redirects with success=true)
        const success = searchParams.get('success');
        if (success !== 'true') {
          setErrorMessage('OAuth callback did not complete successfully');
          setStatus('error');
          return;
        }

        // Backend has already processed the callback and set httpOnly cookies
        // Verify authentication by calling /me endpoint (cookies are sent automatically)
        // Note: We can't check for HttpOnly cookies via document.cookie - they're only sent in HTTP requests
        try {
          await checkAuthStatus();
        } catch {
          // If checkAuthStatus fails, it likely means cookies weren't set or are blocked
          setErrorMessage('Authentication failed. Please check your browser settings and ensure cookies are enabled.');
          setStatus('error');
          return;
        }

        setStatus('success');

        // Redirect to intended destination
        const redirectTo = localStorage.getItem('auth_redirect') || '/';
        localStorage.removeItem('auth_redirect');

        setTimeout(() => {
          router.push(redirectTo);
        }, 1500);

      } catch (error) {
        console.error('OAuth callback error:', error);
        setErrorMessage('An unexpected error occurred during authentication');
        setStatus('error');
      }
    };

    handleCallback();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleRetry = () => {
    router.push('/login');
  };

  const getProviderDisplayName = (provider: string) => {
    const names: Record<string, string> = {
      google: 'Google',
      github: 'GitHub',
      microsoft: 'Microsoft',
    };
    return names[provider] || provider;
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <Navigation />

      <main className="flex-1 flex items-center justify-center py-12">
        <Container size="sm">
          <div className="text-center">
            {status === 'processing' && (
              <>
                <div className="w-12 h-12 border-4 border-deep-indigo-200 border-t-deep-indigo-500 rounded-full animate-spin mx-auto mb-6"></div>
                <h1 className="text-2xl font-semibold text-gray-900 mb-2">
                  Completing sign in...
                </h1>
                <p className="text-gray-600">
                  Finalizing your {getProviderDisplayName(provider)} authentication
                </p>
              </>
            )}

            {status === 'success' && (
              <>
                <div className="w-12 h-12 bg-benzol-green-500 rounded-full flex items-center justify-center mx-auto mb-6">
                  <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <h1 className="text-2xl font-semibold text-gray-900 mb-2">
                  Sign in successful!
                </h1>
                <p className="text-gray-600 mb-4">
                  Welcome to SpecScribe. Redirecting you now...
                </p>
                <div className="w-8 h-8 border-4 border-benzol-green-200 border-t-benzol-green-500 rounded-full animate-spin mx-auto"></div>
              </>
            )}

            {status === 'error' && (
              <>
                <div className="w-12 h-12 bg-red-500 rounded-full flex items-center justify-center mx-auto mb-6">
                  <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </div>
                <h1 className="text-2xl font-semibold text-gray-900 mb-2">
                  Sign in failed
                </h1>
                <p className="text-red-600 mb-6">
                  {errorMessage}
                </p>
                <div className="space-y-3">
                  <button
                    onClick={handleRetry}
                    className="btn-base btn-primary btn-lg"
                  >
                    Try Again
                  </button>
                  <div className="text-sm text-gray-500">
                    Still having trouble?{' '}
                    <a href="/support" className="text-deep-indigo-500 hover:text-deep-indigo-600 underline">
                      Contact support
                    </a>
                  </div>
                </div>
              </>
            )}
          </div>
        </Container>
      </main>

      <Footer />
    </div>
  );
}