import { BenefitStats } from './BenefitStats';

export function AdditionalBenefits() {
  return (
    <div className="mt-16 bg-deep-indigo-50 rounded-2xl p-8">
      <div className="text-center mb-8">
        <h3 className="text-feature-title text-deep-indigo-500 mb-2">
          Built for development teams
        </h3>
        <p className="text-body text-deep-indigo-300">
          SpecScribe integrates seamlessly into your existing workflow
        </p>
      </div>
      <BenefitStats />
    </div>
  );
}