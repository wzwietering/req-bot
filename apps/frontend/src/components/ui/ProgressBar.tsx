interface ProgressBarProps {
  value: number;
  max: number;
  label?: string;
}

export function ProgressBar({ value, max, label }: ProgressBarProps) {
  const percentage = max > 0 ? Math.round((value / max) * 100) : 0;

  return (
    <div className="w-full">
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
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}
