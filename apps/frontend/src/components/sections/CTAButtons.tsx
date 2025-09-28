import { Button } from '../ui';

export function CTAButtons() {
  return (
    <div className="mb-8 flex flex-col sm:flex-row items-center justify-center">
      <Button size="lg" className="min-w-[250px] mb-4 sm:mb-0 sm:mr-4">
        Start Your First Interview
      </Button>
      <Button variant="secondary" size="lg" className="min-w-[200px]">
        Learn More
      </Button>
    </div>
  );
}