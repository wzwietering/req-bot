import { Container } from '../ui';
import { ProcessSteps } from './ProcessSteps';
import { SampleQuestions } from './SampleQuestions';

export function HowItWorks() {
  return (
    <section id="how-it-works" className="py-20 bg-deep-indigo-50">
      <Container>
        <div className="text-center mb-16">
          <h2 className="text-section-heading text-deep-indigo-500 mb-4">
            How It Works
          </h2>
          <p className="text-lead text-deep-indigo-300 max-w-2xl mx-auto">
            Get from idea to comprehensive requirements in three simple steps.
            Our AI guides you through the entire process.
          </p>
        </div>
        <ProcessSteps />
        <SampleQuestions />
      </Container>
    </section>
  );
}