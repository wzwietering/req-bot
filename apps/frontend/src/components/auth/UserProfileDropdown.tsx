'use client';

import React, { useState, useRef, useEffect } from 'react';
import { FaChevronDown, FaUser, FaSignOutAlt } from 'react-icons/fa';
import { User } from '../../lib/auth/types';

interface UserProfileDropdownProps {
  user: User;
  onLogout: () => Promise<void>;
  isLoading?: boolean;
}

export function UserProfileDropdown({ user, onLogout, isLoading = false }: UserProfileDropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  // Close dropdown on escape key
  useEffect(() => {
    function handleEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setIsOpen(false);
      }
    }

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      return () => {
        document.removeEventListener('keydown', handleEscape);
      };
    }
  }, [isOpen]);

  const handleLogout = async () => {
    try {
      setIsLoggingOut(true);
      await onLogout();
      setIsOpen(false);
    } catch (error) {
      console.error('Logout failed:', error);
    } finally {
      setIsLoggingOut(false);
    }
  };

  const handleToggle = () => {
    if (!isLoading) {
      setIsOpen(!isOpen);
    }
  };

  const displayName = user.name || user.email.split('@')[0];
  const avatarUrl = user.avatar_url;

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Profile Button */}
      <button
        onClick={handleToggle}
        disabled={isLoading}
        className="flex items-center space-x-3 p-2 rounded-lg hover:bg-deep-indigo-50 transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-deep-indigo-500 focus:ring-offset-2 disabled:opacity-50"
        aria-label={isOpen ? 'Close user menu' : 'Open user menu'}
        aria-expanded={isOpen}
        aria-haspopup="true"
      >
        {/* Avatar */}
        <div className="relative">
          {avatarUrl ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={avatarUrl}
              alt={`${displayName}'s avatar`}
              className="w-8 h-8 rounded-full object-cover ring-2 ring-white shadow-sm hover:scale-105 transition-transform duration-200"
            />
          ) : (
            <div className="w-8 h-8 rounded-full bg-deep-indigo-500 flex items-center justify-center text-white font-medium text-sm">
              {displayName.charAt(0).toUpperCase()}
            </div>
          )}
          {isLoading && (
            <div className="absolute inset-0 rounded-full bg-white/80 flex items-center justify-center">
              <div className="w-4 h-4 border-2 border-deep-indigo-500 border-t-transparent rounded-full animate-spin" />
            </div>
          )}
        </div>

        {/* Name and Chevron */}
        <div className="hidden md:flex items-center space-x-2">
          <span className="text-deep-indigo-500 font-medium text-sm max-w-32 truncate">
            {displayName}
          </span>
          <FaChevronDown
            className={`w-3 h-3 text-deep-indigo-400 transition-transform duration-200 ${
              isOpen ? 'rotate-180' : ''
            }`}
          />
        </div>
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-64 bg-white rounded-lg shadow-lg border border-deep-indigo-100 z-50 overflow-hidden backdrop-blur-sm">
          {/* User Info Section */}
          <div className="p-4 border-b border-deep-indigo-100 bg-deep-indigo-25">
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
                <p className="text-xs text-deep-indigo-300 capitalize">
                  {user.provider}
                </p>
              </div>
            </div>
          </div>

          {/* Menu Items */}
          <div className="py-1" role="menu" aria-orientation="vertical">
            {/* Profile/Settings (placeholder for future) */}
            <button
              className="w-full px-4 py-3 text-left text-sm text-deep-indigo-400 hover:bg-deep-indigo-50 hover:text-deep-indigo-500 transition-colors duration-150 flex items-center space-x-3"
              role="menuitem"
              disabled
            >
              <FaUser className="w-4 h-4" />
              <span>Profile Settings</span>
              <span className="ml-auto text-xs text-deep-indigo-300">Soon</span>
            </button>

            {/* Logout */}
            <button
              onClick={handleLogout}
              disabled={isLoggingOut}
              className="w-full px-4 py-3 text-left text-sm text-jasper-red-500 hover:bg-jasper-red-50 transition-colors duration-150 flex items-center space-x-3 disabled:opacity-50 disabled:cursor-not-allowed"
              role="menuitem"
            >
              {isLoggingOut ? (
                <div className="w-4 h-4 border-2 border-jasper-red-500 border-t-transparent rounded-full animate-spin" />
              ) : (
                <FaSignOutAlt className="w-4 h-4" />
              )}
              <span>{isLoggingOut ? 'Signing out...' : 'Sign out'}</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}