'use client';

import { useEffect } from 'react';
import Link from 'next/link';
import { AuthButtonsMobile } from '../auth/AuthButtons';

interface NavItem {
  href: string;
  label: string;
}

interface MobileMenuProps {
  isOpen: boolean;
  navItems: NavItem[];
  authNavItems: NavItem[];
  isAuthenticated: boolean;
  onClose: () => void;
}

export function MobileMenu({ isOpen, navItems, authNavItems, isAuthenticated, onClose }: MobileMenuProps) {
  // Handle escape key
  useEffect(() => {
    if (!isOpen) return;

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      id="mobile-menu"
      className="md:hidden py-4 border-t border-deep-indigo-100"
      role="navigation"
      aria-label="Mobile navigation menu"
    >
      <div className="flex flex-col space-y-4">
        {navItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className="text-deep-indigo-400 hover:text-deep-indigo-500 transition-colors px-4 py-3 -mx-2 rounded-lg hover:bg-deep-indigo-50 min-h-[44px] flex items-center"
            onClick={onClose}
          >
            {item.label}
          </Link>
        ))}
        {isAuthenticated && authNavItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className="text-deep-indigo-400 hover:text-deep-indigo-500 transition-colors px-4 py-3 -mx-2 rounded-lg hover:bg-deep-indigo-50 min-h-[44px] flex items-center"
            onClick={onClose}
          >
            {item.label}
          </Link>
        ))}

        <div className="pt-4 border-t border-deep-indigo-100">
          <AuthButtonsMobile onMenuClose={onClose} />
        </div>
      </div>
    </div>
  );
}
