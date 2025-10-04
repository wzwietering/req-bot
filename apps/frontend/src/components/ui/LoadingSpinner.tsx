import React from 'react';

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  label?: string;
}

export function LoadingSpinner({ size = 'md', className = '', label }: LoadingSpinnerProps) {
  const sizeClasses = {
    sm: 'w-4 h-4 border-2',
    md: 'w-8 h-8 border-4',
    lg: 'w-12 h-12 border-4',
  };

  return (
    <div className={`flex flex-col items-center justify-center ${className}`}>
      <div
        className={`
          ${sizeClasses[size]}
          border-deep-indigo-200
          border-t-deep-indigo-500
          rounded-full
          animate-spin
        `}
        role="status"
        aria-label={label || 'Loading'}
      />
      {label && (
        <p className="mt-3 text-sm text-deep-indigo-400">{label}</p>
      )}
      <span className="sr-only">{label || 'Loading'}</span>
    </div>
  );
}
