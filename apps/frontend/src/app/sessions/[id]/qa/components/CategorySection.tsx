'use client';

import { CategoryGroup, categoryConfig } from '../utils/categoryHelpers';
import { QAPairCard } from './QAPairCard';
import { StatusBadge } from './StatusBadge';

interface CategorySectionProps {
  group: CategoryGroup;
}

function getStatusVariant(answeredCount: number, totalCount: number) {
  if (answeredCount === totalCount) {
    return 'complete';
  }

  if (answeredCount > 0) {
    return 'partial';
  }

  return 'notStarted';
}

export function CategorySection({ group }: CategorySectionProps) {
  const config = categoryConfig[group.category];
  const statusVariant = getStatusVariant(group.answeredCount, group.totalCount);

  return (
    <section
      className={`border-l-4 ${config.borderColor} pl-6 py-4`}
      aria-labelledby={`category-${group.category}`}
    >
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <StatusBadge variant={statusVariant} />
          <h2
            id={`category-${group.category}`}
            className="text-xl font-semibold text-deep-indigo-500"
          >
            {group.label}
          </h2>
          <span className={`px-3 py-1 rounded-full text-sm font-medium ${config.colors}`}>
            {group.answeredCount}/{group.totalCount}
          </span>
        </div>

        <div className="space-y-3">
          {group.pairs.map((pair) => (
            <QAPairCard key={pair.question.id} pair={pair} />
          ))}
        </div>
      </div>
    </section>
  );
}
