'use client';

import { useEffect } from 'react';
import { Button } from './Button';

interface ConfirmDialogProps {
  isOpen: boolean;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  onConfirm: () => void;
  onCancel: () => void;
  error?: string | null;
  isLoading?: boolean;
}

export function ConfirmDialog({
  isOpen,
  title,
  message,
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  onConfirm,
  onCancel,
  error,
  isLoading = false,
}: ConfirmDialogProps) {
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

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      onClick={onCancel}
      role="dialog"
      aria-modal="true"
      aria-labelledby="dialog-title"
    >
      <div
        className="bg-white rounded-lg shadow-xl p-6 max-w-md w-full mx-4"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 id="dialog-title" className="text-xl font-semibold text-deep-indigo-500 mb-2">
          {title}
        </h2>
        <p className="text-base text-deep-indigo-400 mb-6">{message}</p>
        {error && (
          <div className="mb-4 p-3 bg-jasper-red-50 border border-jasper-red-200 rounded-md">
            <p className="text-sm text-jasper-red-700">{error}</p>
          </div>
        )}
        <div className="flex gap-3 justify-end">
          <Button onClick={onCancel} variant="secondary" size="md" disabled={isLoading}>
            {cancelText}
          </Button>
          <Button onClick={onConfirm} variant="primary" size="md" disabled={isLoading}>
            {confirmText}
          </Button>
        </div>
      </div>
    </div>
  );
}
