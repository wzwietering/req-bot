"use client";

/**
 * Quota banner component for prominent usage warnings
 * Shows dismissible alerts when approaching or exceeding quota limits
 */

import { useState, useEffect } from "react";
import { FiAlertTriangle, FiX } from "react-icons/fi";
import { useQuota } from "@/contexts/QuotaContext";
import { formatResetDate, getUpgradeMessage } from "@/lib/utils/quota";
import { useAuth } from "@/components/auth/AuthProvider";

interface BannerDismissal {
  dismissedAt: string;
  quotaState: "urgent" | "critical";
  suppressUntil: string;
}

const DISMISSAL_KEY = "quota-banner-dismissal";
const DISMISSAL_DURATION_MS = 24 * 60 * 60 * 1000; // 24 hours

function getBannerDismissal(): BannerDismissal | null {
  if (typeof window === "undefined") return null;

  try {
    const stored = localStorage.getItem(DISMISSAL_KEY);
    if (!stored) return null;
    return JSON.parse(stored);
  } catch {
    return null;
  }
}

function setBannerDismissal(state: "urgent" | "critical") {
  if (typeof window === "undefined") return;

  const dismissal: BannerDismissal = {
    dismissedAt: new Date().toISOString(),
    quotaState: state,
    suppressUntil: new Date(Date.now() + DISMISSAL_DURATION_MS).toISOString(),
  };

  localStorage.setItem(DISMISSAL_KEY, JSON.stringify(dismissal));
}

function clearBannerDismissal() {
  if (typeof window === "undefined") return;
  localStorage.removeItem(DISMISSAL_KEY);
}

export function QuotaBanner() {
  const { isUrgent, isCritical, resetDate, usage } = useQuota();
  const { user } = useAuth();
  const [isVisible, setIsVisible] = useState(false);

  const shouldShow = isUrgent || isCritical;
  const currentState = isCritical ? "critical" : "urgent";

  useEffect(() => {
    if (!shouldShow) {
      setIsVisible(false);
      clearBannerDismissal();
      return;
    }

    const dismissal = getBannerDismissal();

    if (!dismissal) {
      setIsVisible(true);
      return;
    }

    const now = new Date();
    const suppressUntil = new Date(dismissal.suppressUntil);

    // Show if state worsened (urgent → critical)
    if (dismissal.quotaState === "urgent" && currentState === "critical") {
      setIsVisible(true);
      clearBannerDismissal();
      return;
    }

    // Show if 24 hours have elapsed
    if (now >= suppressUntil) {
      setIsVisible(true);
      clearBannerDismissal();
      return;
    }

    setIsVisible(false);
  }, [shouldShow, currentState]);

  const handleDismiss = () => {
    setIsVisible(false);
    setBannerDismissal(currentState);
  };

  const handleUpgrade = () => {
    // TODO: Navigate to upgrade page or open upgrade modal
    console.log("Upgrade to Pro clicked");
  };

  if (!isVisible || !resetDate || !usage) {
    return null;
  }

  const tier = user?.tier || "free";
  const daysIntoWindow = Math.floor((Date.now() - (resetDate.getTime() - usage.windowDays * 24 * 60 * 60 * 1000)) / (24 * 60 * 60 * 1000));
  const percentUsed = usage.quotaLimit > 0 ? Math.round(((usage.quotaLimit - usage.quotaRemaining) / usage.quotaLimit) * 100) : 0;
  const upgradeMessage = getUpgradeMessage(percentUsed, daysIntoWindow, tier);

  const bgColor = isCritical ? "bg-jasper-red-50" : "bg-amber-50";
  const borderColor = isCritical ? "border-jasper-red-200" : "border-amber-200";
  const iconColor = isCritical ? "text-jasper-red-600" : "text-amber-600";
  const textColor = isCritical ? "text-jasper-red-900" : "text-amber-900";

  return (
    <section
      role="alert"
      aria-live="assertive"
      aria-labelledby="quota-banner-title"
      className={`w-full border-b ${bgColor} ${borderColor}`}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3">
        <div className="flex items-start gap-4">
          {/* Icon */}
          <FiAlertTriangle
            className={`w-5 h-5 mt-0.5 flex-shrink-0 ${iconColor}`}
            aria-hidden="true"
          />

          {/* Content */}
          <div className="flex-1 min-w-0">
            <h2 id="quota-banner-title" className={`text-sm font-semibold ${textColor}`}>
              {isCritical ? "Quota Exceeded" : "Approaching Quota Limit"}
            </h2>
            <p className={`text-sm ${textColor} mt-1`}>
              {isCritical
                ? `You've used all ${usage.quotaLimit} sessions this month.`
                : `Only ${usage.quotaRemaining} session${usage.quotaRemaining === 1 ? "" : "s"} remaining this month.`}
              {" "}
              <span className="font-medium">
                Resets {formatResetDate(resetDate)}
              </span>
            </p>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-3 flex-shrink-0">
            {tier === "free" && upgradeMessage && (
              <button
                onClick={handleUpgrade}
                className="btn-base btn-md bg-deep-indigo-400 text-white hover:bg-deep-indigo-500"
              >
                Upgrade to Pro
              </button>
            )}

            <button
              onClick={handleDismiss}
              aria-label="Dismiss notification"
              className={`p-2 rounded-md hover:bg-black/5 focus:outline-2 focus:outline-offset-2 focus:outline-current transition-colors ${textColor}`}
            >
              <FiX className="w-5 h-5" aria-hidden="true" />
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
