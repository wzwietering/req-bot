'use client';

import { useState } from 'react';
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

  const handleCopy = async () => {
    if (isCopying) return;

    setIsCopying(true);
    const text = `Q: ${pair.question.text}\nCategory: ${pair.question.category}\n\nA: ${pair.answer?.text || 'Not answered yet'}`;

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
  };

  const handleEditAnswer = () => {
    if (isAnswered && pair.answer) {
      answerEdit.startEdit(pair.answer.text);
    } else {
      answerEdit.startEdit('');
    }
  };

  const handleDeleteAnswer = () => {
    if (!isAnswered) return;
    setShowAnswerDeleteConfirm(true);
  };

  const confirmDeleteAnswer = async () => {
    await answerEdit.deleteAnswer();
    setShowAnswerDeleteConfirm(false);
  };

  const isEditing = answerEdit.isEditing;
  const isLocked = sessionStatusLoading || sessionComplete || answerEdit.isSaving || answerEdit.isDeleting || questionDelete.isDeleting;

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
              {isCopying ? (
                <FiLoader className="w-5 h-5 text-deep-indigo-400 animate-spin" aria-hidden="true" />
              ) : copyError ? (
                <FiX className="w-5 h-5 text-jasper-red-500" aria-hidden="true" />
              ) : showCopyFeedback ? (
                <FiCheck className="w-5 h-5 text-benzol-green-500" aria-hidden="true" />
              ) : (
                <FiCopy className="w-5 h-5 text-deep-indigo-400" aria-hidden="true" />
              )}
              <span className="hidden lg:inline text-sm text-deep-indigo-500">
                {isCopying ? 'Copying...' : showCopyFeedback ? 'Copied!' : 'Copy'}
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
