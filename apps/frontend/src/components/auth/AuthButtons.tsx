'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '../ui/Button';
import { UserProfileDropdown } from './UserProfileDropdown';
import { useAuth } from './AuthProvider';
import { useQuota } from '@/contexts/QuotaContext';
import { QuotaBadge } from '@/components/ui/QuotaBadge';
import { formatResetDate } from '@/lib/utils/quota';

interface AuthButtonsProps {
  className?: string;
  showMainCTA?: boolean;
}

export function AuthButtons({ className = '', showMainCTA = true }: AuthButtonsProps) {
  const { user, isAuthenticated, isLoading, logout } = useAuth();
  const { isUrgent, isCritical, canCreateSession, usage, resetDate } = useQuota();
  const router = useRouter();

  const handleLogin = () => {
    router.push('/login');
  };

  const handleNewInterview = () => {
    if (!canCreateSession) {
      return; // Button should be disabled, but just in case
    }
    // Clear any existing interview session when starting a new one
    localStorage.removeItem('current-interview-session');
    router.push('/interview/new');
  };

  if (isLoading) {
    return (
      <div className={`flex items-center space-x-3 ${className}`}>
        {/* Login button skeleton */}
        <div className="h-10 w-20 bg-deep-indigo-100 rounded-md animate-pulse" />
        {showMainCTA && (
          <div className="h-10 w-44 bg-deep-indigo-100 rounded-md animate-pulse" />
        )}
      </div>
    );
  }

  if (isAuthenticated && user) {
    const showBadge = isUrgent || isCritical;
    const badgeVariant = isCritical ? 'critical' : 'urgent';

    return (
      <div className={`flex items-center space-x-3 ${className}`}>
        <div className="relative">
          <UserProfileDropdown
            user={user}
            onLogout={logout}
            isLoading={isLoading}
          />
          {showBadge && usage && (
            <QuotaBadge
              count={usage.quotaRemaining}
              variant={badgeVariant}
              aria-label={`${usage.quotaRemaining} sessions remaining`}
            />
          )}
        </div>
        {showMainCTA && (
          <div className="relative group">
            <Button
              size="md"
              onClick={handleNewInterview}
              disabled={!canCreateSession}
              aria-describedby={!canCreateSession ? 'quota-exceeded-tooltip' : undefined}
            >
              New Interview
            </Button>
            {!canCreateSession && resetDate && (
              <div
                id="quota-exceeded-tooltip"
                role="tooltip"
                className="absolute top-full mt-2 right-0 w-64 p-3 bg-white rounded-lg shadow-lg border border-deep-indigo-100 z-50 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200"
              >
                <p className="font-semibold text-sm text-deep-indigo-900 mb-1">
                  Quota Exceeded
                </p>
                <p className="text-sm text-gray-600 mb-2">
                  You&apos;ve used all {usage?.quotaLimit || 10} sessions this month
                </p>
                <p className="text-xs text-gray-500 mb-3">
                  Resets {formatResetDate(resetDate)}
                </p>
                <button
                  onClick={() => {
                    // TODO: Navigate to upgrade page
                    console.log('Upgrade to Pro clicked');
                  }}
                  className="btn-base btn-md bg-deep-indigo-400 text-white hover:bg-deep-indigo-500 w-full"
                >
                  Upgrade to Pro
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className={`flex items-center space-x-3 ${className}`}>
      <Button
        variant="secondary"
        size="md"
        onClick={handleLogin}
        className="transition-all duration-200"
      >
        Sign In
      </Button>
      {showMainCTA && (
        <Button size="md" onClick={handleNewInterview}>
          Start Your First Interview
        </Button>
      )}
    </div>
  );
}

interface AuthButtonsMobileProps {
  className?: string;
  onMenuClose?: () => void;
}

export function AuthButtonsMobile({ className = '', onMenuClose }: AuthButtonsMobileProps) {
  const { user, isAuthenticated, isLoading, logout } = useAuth();
  const router = useRouter();

  const handleLogin = () => {
    router.push('/login');
    onMenuClose?.();
  };

  const handleNewInterview = () => {
    router.push('/interview/new');
    onMenuClose?.();
  };

  const handleLogout = async () => {
    try {
      await logout();
      onMenuClose?.();
    } catch (error) {
      console.error('Logout failed:', error);
    }
  };

  if (isLoading) {
    return (
      <div className={`space-y-3 ${className}`}>
        <div className="h-12 bg-deep-indigo-100 rounded-lg animate-pulse" />
        <div className="h-12 bg-deep-indigo-100 rounded-lg animate-pulse" />
      </div>
    );
  }

  if (isAuthenticated && user) {
    const displayName = user.name || user.email.split('@')[0];
    const avatarUrl = user.avatar_url;

    return (
      <div className={`space-y-4 ${className}`}>
        {/* User Info Section */}
        <div className="p-4 bg-deep-indigo-25 rounded-lg border border-deep-indigo-100">
          <div className="flex items-center space-x-3">
            {avatarUrl ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={avatarUrl}
                alt={`${displayName}'s avatar`}
                className="w-10 h-10 rounded-full object-cover ring-2 ring-white shadow-sm"
              />
            ) : (
              <div className="w-10 h-10 rounded-full bg-deep-indigo-500 flex items-center justify-center text-white font-medium">
                {displayName.charAt(0).toUpperCase()}
              </div>
            )}
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-deep-indigo-500 truncate">
                {displayName}
              </p>
              <p className="text-xs text-deep-indigo-400 truncate">
                {user.email}
              </p>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="space-y-3">
          <Button size="md" className="w-full" onClick={handleNewInterview}>
            New Interview
          </Button>
          <Button
            variant="outline"
            size="md"
            onClick={handleLogout}
            className="w-full text-jasper-red-500 border-jasper-red-200 hover:bg-jasper-red-50"
          >
            Sign Out
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className={`space-y-3 ${className}`}>
      <Button
        variant="secondary"
        size="md"
        onClick={handleLogin}
        className="w-full"
      >
        Sign In
      </Button>
      <Button size="md" className="w-full" onClick={handleNewInterview}>
        Start Your First Interview
      </Button>
    </div>
  );
}