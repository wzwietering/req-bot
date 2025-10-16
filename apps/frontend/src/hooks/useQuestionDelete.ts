import { useState, useCallback } from 'react';
import { sessionsApi } from '@/lib/api/sessions';

interface UseQuestionDeleteResult {
  isDeleting: boolean;
  error: string | null;
  showConfirm: boolean;
  openConfirm: () => void;
  closeConfirm: () => void;
  deleteQuestion: () => Promise<boolean>;
  clearError: () => void;
}

export function useQuestionDelete(
  sessionId: string,
  questionId: string,
  onSuccess: () => void
): UseQuestionDeleteResult {
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showConfirm, setShowConfirm] = useState(false);

  const openConfirm = useCallback(() => {
    setShowConfirm(true);
    setError(null);
  }, []);

  const closeConfirm = useCallback(() => {
    setShowConfirm(false);
    setError(null);
  }, []);

  const deleteQuestion = useCallback(async (): Promise<boolean> => {
    setIsDeleting(true);
    setError(null);

    try {
      await sessionsApi.deleteQuestion(sessionId, questionId);
      setShowConfirm(false);
      onSuccess();
      return true;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to delete question';
      setError(message);
      console.error('Failed to delete question:', err);
      return false;
    } finally {
      setIsDeleting(false);
    }
  }, [sessionId, questionId, onSuccess]);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return {
    isDeleting,
    error,
    showConfirm,
    openConfirm,
    closeConfirm,
    deleteQuestion,
    clearError,
  };
}
