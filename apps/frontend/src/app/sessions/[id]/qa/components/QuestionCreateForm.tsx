'use client';

import { Button } from '@/components/ui/Button';
import { Textarea } from '@/components/ui/Textarea';
import { CategoryBadge } from '@/components/ui/CategoryBadge';
import { Question } from '@/lib/api/types';
import { CharCountColor, QUESTION_CHARACTER_LIMIT } from '@/types/form';

interface QuestionCreateFormProps {
  category: Question['category'];
  questionText: string;
  isRequired: boolean;
  charCount: number;
  charCountColor: CharCountColor;
  isCreating: boolean;
  error: string | null;
  isCreateDisabled: boolean;
  onTextChange: (text: string) => void;
  onRequiredChange: (required: boolean) => void;
  onCreate: () => void;
  onCancel: () => void;
}

const charCountColorClasses: Record<CharCountColor, string> = {
  gray: 'text-deep-indigo-400',
  amber: 'text-amber-600 font-medium',
  red: 'text-jasper-red-600 font-semibold',
};

export function QuestionCreateForm({
  category,
  questionText,
  isRequired,
  charCount,
  charCountColor,
  isCreating,
  error,
  isCreateDisabled,
  onTextChange,
  onRequiredChange,
  onCreate,
  onCancel,
}: QuestionCreateFormProps) {
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Escape' && !isCreating) {
      e.preventDefault();
      onCancel();
    }
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter' && !isCreateDisabled && !isCreating) {
      e.preventDefault();
      onCreate();
    }
  };

  return (
    <div className="bg-deep-indigo-50 border border-deep-indigo-200 rounded-lg p-4 mb-4">
      <div className="flex items-center gap-2 mb-3">
        <h3 className="text-sm font-medium text-deep-indigo-500">Add Question to</h3>
        <CategoryBadge category={category} />
      </div>

      <Textarea
        value={questionText}
        onChange={(e) => onTextChange(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Enter your question text..."
        rows={3}
        maxLength={QUESTION_CHARACTER_LIMIT.max}
        disabled={isCreating}
        aria-label="Question text"
        aria-description="Press Escape to cancel, Ctrl+Enter to create"
        className="mb-2"
      />

      <div className="mb-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="required-checkbox"
              checked={isRequired}
              onChange={(e) => onRequiredChange(e.target.checked)}
              disabled={isCreating}
              className="w-4 h-4 text-benzol-green-600 bg-white border-deep-indigo-300 rounded focus:ring-2 focus:ring-benzol-green-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
            />
            <label
              htmlFor="required-checkbox"
              className="text-sm text-deep-indigo-500 select-none cursor-pointer"
            >
              Required question
            </label>
          </div>

          <div className="text-right">
            <span
              className={`text-sm ${charCountColorClasses[charCountColor]}`}
              aria-live="polite"
              aria-atomic="true"
            >
              {charCount}/{QUESTION_CHARACTER_LIMIT.max} characters
            </span>
            {charCount > QUESTION_CHARACTER_LIMIT.warningThreshold && (
              <p className={`text-xs mt-1 ${charCount <= QUESTION_CHARACTER_LIMIT.max ? 'text-amber-600' : 'text-jasper-red-600'}`}>
                {charCount <= QUESTION_CHARACTER_LIMIT.max
                  ? `Approaching limit (${QUESTION_CHARACTER_LIMIT.max - charCount} remaining)`
                  : `Limit exceeded by ${charCount - QUESTION_CHARACTER_LIMIT.max}`
                }
              </p>
            )}
          </div>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-jasper-red-50 border border-jasper-red-200 rounded-md" role="alert">
          <p className="text-sm text-jasper-red-700">{error}</p>
        </div>
      )}

      <div className="flex gap-3 justify-end">
        <Button onClick={onCancel} variant="secondary" size="md" disabled={isCreating}>
          Cancel
        </Button>
        <Button
          onClick={onCreate}
          variant="success"
          size="md"
          disabled={isCreateDisabled || isCreating}
        >
          {isCreating ? 'Creating...' : 'Create Question'}
        </Button>
      </div>
    </div>
  );
}
