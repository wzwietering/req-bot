import React, { forwardRef, TextareaHTMLAttributes } from 'react';

interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
  helperText?: string;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ label, error, helperText, className = '', ...props }, ref) => {
    const baseClasses = `
      w-full px-4 py-3 rounded-lg border
      bg-white text-deep-indigo-500
      focus:outline-2 focus:outline-benzol-green-500
      transition-colors duration-200
      disabled:bg-deep-indigo-50 disabled:cursor-not-allowed
    `;

    const borderClasses = error
      ? 'border-jasper-red-500 focus:border-jasper-red-500'
      : 'border-deep-indigo-200 focus:border-benzol-green-500';

    return (
      <div className="w-full">
        {label && (
          <label className="block text-sm font-medium text-deep-indigo-500 mb-2">
            {label}
          </label>
        )}
        <textarea
          ref={ref}
          className={`${baseClasses} ${borderClasses} ${className}`}
          {...props}
        />
        {error && (
          <p className="mt-2 text-sm text-jasper-red-500">{error}</p>
        )}
        {helperText && !error && (
          <p className="mt-2 text-sm text-deep-indigo-400">{helperText}</p>
        )}
      </div>
    );
  }
);

Textarea.displayName = 'Textarea';
