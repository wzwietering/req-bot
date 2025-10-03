'use client';

import React, { useState, useEffect } from 'react';
import { OAuthButton } from './OAuthButton';
import { useAuth } from '../../hooks/useAuth';
import { OAuthProvider } from '../../lib/auth/types';

interface LoginFormProps {
  redirectTo?: string;
}

export function LoginForm({ redirectTo }: LoginFormProps) {
  const { login, error, clearError, isLoading } = useAuth();
  const [loadingProvider, setLoadingProvider] = useState<OAuthProvider | null>(null);

  useEffect(() => {
    if (redirectTo) {
      localStorage.setItem('auth_redirect', redirectTo);
    }
  }, [redirectTo]);

  const handleProviderLogin = (provider: OAuthProvider) => {
    clearError();
    setLoadingProvider(provider);

    setTimeout(() => {
      login(provider);
    }, 500);
  };

  const providers: OAuthProvider[] = ['github', 'google', 'microsoft'];

  return (
    <div className="w-full max-w-md mx-auto">
      <div className="text-center mb-8">
        <h1 className="text-hero text-deep-indigo-500 mb-4">
          Welcome to Requirements Bot
        </h1>
        <p className="text-lead text-gray-600">
          Sign in with your preferred developer account
        </p>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg" role="alert">
          <div className="flex items-center">
            <div className="text-red-600 text-sm">
              <strong>Sign in failed:</strong> {error}
            </div>
            <button
              onClick={clearError}
              className="ml-auto text-red-600 hover:text-red-800 text-lg font-bold"
              aria-label="Dismiss error"
            >
              ×
            </button>
          </div>
          <div className="mt-2 text-xs text-red-500">
            Still having trouble? <a href="/support" className="underline hover:text-red-700">Contact support</a>
          </div>
        </div>
      )}

      <div className="space-y-4 mb-8">
        {providers.map((provider) => (
          <OAuthButton
            key={provider}
            provider={provider}
            onClick={handleProviderLogin}
            disabled={isLoading || loadingProvider !== null}
            isLoading={loadingProvider === provider}
          />
        ))}
      </div>

      <div className="text-center text-sm text-gray-500">
        By signing in, you agree to our{' '}
        <a
          href="/terms"
          target="_blank"
          rel="noopener noreferrer"
          className="text-deep-indigo-500 hover:text-deep-indigo-600 underline"
        >
          Terms of Use
        </a>{' '}
        and{' '}
        <a
          href="/privacy"
          target="_blank"
          rel="noopener noreferrer"
          className="text-deep-indigo-500 hover:text-deep-indigo-600 underline"
        >
          Privacy Policy
        </a>
      </div>
    </div>
  );
}