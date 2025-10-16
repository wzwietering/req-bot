'use client';

import { useState, useCallback } from 'react';
import { FiCheck, FiCopy, FiX, FiLoader } from 'react-icons/fi';
import { QuestionAnswerPair } from '@/lib/api/types';
import { Card } from '@/components/ui/Card';
import { CategoryBadge } from '@/components/ui/CategoryBadge';
import { copyToClipboard } from '../utils/categoryHelpers';
import { useAnswerEdit } from '@/hooks/useAnswerEdit';
import { useQuestionDelete } from '@/hooks/useQuestionDelete';
import { DeleteAnswerDialog } from './DeleteAnswerDialog';
import { DeleteQuestionDialog } from './DeleteQuestionDialog';
import { AnswerEditForm, AnswerActions } from './QAPairCardHelpers';
import { FEEDBACK_DURATIONS } from '@/constants/ui';

interface QAPairCardProps {
  pair: QuestionAnswerPair;
  sessionId: string;
  sessionComplete: boolean;
  sessionStatusLoading: boolean;
  onRefresh: () => void;
}

function handleSuccess(
  onRefresh: () => void,
  setSavedSuccess: (value: boolean) => void
) {
  onRefresh();
  setSavedSuccess(true);
  setTimeout(() => setSavedSuccess(false), FEEDBACK_DURATIONS.SUCCESS);
}

function formatCopyText(
  questionText: string,
  category: string,
  answerText: string | null | undefined
): string {
  return `Q: ${questionText}\nCategory: ${category}\n\nA: ${answerText || 'Not answered yet'}`;
}

function getCopyButtonIcon(
  isCopying: boolean,
  copyError: boolean,
  showFeedback: boolean
) {
  if (isCopying) return { Icon: FiLoader, className: 'animate-spin' };
  if (copyError) return { Icon: FiX, className: '' };
  if (showFeedback) return { Icon: FiCheck, className: '' };
  return { Icon: FiCopy, className: '' };
}

function getCopyButtonText(isCopying: boolean, showFeedback: boolean): string {
  if (isCopying) return 'Copying...';
  if (showFeedback) return 'Copied!';
  return 'Copy';
}

export function QAPairCard({ pair, sessionId, sessionComplete, sessionStatusLoading, onRefresh }: QAPairCardProps) {
  const [showCopyFeedback, setShowCopyFeedback] = useState(false);
  const [isCopying, setIsCopying] = useState(false);
  const [copyError, setCopyError] = useState(false);
  const [showAnswerDeleteConfirm, setShowAnswerDeleteConfirm] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);

  const isAnswered = pair.answer !== null;

  const answerEdit = useAnswerEdit(sessionId, pair.question.id, () =>
    handleSuccess(onRefresh, setSavedSuccess)
  );

  const questionDelete = useQuestionDelete(sessionId, pair.question.id, onRefresh);

  const handleCopy = useCallback(async () => {
    if (isCopying) return;

    setIsCopying(true);
    const text = formatCopyText(pair.question.text, pair.question.category, pair.answer?.text);

    try {
      await copyToClipboard(text);
      setShowCopyFeedback(true);
      setTimeout(() => setShowCopyFeedback(false), FEEDBACK_DURATIONS.INFO);
    } catch (err) {
      console.error('Failed to copy:', err);
      setCopyError(true);
      setTimeout(() => setCopyError(false), FEEDBACK_DURATIONS.ERROR);
    } finally {
      setIsCopying(false);
    }
  }, [isCopying, pair.question.text, pair.question.category, pair.answer?.text]);

  const handleEditAnswer = useCallback(() => {
    if (isAnswered && pair.answer) {
      answerEdit.startEdit(pair.answer.text);
    } else {
      answerEdit.startEdit('');
    }
  }, [isAnswered, pair.answer, answerEdit]);

  const handleDeleteAnswer = useCallback(() => {
    if (!isAnswered) return;
    setShowAnswerDeleteConfirm(true);
  }, [isAnswered]);

  const confirmDeleteAnswer = useCallback(async () => {
    const success = await answerEdit.deleteAnswer();
    if (success) {
      setShowAnswerDeleteConfirm(false);
    }
  }, [answerEdit]);

  const isEditing = answerEdit.isEditing;
  const isLocked = sessionStatusLoading || sessionComplete || answerEdit.isSaving || answerEdit.isDeleting || questionDelete.isDeleting;
  const { Icon, className: iconClassName } = getCopyButtonIcon(isCopying, copyError, showCopyFeedback);
  const copyButtonText = getCopyButtonText(isCopying, showCopyFeedback);

  return (
    <>
      <Card
        padding="md"
        className={`relative ${!isAnswered && !isEditing ? 'border-dashed border-2 border-amber-200 bg-amber-50' : ''}`}
      >
        <article className="space-y-3">
          {/* Question Section */}
          <div className="flex justify-between items-start gap-4">
            <div className={`flex-1 space-y-2 ${isEditing ? 'opacity-70' : ''}`}>
              <div className="flex flex-wrap items-center gap-2">
                <CategoryBadge category={pair.question.category} />
                {pair.question.required && (
                  <span className="text-xs font-semibold text-jasper-red-700 px-2 py-1 bg-jasper-red-50 border border-jasper-red-300 rounded-full">
                    Required
                  </span>
                )}
              </div>
              <h3 className="text-base font-semibold text-deep-indigo-500 leading-relaxed">
                <span className="text-deep-indigo-400 text-sm font-medium">Q:</span> {pair.question.text}
              </h3>
            </div>

            <button
              onClick={handleCopy}
              disabled={isCopying}
              className="flex-shrink-0 transition-opacity p-2 rounded hover:bg-deep-indigo-50 focus:outline-none focus:ring-2 focus:ring-benzol-green-500 focus:ring-offset-2 min-h-[44px] flex items-center gap-2"
              aria-label="Copy question and answer"
              title="Copy to clipboard"
            >
              <Icon className={`w-5 h-5 text-deep-indigo-400 ${iconClassName}`} aria-hidden="true" />
              <span className="hidden lg:inline text-sm text-deep-indigo-500">
                {copyButtonText}
              </span>
            </button>
          </div>

          {/* Screen reader announcements for copy */}
          {showCopyFeedback && (
            <span className="sr-only" role="status" aria-live="polite">
              Question and answer copied to clipboard
            </span>
          )}
          {copyError && (
            <span className="sr-only" role="status" aria-live="polite">
              Failed to copy to clipboard
            </span>
          )}

          {/* Answer Section */}
          <div className={`pt-3 border-t ${isAnswered && !isEditing ? 'border-deep-indigo-100' : 'border-amber-200'}`}>
            {isEditing ? (
              <AnswerEditForm
                editedText={answerEdit.editedText}
                charCount={answerEdit.charCount}
                charCountColor={answerEdit.charCountColor}
                isSaving={answerEdit.isSaving}
                isSaveDisabled={answerEdit.isSaveDisabled}
                savedSuccess={savedSuccess}
                error={answerEdit.error}
                onTextChange={answerEdit.updateText}
                onCancel={answerEdit.cancelEdit}
                onSave={answerEdit.saveAnswer}
              />
            ) : (
              <div>
                <div role="definition" className="mb-3">
                  <p className={`text-base ${isAnswered ? 'text-deep-indigo-500' : 'text-amber-800'}`}>
                    <span className="font-medium text-deep-indigo-500 text-sm">A:</span>{' '}
                    {pair.answer?.text || 'No answer provided'}
                  </p>
                </div>

                <AnswerActions
                  isAnswered={isAnswered}
                  isLocked={isLocked}
                  sessionComplete={sessionComplete}
                  questionText={pair.question.text}
                  onEdit={handleEditAnswer}
                  onDelete={handleDeleteAnswer}
                  onDeleteQuestion={questionDelete.openConfirm}
                />
              </div>
            )}
          </div>
        </article>
      </Card>

      {/* Delete Answer Confirmation */}
      {isAnswered && pair.answer && (
        <DeleteAnswerDialog
          isOpen={showAnswerDeleteConfirm}
          answerLength={pair.answer.text.length}
          onConfirm={confirmDeleteAnswer}
          onCancel={() => setShowAnswerDeleteConfirm(false)}
          error={answerEdit.error}
          isLoading={answerEdit.isDeleting}
        />
      )}

      {/* Delete Question Confirmation */}
      <DeleteQuestionDialog
        isOpen={questionDelete.showConfirm}
        questionText={pair.question.text}
        answerLength={pair.answer?.text.length || null}
        onConfirm={questionDelete.deleteQuestion}
        onCancel={questionDelete.closeConfirm}
        error={questionDelete.error}
        isLoading={questionDelete.isDeleting}
      />
    </>
  );
}
