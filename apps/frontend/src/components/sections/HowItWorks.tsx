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
            From conversation to specification in 15 minutes. SpecScribe's guided interview ensures nothing is missed—just like working with an experienced business analyst.
          </p>
        </div>
        <ProcessSteps />
        <SampleQuestions />
      </Container>
    </section>
  );
}