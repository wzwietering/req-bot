'use client';

import React, { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '../../hooks/useAuth';

interface ProtectedRouteProps {
  children: React.ReactNode;
  redirectTo?: string;
  fallback?: React.ReactNode;
}

export function ProtectedRoute({
  children,
  redirectTo = '/login',
  fallback
}: ProtectedRouteProps) {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      // Store current path for redirect after login
      const currentPath = window.location.pathname + window.location.search;
      if (currentPath !== '/login') {
        localStorage.setItem('auth_redirect', currentPath);
      }
      router.push(redirectTo);
    }
  }, [isAuthenticated, isLoading, router, redirectTo]);

  // Show loading state while checking authentication
  if (isLoading) {
    return fallback || (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-4 border-deep-indigo-200 border-t-deep-indigo-500 rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  // Don't render children if not authenticated
  if (!isAuthenticated) {
    return fallback || null;
  }

  return <>{children}</>;
}