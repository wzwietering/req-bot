import { QuestionAnswerPair, Question } from '@/lib/api/types';
import { categoryConfig } from '../config/categoryConfig';

export interface CategoryGroup {
  category: Question['category'];
  label: string;
  pairs: QuestionAnswerPair[];
  answeredCount: number;
  totalCount: number;
}

const CATEGORY_ORDER: Question['category'][] = [
  'scope',
  'users',
  'constraints',
  'nonfunctional',
  'interfaces',
  'data',
  'risks',
  'success',
];

function initializeGroups(): Record<Question['category'], QuestionAnswerPair[]> {
  return {
    scope: [],
    users: [],
    constraints: [],
    nonfunctional: [],
    interfaces: [],
    data: [],
    risks: [],
    success: [],
  };
}

function categorizePairs(pairs: QuestionAnswerPair[]): Record<Question['category'], QuestionAnswerPair[]> {
  const groups = initializeGroups();

  pairs.forEach((pair) => {
    const category = pair.question.category;
    if (groups[category]) {
      groups[category].push(pair);
    }
  });

  return groups;
}

function countAnswered(pairs: QuestionAnswerPair[]): number {
  return pairs.filter((pair) => pair.answer !== null).length;
}

function buildCategoryGroup(
  category: Question['category'],
  pairs: QuestionAnswerPair[]
): CategoryGroup {
  return {
    category,
    label: categoryConfig[category].label,
    pairs,
    answeredCount: countAnswered(pairs),
    totalCount: pairs.length,
  };
}

/**
 * Groups Q&A pairs by category and returns them in a predefined order.
 *
 * Order follows the natural flow of requirements gathering:
 * scope → users → constraints → nonfunctional → interfaces → data → risks → success criteria
 *
 * Empty categories are filtered out to reduce visual clutter.
 */
export function groupByCategory(pairs: QuestionAnswerPair[]): CategoryGroup[] {
  const groups = categorizePairs(pairs);

  return CATEGORY_ORDER
    .map((category) => buildCategoryGroup(category, groups[category]))
    .filter((group) => group.totalCount > 0);
}

export function calculateProgress(pairs: QuestionAnswerPair[]): {
  answered: number;
  total: number;
  percentage: number;
} {
  const total = pairs.length;
  const answered = countAnswered(pairs);
  const percentage = total > 0 ? Math.round((answered / total) * 100) : 0;

  return { answered, total, percentage };
}
