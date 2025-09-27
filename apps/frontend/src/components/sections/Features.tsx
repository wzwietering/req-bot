import { Container } from '../ui';
import { FeatureGrid } from './FeatureGrid';
import { AdditionalBenefits } from './AdditionalBenefits';

export function Features() {
  return (
    <section id="features" className="py-20 bg-white">
      <Container>
        <div className="text-center mb-16">
          <h2 className="text-section-heading text-deep-indigo-500 mb-4">
            Everything you need for better requirements
          </h2>
          <p className="text-lead text-deep-indigo-300 max-w-3xl mx-auto">
            Our AI-powered platform transforms how development teams gather and document project requirements,
            ensuring nothing falls through the cracks.
          </p>
        </div>
        <FeatureGrid />
        <AdditionalBenefits />
      </Container>
    </section>
  );
}