import { ReactNode } from 'react';

export interface FeatureCardProps {
  icon: ReactNode;
  title: string;
  description: string;
  iconColor?: 'red' | 'green' | 'indigo';
}

const iconColorClasses = {
  red: 'text-jasper-red-500',
  green: 'text-benzol-green-500',
  indigo: 'text-deep-indigo-500'
};

export function FeatureCard({ icon, title, description, iconColor = 'indigo' }: FeatureCardProps) {
  return (
    <div className="bg-white p-6 rounded-lg border border-deep-indigo-100 hover:border-deep-indigo-200 hover:shadow-lg transition-all duration-200">
      <div className={`w-12 h-12 mb-4 ${iconColorClasses[iconColor]} flex items-center justify-center`}>
        {icon}
      </div>
      <h3 className="text-feature-title text-deep-indigo-500 mb-3">
        {title}
      </h3>
      <p className="text-body text-deep-indigo-300">
        {description}
      </p>
    </div>
  );
}