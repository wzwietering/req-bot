"use client";

/**
 * Quota tracking context for centralized usage state management
 */

import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  type ReactNode,
} from "react";
import { getUserUsage, type UsageStats } from "@/lib/api/usage";
import { useAuth } from "@/components/auth/AuthProvider";
import {
  calculatePercentUsed,
  getQuotaStatus,
  type QuotaStatus,
} from "@/lib/utils/quota";

interface QuotaContextValue {
  usage: UsageStats | null;
  isLoading: boolean;
  error: Error | null;
  status: QuotaStatus;
  isHealthy: boolean;
  isNotice: boolean;
  isWarning: boolean;
  isUrgent: boolean;
  isCritical: boolean;
  canCreateSession: boolean;
  percentUsed: number;
  resetDate: Date | null;
  refetch: () => Promise<void>;
}

const QuotaContext = createContext<QuotaContextValue | undefined>(undefined);

interface QuotaProviderProps {
  children: ReactNode;
}

export function QuotaProvider({ children }: QuotaProviderProps) {
  const { isAuthenticated, user } = useAuth();
  const [usage, setUsage] = useState<UsageStats | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchUsage = useCallback(async () => {
    if (!isAuthenticated || !user) {
      setUsage(null);
      setError(null);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const data = await getUserUsage();
      setUsage(data);
    } catch (err) {
      setError(err instanceof Error ? err : new Error("Failed to fetch usage data"));
    } finally {
      setIsLoading(false);
    }
  }, [isAuthenticated, user]);

  // Fetch usage on mount and when authentication changes
  useEffect(() => {
    fetchUsage();
  }, [fetchUsage]);

  // Listen for quota events (e.g., after creating a session or hitting quota)
  useEffect(() => {
    const handleQuotaUpdate = () => {
      fetchUsage();
    };

    // Custom event for quota changes
    window.addEventListener('quota-update', handleQuotaUpdate);

    return () => {
      window.removeEventListener('quota-update', handleQuotaUpdate);
    };
  }, [fetchUsage]);

  // Calculate derived values
  const percentUsed = usage
    ? calculatePercentUsed(
        usage.quotaLimit - usage.quotaRemaining,
        usage.quotaLimit
      )
    : 0;

  const status = getQuotaStatus(percentUsed);

  const isHealthy = status === "healthy";
  const isNotice = status === "notice";
  const isWarning = status === "warning";
  const isUrgent = status === "urgent";
  const isCritical = status === "critical";
  const canCreateSession = !isCritical;

  // Calculate reset date (assuming rolling 30-day window from now)
  const resetDate = usage
    ? new Date(Date.now() + usage.windowDays * 24 * 60 * 60 * 1000)
    : null;

  const value: QuotaContextValue = {
    usage,
    isLoading,
    error,
    status,
    isHealthy,
    isNotice,
    isWarning,
    isUrgent,
    isCritical,
    canCreateSession,
    percentUsed,
    resetDate,
    refetch: fetchUsage,
  };

  return (
    <QuotaContext.Provider value={value}>{children}</QuotaContext.Provider>
  );
}

export function useQuota(): QuotaContextValue {
  const context = useContext(QuotaContext);
  if (context === undefined) {
    throw new Error("useQuota must be used within a QuotaProvider");
  }
  return context;
}
