'use client';

import { Button } from '@/components/ui/Button';
import { Textarea } from '@/components/ui/Textarea';
import { FiEdit2, FiTrash2 } from 'react-icons/fi';
import { CharCountColor, ANSWER_CHARACTER_LIMIT } from '@/types/form';
import { CHAR_COUNT_COLOR_CLASSES } from '@/constants/ui';

function handleFormKeyDown(
  e: React.KeyboardEvent<HTMLTextAreaElement>,
  isLoading: boolean,
  isDisabled: boolean,
  onCancel: () => void,
  onSubmit: () => void
) {
  if (e.key === 'Escape' && !isLoading) {
    e.preventDefault();
    onCancel();
  }
  if ((e.metaKey || e.ctrlKey) && e.key === 'Enter' && !isDisabled && !isLoading) {
    e.preventDefault();
    onSubmit();
  }
}

function getCharCountMessage(charCount: number, maxLimit: number): string {
  if (charCount <= maxLimit) {
    const remaining = maxLimit - charCount;
    return `Approaching character limit (${remaining} remaining)`;
  }
  const exceeded = charCount - maxLimit;
  return `Character limit exceeded by ${exceeded}`;
}

interface AnswerEditFormProps {
  editedText: string;
  charCount: number;
  charCountColor: CharCountColor;
  isSaving: boolean;
  isSaveDisabled: boolean;
  savedSuccess: boolean;
  error: string | null;
  onTextChange: (text: string) => void;
  onCancel: () => void;
  onSave: () => void;
}

export function AnswerEditForm({
  editedText,
  charCount,
  charCountColor,
  isSaving,
  isSaveDisabled,
  savedSuccess,
  error,
  onTextChange,
  onCancel,
  onSave,
}: AnswerEditFormProps) {
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    handleFormKeyDown(e, isSaving, isSaveDisabled, onCancel, onSave);
  };

  const charCountMsg = getCharCountMessage(charCount, ANSWER_CHARACTER_LIMIT.max);
  const showCharWarning = charCount > ANSWER_CHARACTER_LIMIT.warningThreshold;

  return (
    <div className="space-y-3">
      <Textarea
        value={editedText}
        onChange={(e) => onTextChange(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Enter your answer..."
        rows={4}
        maxLength={ANSWER_CHARACTER_LIMIT.max}
        disabled={isSaving}
        aria-label="Answer text"
        aria-description="Press Escape to cancel, Ctrl+Enter to save"
      />

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <div>
            <span
              className={`text-sm ${CHAR_COUNT_COLOR_CLASSES[charCountColor]}`}
              aria-live="polite"
              aria-atomic="true"
            >
              {charCount}/{ANSWER_CHARACTER_LIMIT.max} characters
            </span>
            {showCharWarning && (
              <p className={`text-xs mt-1 ${charCount <= ANSWER_CHARACTER_LIMIT.max ? 'text-amber-600' : 'text-jasper-red-600'}`}>
                {charCountMsg}
              </p>
            )}
          </div>

          <div className="flex gap-2">
            <Button onClick={onCancel} variant="secondary" size="md" disabled={isSaving}>
              Cancel
            </Button>
            <Button onClick={onSave} variant="success" size="md" disabled={isSaveDisabled || isSaving}>
              {savedSuccess ? '✓ Saved' : isSaving ? 'Saving...' : 'Save'}
            </Button>
          </div>
        </div>
      </div>

      {error && (
        <div className="p-3 bg-jasper-red-50 border border-jasper-red-200 rounded-md" role="alert">
          <p className="text-sm text-jasper-red-700">{error}</p>
        </div>
      )}
    </div>
  );
}

interface AnswerActionsProps {
  isAnswered: boolean;
  isLocked: boolean;
  sessionComplete: boolean;
  questionText: string;
  onEdit: () => void;
  onDelete: () => void;
  onDeleteQuestion: () => void;
}

export function AnswerActions({
  isAnswered,
  isLocked,
  sessionComplete,
  questionText,
  onEdit,
  onDelete,
  onDeleteQuestion,
}: AnswerActionsProps) {
  const lockReason = sessionComplete ? 'Editing locked - session is complete' : '';

  return (
    <div className="flex gap-2 justify-end">
      {isAnswered ? (
        <>
          <Button
            onClick={onEdit}
            variant="secondary"
            size="sm"
            disabled={isLocked}
            title={lockReason || 'Edit answer'}
            aria-label={`Edit answer for question: ${questionText}`}
            className="min-h-[44px]"
          >
            <FiEdit2 className="w-4 h-4 sm:mr-2" aria-hidden="true" />
            <span className="hidden sm:inline">Edit</span>
          </Button>
          <Button
            onClick={onDelete}
            variant="danger-text"
            size="sm"
            disabled={isLocked}
            title={lockReason || 'Delete answer'}
            aria-label={`Delete answer for question: ${questionText}`}
            className="min-h-[44px]"
          >
            <FiTrash2 className="w-4 h-4 sm:mr-2" aria-hidden="true" />
            <span className="hidden sm:inline">Delete Answer</span>
          </Button>
        </>
      ) : (
        <Button
          onClick={onEdit}
          variant="secondary"
          size="sm"
          disabled={isLocked}
          title={lockReason || 'Add answer'}
          aria-label={`Add answer for question: ${questionText}`}
          className="min-h-[44px]"
        >
          Add Answer
        </Button>
      )}

      <Button
        onClick={onDeleteQuestion}
        variant="danger-text"
        size="sm"
        disabled={isLocked}
        title={lockReason || 'Delete question and answer'}
        aria-label={`Delete question and answer: ${questionText}`}
        className="min-h-[44px]"
      >
        <FiTrash2 className="w-4 h-4 sm:mr-2" aria-hidden="true" />
        <span className="hidden sm:inline">Delete Question</span>
      </Button>
    </div>
  );
}
