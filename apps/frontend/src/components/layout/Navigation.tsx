'use client';

import { useState } from 'react';
import { Container } from '../ui';
import { AuthButtons } from '../auth/AuthButtons';
import { useAuth } from '../auth/AuthProvider';
import { NavLogo } from './NavLogo';
import { NavLinks } from './NavLinks';
import { MobileMenuButton } from './MobileMenuButton';
import { MobileMenu } from './MobileMenu';

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
          <NavLogo />

          <div className="hidden md:flex items-center space-x-8">
            <NavLinks items={navItems} />
            {isAuthenticated && <NavLinks items={authNavItems} />}
          </div>

          <div className="hidden md:block">
            <AuthButtons />
          </div>

          <MobileMenuButton isOpen={isMenuOpen} onClick={() => setIsMenuOpen(!isMenuOpen)} />
        </div>

        <MobileMenu
          isOpen={isMenuOpen}
          navItems={navItems}
          authNavItems={authNavItems}
          isAuthenticated={isAuthenticated}
          onClose={() => setIsMenuOpen(false)}
        />
      </Container>
    </nav>
  );
}