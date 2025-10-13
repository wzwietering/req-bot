import { QuestionAnswerPair } from '@/lib/api/types';
import { groupByCategory, CategoryGroup } from './categoryGrouping';

function buildHeader(sessionName: string): string[] {
  return [
    `# ${sessionName} - Q&A Summary`,
    '',
    `Generated: ${new Date().toLocaleDateString()}`,
    '',
  ];
}

function formatQuestion(pair: QuestionAnswerPair): string[] {
  const lines = [`### Q: ${pair.question.text}`];

  if (pair.question.required) {
    lines.push('*Required*');
  }

  return lines;
}

function formatAnswer(pair: QuestionAnswerPair): string {
  return pair.answer?.text || '*Not answered yet*';
}

function formatQAPair(pair: QuestionAnswerPair): string[] {
  const lines = [
    ...formatQuestion(pair),
    '',
    `**A:** ${formatAnswer(pair)}`,
    '',
  ];

  return lines;
}

function formatCategorySection(group: CategoryGroup): string[] {
  const header = `## ${group.label} (${group.answeredCount}/${group.totalCount} answered)`;
  const lines = [header, ''];

  group.pairs.forEach((pair) => {
    lines.push(...formatQAPair(pair));
  });

  return lines;
}

export function exportToMarkdown(
  sessionName: string,
  pairs: QuestionAnswerPair[]
): string {
  const groups = groupByCategory(pairs);
  const lines: string[] = buildHeader(sessionName);

  groups.forEach((group) => {
    lines.push(...formatCategorySection(group));
  });

  return lines.join('\n');
}

/**
 * Downloads a text file to the user's device.
 * Handles blob creation, DOM manipulation, and cleanup.
 * Guarantees URL and DOM cleanup even if download fails.
 */
export function downloadMarkdownFile(filename: string, content: string): void {
  let url: string | null = null;
  let anchor: HTMLAnchorElement | null = null;

  try {
    const blob = new Blob([content], { type: 'text/markdown' });
    url = URL.createObjectURL(blob);
    anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
  } finally {
    if (anchor && document.body.contains(anchor)) {
      document.body.removeChild(anchor);
    }
    if (url) {
      URL.revokeObjectURL(url);
    }
  }
}
