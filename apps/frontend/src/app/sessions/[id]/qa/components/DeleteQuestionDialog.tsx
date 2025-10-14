'use client';

import { useEffect, useRef } from 'react';
import { Button } from '@/components/ui/Button';

interface DeleteQuestionDialogProps {
  isOpen: boolean;
  questionText: string;
  answerLength: number | null;
  onConfirm: () => void;
  onCancel: () => void;
  error?: string | null;
  isLoading?: boolean;
}

export function DeleteQuestionDialog({
  isOpen,
  questionText,
  answerLength,
  onConfirm,
  onCancel,
  error,
  isLoading = false,
}: DeleteQuestionDialogProps) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);

  // Truncate question text for display
  const truncatedQuestion = questionText.length > 80 ? `${questionText.substring(0, 80)}...` : questionText;

  // Handle escape key
  useEffect(() => {
    if (!isOpen) return;

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !isLoading) {
        onCancel();
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, isLoading, onCancel]);

  // Focus management and trap
  useEffect(() => {
    if (!isOpen) return;

    previousFocusRef.current = document.activeElement as HTMLElement;

    const dialog = dialogRef.current;
    if (dialog) {
      const focusableElements = dialog.querySelectorAll(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      const firstElement = focusableElements[0] as HTMLElement;
      const lastElement = focusableElements[focusableElements.length - 1] as HTMLElement;

      firstElement?.focus();

      const handleTab = (e: KeyboardEvent) => {
        if (e.key !== 'Tab') return;

        if (e.shiftKey) {
          if (document.activeElement === firstElement) {
            e.preventDefault();
            lastElement?.focus();
          }
        } else {
          if (document.activeElement === lastElement) {
            e.preventDefault();
            firstElement?.focus();
          }
        }
      };

      document.addEventListener('keydown', handleTab);

      return () => {
        document.removeEventListener('keydown', handleTab);
        previousFocusRef.current?.focus();
      };
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleBackdropClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget && !isLoading) {
      onCancel();
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      role="dialog"
      aria-modal="true"
      aria-labelledby="dialog-title"
      aria-describedby="dialog-description"
      onClick={handleBackdropClick}
    >
      <div
        ref={dialogRef}
        className="bg-white rounded-lg shadow-xl p-6 max-w-md w-full mx-4"
        role="document"
      >
        <div className="flex items-start justify-between mb-2">
          <h2 id="dialog-title" className="text-xl font-semibold text-jasper-red-600">
            Delete Question?
          </h2>
          <button
            onClick={onCancel}
            disabled={isLoading}
            aria-label="Close dialog"
            className="text-deep-indigo-400 hover:text-deep-indigo-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed p-2 -m-2 min-h-[44px] min-w-[44px] flex items-center justify-center"
          >
            <svg
              className="w-6 h-6"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div id="dialog-description" className="text-base text-deep-indigo-400 mb-4">
          <p className="mb-3 font-medium">This will permanently delete:</p>
          <ul className="space-y-2 ml-4">
            <li className="flex items-start">
              <span className="text-jasper-red-500 mr-2">•</span>
              <span className="flex-1">
                The question: <span className="italic">&ldquo;{truncatedQuestion}&rdquo;</span>
              </span>
            </li>
            {answerLength !== null && (
              <li className="flex items-start">
                <span className="text-jasper-red-500 mr-2">•</span>
                <span className="flex-1">Its answer ({answerLength} characters)</span>
              </li>
            )}
          </ul>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-jasper-red-50 border border-jasper-red-200 rounded-md" role="alert">
            <p className="text-sm text-jasper-red-700">{error}</p>
          </div>
        )}

        <div className="flex gap-3 justify-end">
          <Button onClick={onCancel} variant="secondary" size="md" disabled={isLoading}>
            Cancel
          </Button>
          <Button onClick={onConfirm} variant="danger" size="md" disabled={isLoading}>
            Delete Question & Answer
          </Button>
        </div>
      </div>
    </div>
  );
}
