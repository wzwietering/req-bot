import { QuestionAnswerPair, Question } from '@/lib/api/types';

export interface CategoryGroup {
  category: Question['category'];
  label: string;
  pairs: QuestionAnswerPair[];
  answeredCount: number;
  totalCount: number;
}

export const categoryConfig: Record<
  Question['category'],
  { label: string; colors: string; borderColor: string; badgeColors: string }
> = {
  scope: {
    label: 'Project Scope',
    colors: 'bg-indigo-100 text-indigo-700',
    borderColor: 'border-l-indigo-500',
    badgeColors: 'bg-indigo-50 text-indigo-700 border-indigo-200',
  },
  users: {
    label: 'Users & Stakeholders',
    colors: 'bg-purple-100 text-purple-700',
    borderColor: 'border-l-purple-500',
    badgeColors: 'bg-purple-50 text-purple-700 border-purple-200',
  },
  constraints: {
    label: 'Constraints',
    colors: 'bg-amber-100 text-amber-800',
    borderColor: 'border-l-amber-500',
    badgeColors: 'bg-amber-50 text-amber-700 border-amber-200',
  },
  nonfunctional: {
    label: 'Non-Functional Requirements',
    colors: 'bg-blue-100 text-blue-700',
    borderColor: 'border-l-blue-500',
    badgeColors: 'bg-blue-50 text-blue-700 border-blue-200',
  },
  interfaces: {
    label: 'Interfaces & Integrations',
    colors: 'bg-teal-100 text-teal-700',
    borderColor: 'border-l-teal-500',
    badgeColors: 'bg-teal-50 text-teal-700 border-teal-200',
  },
  data: {
    label: 'Data Requirements',
    colors: 'bg-cyan-100 text-cyan-800',
    borderColor: 'border-l-cyan-500',
    badgeColors: 'bg-cyan-50 text-cyan-700 border-cyan-200',
  },
  risks: {
    label: 'Risks & Assumptions',
    colors: 'bg-orange-100 text-orange-700',
    borderColor: 'border-l-orange-500',
    badgeColors: 'bg-rose-50 text-rose-700 border-rose-200',
  },
  success: {
    label: 'Success Criteria',
    colors: 'bg-benzol-green-100 text-benzol-green-700',
    borderColor: 'border-l-benzol-green-500',
    badgeColors: 'bg-green-50 text-green-700 border-green-200',
  },
};

/**
 * Groups Q&A pairs by category and returns them in a predefined order.
 *
 * Order follows the natural flow of requirements gathering:
 * scope → users → constraints → nonfunctional → interfaces → data → risks → success criteria
 *
 * Empty categories are filtered out to reduce visual clutter.
 */
export function groupByCategory(pairs: QuestionAnswerPair[]): CategoryGroup[] {
  const groups: Record<Question['category'], QuestionAnswerPair[]> = {
    scope: [],
    users: [],
    constraints: [],
    nonfunctional: [],
    interfaces: [],
    data: [],
    risks: [],
    success: [],
  };

  pairs.forEach((pair) => {
    const category = pair.question.category;
    if (groups[category]) {
      groups[category].push(pair);
    }
  });

  const categoryOrder: Question['category'][] = [
    'scope',
    'users',
    'constraints',
    'nonfunctional',
    'interfaces',
    'data',
    'risks',
    'success',
  ];

  return categoryOrder
    .map((category) => {
      const categoryPairs = groups[category];
      const answeredCount = categoryPairs.filter((pair) => pair.answer !== null).length;

      return {
        category,
        label: categoryConfig[category].label,
        pairs: categoryPairs,
        answeredCount,
        totalCount: categoryPairs.length,
      };
    })
    .filter((group) => group.totalCount > 0);
}

export function calculateProgress(pairs: QuestionAnswerPair[]): {
  answered: number;
  total: number;
  percentage: number;
} {
  const total = pairs.length;
  const answered = pairs.filter((pair) => pair.answer !== null).length;
  const percentage = total > 0 ? Math.round((answered / total) * 100) : 0;

  return { answered, total, percentage };
}

/**
 * Downloads a text file to the user's device.
 * Handles blob creation, DOM manipulation, and cleanup.
 * Guarantees URL cleanup even if download fails.
 */
export function downloadMarkdownFile(filename: string, content: string): void {
  let url: string | null = null;

  try {
    const blob = new Blob([content], { type: 'text/markdown' });
    url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  } finally {
    if (url) {
      URL.revokeObjectURL(url);
    }
  }
}

export function exportToMarkdown(
  sessionName: string,
  pairs: QuestionAnswerPair[]
): string {
  const groups = groupByCategory(pairs);
  const lines: string[] = [];

  lines.push(`# ${sessionName} - Q&A Summary`);
  lines.push('');
  lines.push(`Generated: ${new Date().toLocaleDateString()}`);
  lines.push('');

  groups.forEach((group) => {
    lines.push(`## ${group.label} (${group.answeredCount}/${group.totalCount} answered)`);
    lines.push('');

    group.pairs.forEach((pair) => {
      lines.push(`### Q: ${pair.question.text}`);
      if (pair.question.required) {
        lines.push('*Required*');
      }
      lines.push('');
      lines.push(`**A:** ${pair.answer?.text || '*Not answered yet*'}`);
      lines.push('');
    });
  });

  return lines.join('\n');
}

/**
 * Fallback copy method for browsers without Clipboard API.
 * Uses deprecated execCommand as last resort.
 */
function fallbackCopyToClipboard(text: string): Promise<void> {
  const textArea = document.createElement('textarea');
  textArea.value = text;
  textArea.style.position = 'fixed';
  textArea.style.left = '-999999px';
  document.body.appendChild(textArea);
  textArea.select();

  try {
    document.execCommand('copy');
    document.body.removeChild(textArea);
    return Promise.resolve();
  } catch (err) {
    document.body.removeChild(textArea);
    return Promise.reject(err);
  }
}

export function copyToClipboard(text: string): Promise<void> {
  if (navigator.clipboard?.writeText) {
    return navigator.clipboard.writeText(text);
  }
  return fallbackCopyToClipboard(text);
}
