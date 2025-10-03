'use client';

import React from 'react';
import { ProtectedRoute } from './ProtectedRoute';

interface WithAuthOptions {
  redirectTo?: string;
  fallback?: React.ReactNode;
}

export function withAuth<P extends object>(
  Component: React.ComponentType<P>,
  options: WithAuthOptions = {}
) {
  return function AuthenticatedComponent(props: P) {
    return (
      <ProtectedRoute {...options}>
        <Component {...props} />
      </ProtectedRoute>
    );
  };
}