'use client';

import React, { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { LoginForm } from '../../components/auth/LoginForm';
import { useAuth } from '../../hooks/useAuth';
import { Navigation, Footer } from '../../components/layout';
import { Container } from '../../components/ui';

export default function LoginPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAuth();

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      const redirectTo = localStorage.getItem('auth_redirect') || '/';
      localStorage.removeItem('auth_redirect');
      router.push(redirectTo);
    }
  }, [isAuthenticated, isLoading, router]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-4 border-deep-indigo-200 border-t-deep-indigo-500 rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">Checking authentication...</p>
        </div>
      </div>
    );
  }

  if (isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-4 border-benzol-green-200 border-t-benzol-green-500 rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">Redirecting...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Skip to main content link for accessibility */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:px-4 focus:py-2 focus:bg-jasper-red-500 focus:text-white focus:rounded focus:outline-2 focus:outline-benzol-green-500"
      >
        Skip to main content
      </a>

      <Navigation />

      {/* Main content */}
      <main id="main-content" className="flex-1 flex items-center justify-center py-12">
        <Container size="sm">
          <LoginForm />
        </Container>
      </main>

      <Footer />
    </div>
  );
}