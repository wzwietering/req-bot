'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Container } from '../ui';
import { AuthButtons, AuthButtonsMobile } from '../auth/AuthButtons';
import { useAuth } from '../auth/AuthProvider';

export function Navigation() {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const { isAuthenticated } = useAuth();

  const navItems = [
    { href: '/#features', label: 'Features' },
    { href: '/#how-it-works', label: 'How It Works' }
  ];

  const authNavItems = [
    { href: '/sessions', label: 'My Sessions' }
  ];

  return (
    <nav className="sticky top-0 z-50 bg-white/95 backdrop-blur-sm border-b border-deep-indigo-100">
      <Container>
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link href="/" className="flex items-center space-x-2">
            <div className="w-8 h-8 bg-jasper-red-500 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-lg">R</span>
            </div>
            <span className="text-xl font-semibold text-deep-indigo-500">
              Requirements Bot
            </span>
          </Link>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center space-x-8">
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="text-deep-indigo-400 hover:text-deep-indigo-500 transition-colors"
              >
                {item.label}
              </Link>
            ))}
            {isAuthenticated && authNavItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="text-deep-indigo-400 hover:text-deep-indigo-500 transition-colors"
              >
                {item.label}
              </Link>
            ))}
          </div>

          {/* Desktop Auth Buttons */}
          <div className="hidden md:block">
            <AuthButtons />
          </div>

          {/* Mobile Menu Button */}
          <button
            className="md:hidden p-2 rounded-md text-deep-indigo-400 hover:text-deep-indigo-500 hover:bg-deep-indigo-50"
            onClick={() => setIsMenuOpen(!isMenuOpen)}
            aria-label={isMenuOpen ? "Close menu" : "Open menu"}
            aria-expanded={isMenuOpen}
            aria-controls="mobile-menu"
          >
            <svg
              className="w-6 h-6"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              {isMenuOpen ? (
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              ) : (
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 6h16M4 12h16M4 18h16"
                />
              )}
            </svg>
          </button>
        </div>

        {/* Mobile Menu */}
        {isMenuOpen && (
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
                  onClick={() => setIsMenuOpen(false)}
                >
                  {item.label}
                </Link>
              ))}
              {isAuthenticated && authNavItems.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className="text-deep-indigo-400 hover:text-deep-indigo-500 transition-colors px-4 py-3 -mx-2 rounded-lg hover:bg-deep-indigo-50 min-h-[44px] flex items-center"
                  onClick={() => setIsMenuOpen(false)}
                >
                  {item.label}
                </Link>
              ))}

              {/* Mobile Auth Section */}
              <div className="pt-4 border-t border-deep-indigo-100">
                <AuthButtonsMobile onMenuClose={() => setIsMenuOpen(false)} />
              </div>
            </div>
          </div>
        )}
      </Container>
    </nav>
  );
}