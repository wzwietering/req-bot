interface ProgressBarProps {
  value: number;
  max: number;
  label?: string;
  showPercentage?: boolean;
}

export function ProgressBar({ value, max, label, showPercentage = false }: ProgressBarProps) {
  const percentage = max > 0 ? Math.round((value / max) * 100) : 0;
  const displayPercentage = value > 0 && percentage < 2 ? 2 : percentage;

  return (
    <div className="w-full">
      {showPercentage && (
        <div className="flex justify-between items-center mb-1">
          <span className="text-xs text-deep-indigo-500 font-medium">{percentage}%</span>
        </div>
      )}
      <div
        className="h-1.5 bg-deep-indigo-100 rounded-full overflow-hidden"
        role="progressbar"
        aria-valuenow={percentage}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={label || `Progress: ${percentage}% complete`}
      >
        <div
          className="h-full bg-benzol-green-500 transition-all duration-300"
          style={{ width: `${displayPercentage}%` }}
        />
      </div>
    </div>
  );
}
