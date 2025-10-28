"use client";

/**
 * Quota badge component for header notifications
 * Shows remaining quota count with color-coded urgency
 */

import { FiAlertCircle } from "react-icons/fi";

interface QuotaBadgeProps {
  count: number;
  variant: "urgent" | "critical";
  "aria-label"?: string;
  className?: string;
}

const variantStyles = {
  urgent: "bg-amber-500 text-white",
  critical: "bg-jasper-red-600 text-white",
};

export function QuotaBadge({
  count,
  variant,
  "aria-label": ariaLabel,
  className = "",
}: QuotaBadgeProps) {
  return (
    <div
      role="status"
      aria-live="polite"
      aria-label={ariaLabel || `${count} sessions remaining`}
      className={`
        absolute -top-1 -right-1
        flex items-center justify-center
        min-w-[20px] h-5 px-1.5
        rounded-full
        text-xs font-bold
        quota-badge
        ${variantStyles[variant]}
        ${className}
      `}
    >
      {count === 0 ? (
        <FiAlertCircle className="w-3 h-3" aria-hidden="true" />
      ) : (
        <span>{count}</span>
      )}
    </div>
  );
}
