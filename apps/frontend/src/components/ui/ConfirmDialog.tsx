'use client';

import { Button } from './Button';

interface ConfirmDialogProps {
  isOpen: boolean;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmDialog({
  isOpen,
  title,
  message,
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
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
        <div className="flex gap-3 justify-end">
          <Button onClick={onCancel} variant="secondary" size="md">
            {cancelText}
          </Button>
          <Button onClick={onConfirm} variant="primary" size="md">
            {confirmText}
          </Button>
        </div>
      </div>
    </div>
  );
}
