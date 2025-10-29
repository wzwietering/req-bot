/**
 * Usage tracking API client
 */

import { apiClient } from "./apiClient";
import type { components } from "@specscribe/shared-types/api";

type UsageStatsResponse = components["schemas"]["UsageStatsResponse"];

export interface UsageStats {
  questionsGenerated: number;
  answersSubmitted: number;
  quotaLimit: number;
  quotaRemaining: number;
  windowDays: number;
  nextQuotaAvailableAt: Date | null;
}

/**
 * Fetches current user's usage statistics
 */
export async function getUserUsage(): Promise<UsageStats> {
  const response = await apiClient.get<UsageStatsResponse>("/api/v1/usage/me");

  return {
    questionsGenerated: response.questions_generated,
    answersSubmitted: response.answers_submitted,
    quotaLimit: response.quota_limit,
    quotaRemaining: response.quota_remaining,
    windowDays: response.window_days,
    nextQuotaAvailableAt: response.next_quota_available_at
      ? new Date(response.next_quota_available_at)
      : null,
  };
}
