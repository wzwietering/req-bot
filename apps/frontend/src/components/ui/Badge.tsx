interface BadgeProps {
  variant: 'active' | 'completed' | 'processing' | 'failed';
  children: React.ReactNode;
}

export function Badge({ variant, children }: BadgeProps) {
  const variantStyles = {
    active: 'bg-benzol-green-50 text-benzol-green-700 border-benzol-green-200',
    completed: 'bg-deep-indigo-50 text-deep-indigo-700 border-deep-indigo-200',
    processing: 'bg-amber-50 text-amber-700 border-amber-200',
    failed: 'bg-jasper-red-50 text-jasper-red-800 border-jasper-red-300',
  };

  const dotStyles = {
    active: 'bg-benzol-green-500 animate-pulse',
    completed: '',
    processing: 'bg-amber-500 animate-pulse',
    failed: '',
  };

  return (
    <span
      role="status"
      aria-label={`Session status: ${children}`}
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-full border ${variantStyles[variant]}`}
    >
      {dotStyles[variant] && (
        <span
          className={`w-1.5 h-1.5 rounded-full ${dotStyles[variant]}`}
          aria-hidden="true"
        />
      )}
      {children}
    </span>
  );
}
