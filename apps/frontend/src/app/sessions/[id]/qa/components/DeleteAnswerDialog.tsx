'use client';

import { ConfirmDialog } from '@/components/ui/ConfirmDialog';

interface DeleteAnswerDialogProps {
  isOpen: boolean;
  answerLength: number;
  onConfirm: () => void;
  onCancel: () => void;
  error?: string | null;
  isLoading?: boolean;
}

export function DeleteAnswerDialog({
  isOpen,
  answerLength,
  onConfirm,
  onCancel,
  error,
  isLoading = false,
}: DeleteAnswerDialogProps) {
  const message = `This will remove the answer (${answerLength} characters) but keep the question.`;

  return (
    <ConfirmDialog
      isOpen={isOpen}
      title="Delete Answer?"
      message={message}
      confirmText="Delete Answer"
      cancelText="Cancel"
      confirmVariant="danger"
      onConfirm={onConfirm}
      onCancel={onCancel}
      error={error}
      isLoading={isLoading}
    />
  );
}
