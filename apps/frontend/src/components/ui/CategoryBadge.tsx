interface CategoryBadgeProps {
  category: string;
  className?: string;
}

const categoryStyles: Record<string, string> = {
  scope: 'bg-indigo-50 text-indigo-700 border-indigo-200',
  users: 'bg-blue-50 text-blue-700 border-blue-200',
  constraints: 'bg-amber-50 text-amber-700 border-amber-200',
  nonfunctional: 'bg-purple-50 text-purple-700 border-purple-200',
  interfaces: 'bg-teal-50 text-teal-700 border-teal-200',
  data: 'bg-cyan-50 text-cyan-700 border-cyan-200',
  risks: 'bg-rose-50 text-rose-700 border-rose-200',
  success: 'bg-green-50 text-green-700 border-green-200',
};

export function CategoryBadge({ category, className = '' }: CategoryBadgeProps) {
  const styles = categoryStyles[category] || 'bg-deep-indigo-50 text-deep-indigo-700 border-deep-indigo-200';

  return (
    <span
      className={`inline-flex items-center px-2.5 py-1 text-xs font-medium rounded-full border ${styles} ${className}`}
    >
      {category}
    </span>
  );
}
