'use client';

import { CategoryGroup, categoryConfig } from '../utils/categoryHelpers';
import { QAPairCard } from './QAPairCard';

interface CategorySectionProps {
  group: CategoryGroup;
}

export function CategorySection({ group }: CategorySectionProps) {
  const config = categoryConfig[group.category];
  const isComplete = group.answeredCount === group.totalCount;
  const isPartial = group.answeredCount > 0 && group.answeredCount < group.totalCount;

  const statusIndicator = isComplete ? (
    <span
      className="inline-flex h-2 w-2 rounded-full bg-benzol-green-500"
      aria-label="All answered"
      title="All questions in this category are answered"
    />
  ) : isPartial ? (
    <span
      className="inline-flex h-2 w-2 rounded-full bg-amber-500"
      aria-label="Partially answered"
      title="Some questions in this category are answered"
    />
  ) : (
    <span
      className="inline-flex h-2 w-2 rounded-full bg-jasper-red-500"
      aria-label="Not answered"
      title="No questions in this category are answered yet"
    />
  );

  return (
    <section
      className={`border-l-4 ${config.borderColor} pl-6 py-4`}
      aria-labelledby={`category-${group.category}`}
    >
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          {statusIndicator}
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
