/**
 * Quota-related utility functions
 */

// Time constants
export const MS_PER_HOUR = 60 * 60 * 1000;
export const MS_PER_DAY = 24 * MS_PER_HOUR;

export type QuotaStatus = "healthy" | "notice" | "warning" | "urgent" | "critical";

/**
 * Calculate quota status based on percentage used
 */
export function getQuotaStatus(percentUsed: number): QuotaStatus {
  if (percentUsed >= 100) return "critical";
  if (percentUsed >= 90) return "urgent";
  if (percentUsed >= 80) return "warning";
  if (percentUsed >= 50) return "notice";
  return "healthy";
}

/**
 * Get human-readable status label
 */
export function getStatusLabel(status: QuotaStatus): string {
  const labels: Record<QuotaStatus, string> = {
    healthy: "Healthy usage",
    notice: "Moderate usage",
    warning: "Approaching limit",
    urgent: "Nearly at limit",
    critical: "Quota exceeded",
  };
  return labels[status];
}

/**
 * Format reset date with smart precision based on time remaining.
 * Note: In a rolling window system, this represents when the next
 * quota slot becomes available (when the oldest usage event expires).
 */
export function formatResetDate(date: Date): string {
  const now = new Date();
  const msUntil = date.getTime() - now.getTime();
  const hoursUntil = Math.floor(msUntil / MS_PER_HOUR);
  const daysUntil = Math.floor(msUntil / MS_PER_DAY);

  if (msUntil < 0) {
    return "soon"; // Reset date has passed, should reset soon
  }

  if (hoursUntil < 24) {
    return hoursUntil < 1
      ? "in less than an hour"
      : `in ${hoursUntil} hour${hoursUntil === 1 ? "" : "s"}`;
  }

  if (daysUntil < 2) {
    const hours = date.getHours();
    const minutes = date.getMinutes();
    const ampm = hours >= 12 ? "PM" : "AM";
    const displayHours = hours % 12 || 12;
    const displayMinutes = minutes.toString().padStart(2, "0");
    return `tomorrow at ${displayHours}:${displayMinutes} ${ampm}`;
  }

  if (daysUntil < 7) {
    return `in ${daysUntil} day${daysUntil === 1 ? "" : "s"}`;
  }

  const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  return `on ${months[date.getMonth()]} ${date.getDate()}`;
}

/**
 * Get context-aware upgrade message based on usage pattern
 */
export function getUpgradeMessage(
  percentUsed: number,
  daysIntoWindow: number,
  tier: string
): string {
  if (tier !== "free") return "";

  if (percentUsed >= 100) {
    return "Upgrade now to continue creating interviews immediately";
  }

  // Power user detection: used 80% in less than 7 days
  if (percentUsed >= 80 && daysIntoWindow < 7) {
    return "You're using SpecScribe frequently. Pro tier includes 10,000 sessions/month";
  }

  if (percentUsed >= 80) {
    return "Maximize your workflow with Pro's unlimited sessions";
  }

  return "Pro users get 10,000 questions/month";
}

/**
 * Calculate percentage used with precision
 */
export function calculatePercentUsed(used: number, total: number): number {
  if (total === 0) return 0;
  return Math.min(100, Math.round((used / total) * 100));
}
