import { useState, useCallback } from 'react';
import { sessionsApi } from '@/lib/api/sessions';
import { CharCountColor, ANSWER_CHARACTER_LIMIT, getCharCountColor } from '@/types/form';

interface UseAnswerEditResult {
  isEditing: boolean;
  isSaving: boolean;
  isDeleting: boolean;
  error: string | null;
  editedText: string;
  charCount: number;
  charCountColor: CharCountColor;
  isSaveDisabled: boolean;
  startEdit: (initialText: string) => void;
  updateText: (text: string) => void;
  saveAnswer: () => Promise<void>;
  cancelEdit: () => void;
  deleteAnswer: () => Promise<void>;
  clearError: () => void;
}

export function useAnswerEdit(
  sessionId: string,
  questionId: string,
  onSuccess: () => void
): UseAnswerEditResult {
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editedText, setEditedText] = useState('');

  const charCount = editedText.length;
  const charCountColor = getCharCountColor(charCount, ANSWER_CHARACTER_LIMIT);
  const isSaveDisabled = charCount === 0 || charCount > ANSWER_CHARACTER_LIMIT.max;

  const startEdit = useCallback((initialText: string) => {
    setEditedText(initialText);
    setIsEditing(true);
    setError(null);
  }, []);

  const updateText = useCallback((text: string) => {
    setEditedText(text);
    setError(null);
  }, []);

  const saveAnswer = useCallback(async () => {
    if (isSaveDisabled) return;

    setIsSaving(true);
    setError(null);

    try {
      await sessionsApi.updateAnswer(sessionId, questionId, { text: editedText });
      setIsEditing(false);
      onSuccess();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to save answer';
      setError(message);
      console.error('Failed to save answer:', err);
    } finally {
      setIsSaving(false);
    }
  }, [sessionId, questionId, editedText, isSaveDisabled, onSuccess]);

  const cancelEdit = useCallback(() => {
    setIsEditing(false);
    setEditedText('');
    setError(null);
  }, []);

  const deleteAnswer = useCallback(async () => {
    setIsDeleting(true);
    setError(null);

    try {
      await sessionsApi.deleteAnswer(sessionId, questionId);
      onSuccess();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to delete answer';
      setError(message);
      console.error('Failed to delete answer:', err);
    } finally {
      setIsDeleting(false);
    }
  }, [sessionId, questionId, onSuccess]);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return {
    isEditing,
    isSaving,
    isDeleting,
    error,
    editedText,
    charCount,
    charCountColor,
    isSaveDisabled,
    startEdit,
    updateText,
    saveAnswer,
    cancelEdit,
    deleteAnswer,
    clearError,
  };
}
