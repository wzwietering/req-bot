// Re-export all functions and types for backward compatibility
export { categoryConfig } from '../config/categoryConfig';
export { groupByCategory, calculateProgress, type CategoryGroup } from './categoryGrouping';
export { exportToMarkdown, downloadMarkdownFile } from './markdownExport';
export { copyToClipboard } from './clipboardUtils';
