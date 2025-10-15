import { useState, useCallback } from 'react';
import { sessionsApi } from '@/lib/api/sessions';
import { CharCountColor, ANSWER_CHARACTER_LIMIT, getCharCountColor } from '@/types/form';
import { UNSAVED_CHANGES_THRESHOLD } from '@/constants/ui';
import { validateAnswer, sanitizeInput } from '@/lib/utils/validation';

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
  deleteAnswer: () => Promise<boolean>;
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
  const [originalText, setOriginalText] = useState('');

  const charCount = editedText.length;
  const charCountColor = getCharCountColor(charCount, ANSWER_CHARACTER_LIMIT);
  const isSaveDisabled = charCount === 0 || charCount > ANSWER_CHARACTER_LIMIT.max;

  const startEdit = useCallback((initialText: string) => {
    setEditedText(initialText);
    setOriginalText(initialText);
    setIsEditing(true);
    setError(null);
  }, []);

  const updateText = useCallback((text: string) => {
    setEditedText(text);
    setError(null);
  }, []);

  const saveAnswer = useCallback(async () => {
    if (isSaveDisabled) return;

    const validation = validateAnswer(editedText);
    if (!validation.isValid) {
      setError(validation.error);
      return;
    }

    setIsSaving(true);
    setError(null);

    try {
      const sanitized = sanitizeInput(editedText);
      await sessionsApi.updateAnswer(sessionId, questionId, { text: sanitized });
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
    const trimmedText = editedText.trim();
    const trimmedOriginal = originalText.trim();
    const hasChanges = trimmedText !== trimmedOriginal;

    if (hasChanges && trimmedText.length > UNSAVED_CHANGES_THRESHOLD) {
      const confirmed = window.confirm(
        'You have unsaved changes. Are you sure you want to discard them?'
      );
      if (!confirmed) return;
    }

    setIsEditing(false);
    setEditedText('');
    setOriginalText('');
    setError(null);
  }, [editedText, originalText]);

  const deleteAnswer = useCallback(async (): Promise<boolean> => {
    setIsDeleting(true);
    setError(null);

    try {
      await sessionsApi.deleteAnswer(sessionId, questionId);
      onSuccess();
      return true;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to delete answer';
      setError(message);
      console.error('Failed to delete answer:', err);
      return false;
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
