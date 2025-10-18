'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { Button, Container } from '../ui';
import { ShieldIcon, CheckCircleIcon } from '../icons';

export function Hero() {
  const router = useRouter();
  const [hasSavedSession, setHasSavedSession] = useState(false);

  useEffect(() => {
    const savedSessionId = localStorage.getItem('current-interview-session');
    setHasSavedSession(!!savedSessionId);
  }, []);

  const handleResumeInterview = () => {
    router.push('/interview/new');
  };

  return (
    <section className="relative py-20 lg:py-32 bg-gradient-to-br from-deep-indigo-50 to-white overflow-hidden">
      {/* Background decoration */}
      <div className="absolute inset-0 opacity-10">
        <svg
          className="absolute top-0 left-0 transform -translate-x-1/2 -translate-y-1/2"
          width="404"
          height="404"
          fill="none"
          viewBox="0 0 404 404"
        >
          <defs>
            <pattern
              id="hero-pattern"
              x="0"
              y="0"
              width="20"
              height="20"
              patternUnits="userSpaceOnUse"
            >
              <rect x="0" y="0" width="4" height="4" className="fill-jasper-red-500" />
            </pattern>
          </defs>
          <rect width="404" height="404" fill="url(#hero-pattern)" />
        </svg>
      </div>

      <Container>
        <div className="relative text-center">
          {/* Main Headline */}
          <h1 className="text-hero text-deep-indigo-500 mb-6 max-w-4xl mx-auto">
            Turn Conversations Into Code-Ready Specs
          </h1>

          {/* Subheading */}
          <p className="text-lead text-deep-indigo-300 mb-10 max-w-2xl mx-auto">
            A guided 8-question interview that captures requirements with the precision of a business analyst—in 15 minutes, not hours
          </p>

          {/* CTAs */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3 sm:gap-4 mb-10 sm:mb-12">
            {hasSavedSession ? (
              <>
                <Button size="lg" className="w-full sm:w-auto sm:min-w-[200px]" onClick={handleResumeInterview}>
                  Resume Your Interview
                </Button>
                <Link href="/interview/new" onClick={() => localStorage.removeItem('current-interview-session')}>
                  <Button variant="secondary" size="lg" className="w-full sm:w-auto sm:min-w-[200px]">
                    Start New Interview
                  </Button>
                </Link>
              </>
            ) : (
              <>
                <Link href="/interview/new">
                  <Button size="lg" className="w-full sm:w-auto sm:min-w-[200px]">
                    Start Your First Interview
                  </Button>
                </Link>
                <Link href="#how-it-works">
                  <Button variant="secondary" size="lg" className="w-full sm:w-auto sm:min-w-[200px]">
                    See How It Works
                  </Button>
                </Link>
              </>
            )}
          </div>

          {/* Trust indicators */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 sm:gap-6 text-xs sm:text-sm text-deep-indigo-300">
            <div className="flex items-center">
              <ShieldIcon className="w-4 h-4 mr-2 text-benzol-green-500" />
              Secure OAuth authentication
            </div>
            <div className="flex items-center">
              <CheckCircleIcon className="w-4 h-4 mr-2 text-benzol-green-500" />
              Open source project
            </div>
          </div>
        </div>
      </Container>
    </section>
  );
}