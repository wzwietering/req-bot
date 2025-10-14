import { useState, useCallback } from 'react';
import { sessionsApi } from '@/lib/api/sessions';
import { Question } from '@/lib/api/types';
import { CharCountColor, QUESTION_CHARACTER_LIMIT, getCharCountColor } from '@/types/form';

interface QuestionFormData {
  text: string;
  category: Question['category'];
  required: boolean;
}

interface UseQuestionCreateResult {
  isCreating: boolean;
  error: string | null;
  showForm: boolean;
  formData: QuestionFormData;
  charCount: number;
  charCountColor: CharCountColor;
  isCreateDisabled: boolean;
  openForm: (category: Question['category']) => void;
  closeForm: () => void;
  updateText: (text: string) => void;
  updateRequired: (required: boolean) => void;
  createQuestion: () => Promise<void>;
  clearError: () => void;
}

export function useQuestionCreate(
  sessionId: string,
  onSuccess: () => void
): UseQuestionCreateResult {
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState<QuestionFormData>({
    text: '',
    category: 'scope',
    required: true,
  });

  const charCount = formData.text.length;
  const charCountColor = getCharCountColor(charCount, QUESTION_CHARACTER_LIMIT);
  const isCreateDisabled = charCount === 0 || charCount > QUESTION_CHARACTER_LIMIT.max;

  const openForm = useCallback((category: Question['category']) => {
    setFormData({
      text: '',
      category,
      required: true,
    });
    setShowForm(true);
    setError(null);
  }, []);

  const closeForm = useCallback(() => {
    const UNSAVED_CHANGES_THRESHOLD = 50;
    const trimmedText = formData.text.trim();

    if (trimmedText.length > UNSAVED_CHANGES_THRESHOLD) {
      const confirmed = window.confirm(
        'You have unsaved changes. Are you sure you want to discard them?'
      );
      if (!confirmed) return;
    }

    setShowForm(false);
    setFormData({
      text: '',
      category: 'scope',
      required: true,
    });
    setError(null);
  }, [formData.text]);

  const updateText = useCallback((text: string) => {
    setFormData((prev) => ({ ...prev, text }));
    setError(null);
  }, []);

  const updateRequired = useCallback((required: boolean) => {
    setFormData((prev) => ({ ...prev, required }));
  }, []);

  const createQuestion = useCallback(async () => {
    if (isCreateDisabled) return;

    setIsCreating(true);
    setError(null);

    try {
      await sessionsApi.createQuestion(sessionId, formData);
      setShowForm(false);
      setFormData({
        text: '',
        category: 'scope',
        required: true,
      });
      onSuccess();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to create question';
      setError(message);
      console.error('Failed to create question:', err);
    } finally {
      setIsCreating(false);
    }
  }, [sessionId, formData, isCreateDisabled, onSuccess]);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return {
    isCreating,
    error,
    showForm,
    formData,
    charCount,
    charCountColor,
    isCreateDisabled,
    openForm,
    closeForm,
    updateText,
    updateRequired,
    createQuestion,
    clearError,
  };
}
