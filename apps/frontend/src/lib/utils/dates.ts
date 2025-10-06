// Time constants
const MS_PER_MINUTE = 60_000;
const MS_PER_HOUR = 3_600_000;
const MS_PER_DAY = 86_400_000;

/**
 * Validates and parses a date string.
 *
 * @param dateString - ISO 8601 date string or valid date format
 * @returns Parsed Date object or null if invalid
 *
 * @example
 * const date = parseAndValidateDate('2024-01-15T10:30:00Z');
 * if (!date) {
 *   console.error('Invalid date');
 * }
 */
function parseAndValidateDate(dateString: string): Date | null {
  if (!dateString) {
    return null;
  }

  const date = new Date(dateString);
  if (isNaN(date.getTime())) {
    if (process.env.NODE_ENV === 'development') {
      console.warn(`Invalid date string: ${dateString}`);
    }
    return null;
  }

  return date;
}

/**
 * Format date for display with smart relative/absolute formatting.
 *
 * @param dateString - ISO 8601 date string
 * @returns Formatted date string or error message
 *
 * @example
 * formatDate('2024-01-15T10:30:00Z') // "2 hours ago" or "Jan 15"
 */
export function formatDate(dateString: string): string {
  const date = parseAndValidateDate(dateString);
  if (!date) return 'Invalid date';

  const now = new Date();
  const diffMs = now.getTime() - date.getTime();

  // Handle future dates
  if (diffMs < 0) return 'In the future';

  const diffMins = Math.floor(diffMs / MS_PER_MINUTE);
  const diffHours = Math.floor(diffMs / MS_PER_HOUR);
  const diffDays = Math.floor(diffMs / MS_PER_DAY);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins} minute${diffMins === 1 ? '' : 's'} ago`;
  if (diffHours < 24) return `${diffHours} hour${diffHours === 1 ? '' : 's'} ago`;
  if (diffDays < 7) return `${diffDays} day${diffDays === 1 ? '' : 's'} ago`;

  const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const month = monthNames[date.getMonth()];
  const day = date.getDate();
  const year = date.getFullYear();

  if (diffDays < 30) return `${month} ${day}`;
  if (year === now.getFullYear()) return `${month} ${day}`;
  return `${month} ${day}, ${year}`;
}

/**
 * Format date as relative time for recent dates.
 *
 * @param dateString - ISO 8601 date string
 * @returns Short relative time format or falls back to formatDate
 *
 * @example
 * formatRelativeDate('2024-01-15T10:30:00Z') // "2h ago" or "Jan 15"
 */
export function formatRelativeDate(dateString: string): string {
  const date = parseAndValidateDate(dateString);
  if (!date) return 'Invalid date';

  const now = new Date();
  const diffMs = now.getTime() - date.getTime();

  if (diffMs < 0) return 'In the future';

  const diffHours = Math.floor(diffMs / MS_PER_HOUR);

  if (diffHours < 1) return 'Just now';
  if (diffHours < 24) return `${diffHours}h ago`;
  return formatDate(dateString);
}
