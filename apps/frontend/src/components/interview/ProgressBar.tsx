import React from 'react';

interface ProgressBarProps {
  current: number;
  total: number;
  percentage: number;
}

export function ProgressBar({ current, total, percentage }: ProgressBarProps) {
  const remaining = total - current;
  const estimatedMinutesRemaining = Math.ceil(remaining * 1.5);

  return (
    <div className="w-full">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1 sm:gap-0 mb-3">
        <div className="text-sm">
          <span className="font-semibold text-deep-indigo-500">{current}</span>
          <span className="text-deep-indigo-400"> of {total} questions</span>
        </div>
        {remaining > 0 && (
          <span className="text-xs sm:text-sm text-deep-indigo-400">
            ~{estimatedMinutesRemaining} min remaining
          </span>
        )}
      </div>

      <div className="w-full h-3 bg-deep-indigo-100 rounded-full overflow-hidden shadow-inner">
        <div
          className="h-full bg-gradient-to-r from-benzol-green-500 to-benzol-green-400 transition-all duration-500 ease-out shadow-sm"
          style={{ width: `${percentage}%` }}
          role="progressbar"
          aria-valuenow={percentage}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={`Interview progress: ${current} of ${total} questions completed, ${percentage}% done`}
        />
      </div>

      <div className="text-xs text-deep-indigo-400 mt-2 text-right font-medium">
        {percentage.toFixed(0)}% complete
      </div>
    </div>
  );
}
