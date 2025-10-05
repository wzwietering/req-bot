interface BadgeProps {
  variant: 'active' | 'completed' | 'processing' | 'failed';
  children: React.ReactNode;
}

export function Badge({ variant, children }: BadgeProps) {
  const variantStyles = {
    active: 'bg-benzol-green-50 text-benzol-green-700 border-benzol-green-200',
    completed: 'bg-deep-indigo-50 text-deep-indigo-700 border-deep-indigo-200',
    processing: 'bg-jasper-red-50 text-jasper-red-700 border-jasper-red-200',
    failed: 'bg-jasper-red-50 text-jasper-red-800 border-jasper-red-300',
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium uppercase rounded-full border ${variantStyles[variant]}`}
    >
      <span
        className={`w-1.5 h-1.5 rounded-full ${
          variant === 'active' ? 'bg-benzol-green-500 animate-pulse' : ''
        } ${variant === 'processing' ? 'bg-jasper-red-500 animate-pulse' : ''}`}
        aria-hidden="true"
      />
      {children}
    </span>
  );
}
