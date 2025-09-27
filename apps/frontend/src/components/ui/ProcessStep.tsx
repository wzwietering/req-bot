import { ReactNode } from 'react';

export interface ProcessStepProps {
  step: number;
  title: string;
  description: string;
  icon?: ReactNode;
  isLast?: boolean;
}

export function ProcessStep({ step, title, description, icon }: ProcessStepProps) {
  return (
    <div className="relative flex flex-col items-center text-center">
      {/* Step Number Circle */}
      <div className="relative z-10 w-16 h-16 bg-benzol-green-500 rounded-full flex items-center justify-center mb-4">
        {icon ? (
          <span className="text-white text-xl">{icon}</span>
        ) : (
          <span className="text-white font-semibold text-lg">{step}</span>
        )}
      </div>

      {/* Content */}
      <h3 className="text-feature-title text-deep-indigo-500 mb-2">
        {title}
      </h3>
      <p className="text-body text-deep-indigo-300 max-w-xs">
        {description}
      </p>
    </div>
  );
}