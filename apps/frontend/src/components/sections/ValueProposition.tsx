import { CheckIcon } from '../icons';

const benefits = [
  {
    title: 'Comprehensive Coverage',
    description: '8 comprehensive question categories ensure every requirement is captured'
  },
  {
    title: 'Professional Documentation',
    description: 'Structured Markdown with prioritized requirements'
  },
  {
    title: 'Adaptive Interview Process',
    description: 'Intelligent follow-ups that dig deeper when answers need clarification'
  }
];

function BenefitItem({ title, description }: { title: string; description: string }) {
  return (
    <div className="flex items-start">
      <div className="w-6 h-6 bg-benzol-green-500 rounded-full flex items-center justify-center mr-3 mt-0.5 flex-shrink-0">
        <CheckIcon className="w-3 h-3 text-white" />
      </div>
      <div>
        <div className="font-medium text-deep-indigo-500 mb-1">{title}</div>
        <div className="text-sm text-deep-indigo-300">{description}</div>
      </div>
    </div>
  );
}

export function ValueProposition() {
  return (
    <div className="bg-white rounded-2xl p-8 shadow-sm border border-deep-indigo-100">
      <h3 className="text-feature-title text-deep-indigo-500 mb-4">
        What you&apos;ll get with SpecScribe:
      </h3>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-left">
        {benefits.map((benefit, index) => (
          <BenefitItem key={index} title={benefit.title} description={benefit.description} />
        ))}
      </div>
    </div>
  );
}