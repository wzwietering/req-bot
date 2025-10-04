'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '../ui/Button';
import { UserProfileDropdown } from './UserProfileDropdown';
import { useAuth } from './AuthProvider';

interface AuthButtonsProps {
  className?: string;
  showMainCTA?: boolean;
}

export function AuthButtons({ className = '', showMainCTA = true }: AuthButtonsProps) {
  const { user, isAuthenticated, isLoading, logout } = useAuth();
  const router = useRouter();

  const handleLogin = () => {
    router.push('/login');
  };

  const handleNewInterview = () => {
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
    return (
      <div className={`flex items-center space-x-3 ${className}`}>
        <UserProfileDropdown
          user={user}
          onLogout={logout}
          isLoading={isLoading}
        />
        {showMainCTA && (
          <Button size="md" onClick={handleNewInterview}>
            New Interview
          </Button>
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