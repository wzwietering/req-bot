import { categoryConfig } from '@/app/sessions/[id]/qa/utils/categoryHelpers';
import { Question } from '@/lib/api/types';

interface CategoryBadgeProps {
  category: string;
  className?: string;
}

export function CategoryBadge({ category, className = '' }: CategoryBadgeProps) {
  const config = categoryConfig[category as Question['category']];
  const styles = config?.badgeColors || 'bg-deep-indigo-50 text-deep-indigo-700 border-deep-indigo-200';
  const label = config?.label || category;

  if (!config && process.env.NODE_ENV === 'development') {
    console.warn(`Unknown category: ${category}. Please add to categoryConfig.`);
  }

  return (
    <span
      className={`inline-flex items-center px-2.5 py-1 text-xs font-medium rounded-full border ${styles} ${className}`}
    >
      {label}
    </span>
  );
}
