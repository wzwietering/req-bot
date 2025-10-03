import Link from 'next/link';
import { Button, Container } from '../ui';
import { ShieldIcon, CheckCircleIcon } from '../icons';

export function Hero() {
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
          {/* Badge */}
          <div className="inline-flex items-center px-3 py-1.5 mb-6 md:mb-8 text-xs md:text-sm font-medium text-benzol-green-700 bg-benzol-green-50 border border-benzol-green-200 rounded-full">
            <svg className="w-3 h-3 md:w-4 md:h-4 mr-1.5 md:mr-2" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            AI-Powered Requirements Gathering
          </div>

          {/* Main Headline */}
          <h1 className="text-hero text-deep-indigo-500 mb-6 max-w-4xl mx-auto">
            Stop Gathering{' '}
            <span className="text-jasper-red-500">Incomplete Requirements</span>
          </h1>

          {/* Subheading */}
          <p className="text-lead text-deep-indigo-300 mb-10 max-w-2xl mx-auto">
            AI-powered interviews ensure your development projects start with comprehensive,
            well-documented requirements every time. No more missed details or unclear specifications.
          </p>

          {/* CTAs */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3 sm:gap-4 mb-10 sm:mb-12">
            <Button size="lg" className="w-full sm:w-auto sm:min-w-[200px]">
              Start Your First Interview
            </Button>
            <Link href="#how-it-works">
              <Button variant="secondary" size="lg" className="w-full sm:w-auto sm:min-w-[200px]">
                See How It Works
              </Button>
            </Link>
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