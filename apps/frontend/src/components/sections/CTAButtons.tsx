import Link from 'next/link';
import { Button } from '../ui';

export function CTAButtons() {
  return (
    <div className="mb-8 flex flex-col sm:flex-row items-center justify-center">
      <Link href="/interview/new">
        <Button size="lg" className="min-w-[250px] mb-4 sm:mb-0 sm:mr-4">
          Start Your First Interview
        </Button>
      </Link>
      <Link href="/#how-it-works">
        <Button variant="secondary" size="lg" className="min-w-[200px]">
          See How It Works
        </Button>
      </Link>
    </div>
  );
}