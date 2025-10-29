"use client";

/**
 * Usage indicator component with accessibility support
 * Displays quota usage with icon, color, and text (not relying on color alone)
 */

import { FiCheckCircle, FiInfo, FiAlertTriangle, FiXCircle } from "react-icons/fi";
import { getStatusLabel, calculatePercentUsed, type QuotaStatus } from "@/lib/utils/quota";

interface UsageIndicatorProps {
  current: number;
  total: number;
  status: QuotaStatus;
  variant?: "compact" | "detailed";
  showPercentage?: boolean;
  className?: string;
}

const statusIcons = {
  healthy: FiCheckCircle,
  notice: FiInfo,
  warning: FiAlertTriangle,
  urgent: FiAlertTriangle,
  critical: FiXCircle,
};

const statusColors = {
  healthy: "text-benzol-green-600",
  notice: "text-deep-indigo-500",
  warning: "text-amber-600",
  urgent: "text-amber-700",
  critical: "text-jasper-red-600",
};

const progressBarColors = {
  healthy: "bg-benzol-green-500",
  notice: "bg-deep-indigo-400",
  warning: "bg-amber-500",
  urgent: "bg-amber-600",
  critical: "bg-jasper-red-600",
};

const progressBarPatterns = {
  healthy: "",
  notice: "",
  warning: "bg-stripes", // Diagonal stripes for warning states
  urgent: "bg-stripes",
  critical: "",
};

export function UsageIndicator({
  current,
  total,
  status,
  variant = "detailed",
  showPercentage = false,
  className = "",
}: UsageIndicatorProps) {
  const Icon = statusIcons[status];
  const percentage = calculatePercentUsed(current, total);
  const statusLabel = getStatusLabel(status);

  if (variant === "compact") {
    return (
      <div
        role="status"
        aria-live="polite"
        aria-label={`${percentage}% of quota used. ${total - current} sessions remaining. Status: ${statusLabel}`}
        className={`flex items-center gap-2 ${className}`}
      >
        <Icon className={`w-4 h-4 ${statusColors[status]}`} aria-hidden="true" />
        <span className="text-sm font-medium">
          {current}/{total}
        </span>
        {showPercentage && (
          <span className="text-xs text-gray-500">({percentage}%)</span>
        )}
      </div>
    );
  }

  return (
    <div
      role="status"
      aria-live="polite"
      aria-label={`${percentage}% of quota used. ${total - current} sessions remaining. Status: ${statusLabel}`}
      className={`space-y-2 ${className}`}
    >
      {/* Status label with icon */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Icon className={`w-4 h-4 ${statusColors[status]}`} aria-hidden="true" />
          <span className="text-sm font-medium text-gray-700">
            {statusLabel}
          </span>
        </div>
        <span className="text-sm font-semibold text-gray-900">
          {current}/{total}
        </span>
      </div>

      {/* Progress bar */}
      <div className="relative h-2 bg-gray-200 rounded-full overflow-hidden">
        <div
          className={`h-full transition-all duration-300 ${progressBarColors[status]} ${progressBarPatterns[status]}`}
          style={{ width: `${percentage}%` }}
          role="presentation"
        />
      </div>

      {showPercentage && (
        <p className="text-xs text-gray-500 text-right">
          {percentage}% used
        </p>
      )}
    </div>
  );
}
