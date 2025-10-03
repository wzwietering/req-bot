'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from './useAuth';

interface UseRequireAuthOptions {
  redirectTo?: string;
}

export function useRequireAuth(options: UseRequireAuthOptions = {}) {
  const { isAuthenticated, isLoading, user } = useAuth();
  const router = useRouter();
  const { redirectTo = '/login' } = options;

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      // Store current path for redirect after login
      const currentPath = window.location.pathname + window.location.search;
      if (currentPath !== redirectTo) {
        localStorage.setItem('auth_redirect', currentPath);
      }
      router.push(redirectTo);
    }
  }, [isAuthenticated, isLoading, router, redirectTo]);

  return {
    isAuthenticated,
    isLoading,
    user,
    isReady: !isLoading && isAuthenticated,
  };
}