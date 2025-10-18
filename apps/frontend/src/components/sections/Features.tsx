import { Container } from '../ui';
import { FeatureGrid } from './FeatureGrid';
import { AdditionalBenefits } from './AdditionalBenefits';

export function Features() {
  return (
    <section id="features" className="py-20 bg-white">
      <Container>
        <div className="text-center mb-16">
          <h2 className="text-section-heading text-deep-indigo-500 mb-4">
            The Features of a Professional Business Analyst
          </h2>
          <p className="text-lead text-deep-indigo-300 max-w-3xl mx-auto">
            SpecScribe conducts intelligent interviews using 8 comprehensive question categories,
            ensuring every project starts with a clear, actionable blueprint.
          </p>
        </div>
        <FeatureGrid />
        <AdditionalBenefits />
      </Container>
    </section>
  );
}