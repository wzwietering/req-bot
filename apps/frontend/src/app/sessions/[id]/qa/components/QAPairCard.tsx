'use client';

import { useState } from 'react';
import { FiCheck, FiCopy, FiX, FiLoader, FiEdit2, FiTrash2 } from 'react-icons/fi';
import { QuestionAnswerPair } from '@/lib/api/types';
import { Card } from '@/components/ui/Card';
import { CategoryBadge } from '@/components/ui/CategoryBadge';
import { Button } from '@/components/ui/Button';
import { Textarea } from '@/components/ui/Textarea';
import { copyToClipboard } from '../utils/categoryHelpers';
import { useAnswerEdit } from '@/hooks/useAnswerEdit';
import { useQuestionDelete } from '@/hooks/useQuestionDelete';
import { DeleteAnswerDialog } from './DeleteAnswerDialog';
import { DeleteQuestionDialog } from './DeleteQuestionDialog';

interface QAPairCardProps {
  pair: QuestionAnswerPair;
  sessionId: string;
  sessionComplete: boolean;
  onRefresh: () => void;
}

const charCountColorClasses = {
  gray: 'text-deep-indigo-400',
  amber: 'text-amber-600 font-medium',
  red: 'text-jasper-red-600 font-semibold',
};

export function QAPairCard({ pair, sessionId, sessionComplete, onRefresh }: QAPairCardProps) {
  const [showCopyFeedback, setShowCopyFeedback] = useState(false);
  const [isCopying, setIsCopying] = useState(false);
  const [copyError, setCopyError] = useState(false);
  const [showAnswerDeleteConfirm, setShowAnswerDeleteConfirm] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);

  const isAnswered = pair.answer !== null;

  const answerEdit = useAnswerEdit(sessionId, pair.question.id, () => {
    onRefresh();
    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 2000);
  });

  const questionDelete = useQuestionDelete(sessionId, pair.question.id, onRefresh);

  const handleCopy = async () => {
    if (isCopying) return;

    setIsCopying(true);
    const text = `Q: ${pair.question.text}\nCategory: ${pair.question.category}\n\nA: ${pair.answer?.text || 'Not answered yet'}`;

    try {
      await copyToClipboard(text);
      setShowCopyFeedback(true);
      setTimeout(() => setShowCopyFeedback(false), 3000);
    } catch (err) {
      console.error('Failed to copy:', err);
      setCopyError(true);
      setTimeout(() => setCopyError(false), 3000);
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
  const isLocked = sessionComplete || answerEdit.isSaving || answerEdit.isDeleting || questionDelete.isDeleting;

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
                  <span className="text-xs font-medium text-deep-indigo-700 px-2 py-1 bg-deep-indigo-50 border border-deep-indigo-200 rounded-full">
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
              className="flex-shrink-0 transition-opacity p-2 rounded hover:bg-deep-indigo-50 focus:outline-none focus:ring-2 focus:ring-benzol-green-500 focus:ring-offset-2 min-h-[44px] min-w-[44px] flex items-center justify-center"
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
              /* Edit Mode */
              <div className="space-y-3">
                <Textarea
                  value={answerEdit.editedText}
                  onChange={(e) => answerEdit.updateText(e.target.value)}
                  placeholder="Enter your answer..."
                  rows={4}
                  maxLength={5000}
                  disabled={answerEdit.isSaving}
                  aria-label="Answer text"
                />

                <div className="flex items-center justify-between">
                  <span
                    className={`text-sm ${charCountColorClasses[answerEdit.charCountColor]}`}
                    aria-live="polite"
                    aria-atomic="true"
                  >
                    {answerEdit.charCount}/5000 characters
                  </span>

                  <div className="flex gap-2">
                    <Button
                      onClick={answerEdit.cancelEdit}
                      variant="secondary"
                      size="md"
                      disabled={answerEdit.isSaving}
                    >
                      Cancel
                    </Button>
                    <Button
                      onClick={answerEdit.saveAnswer}
                      variant="success"
                      size="md"
                      disabled={answerEdit.isSaveDisabled || answerEdit.isSaving}
                    >
                      {savedSuccess ? '✓ Saved' : answerEdit.isSaving ? 'Saving...' : 'Save'}
                    </Button>
                  </div>
                </div>

                {answerEdit.error && (
                  <div className="p-3 bg-jasper-red-50 border border-jasper-red-200 rounded-md" role="alert">
                    <p className="text-sm text-jasper-red-700">{answerEdit.error}</p>
                  </div>
                )}
              </div>
            ) : (
              /* View Mode */
              <div>
                <div role="definition" className="mb-3">
                  <p className={`text-base ${isAnswered ? 'text-deep-indigo-500' : 'text-amber-800'}`}>
                    <span className="font-medium text-deep-indigo-500 text-sm">A:</span>{' '}
                    {pair.answer?.text || 'No answer provided'}
                  </p>
                </div>

                {/* Action Buttons */}
                <div className="flex gap-2 justify-end">
                  {isAnswered ? (
                    <>
                      <Button
                        onClick={handleEditAnswer}
                        variant="secondary"
                        size="sm"
                        disabled={isLocked}
                        title={sessionComplete ? 'Editing locked - session is complete' : 'Edit answer'}
                        aria-label={`Edit answer for question: ${pair.question.text}`}
                        className="min-h-[44px]"
                      >
                        <FiEdit2 className="w-4 h-4 sm:mr-2" aria-hidden="true" />
                        <span className="hidden sm:inline">Edit</span>
                      </Button>
                      <Button
                        onClick={handleDeleteAnswer}
                        variant="danger-text"
                        size="sm"
                        disabled={isLocked}
                        title={sessionComplete ? 'Editing locked - session is complete' : 'Delete answer'}
                        aria-label={`Delete answer for question: ${pair.question.text}`}
                        className="min-h-[44px]"
                      >
                        <FiTrash2 className="w-4 h-4 sm:mr-2" aria-hidden="true" />
                        <span className="hidden sm:inline">Delete Answer</span>
                      </Button>
                    </>
                  ) : (
                    <Button
                      onClick={handleEditAnswer}
                      variant="secondary"
                      size="sm"
                      disabled={isLocked}
                      title={sessionComplete ? 'Editing locked - session is complete' : 'Add answer'}
                      aria-label={`Add answer for question: ${pair.question.text}`}
                      className="min-h-[44px]"
                    >
                      Add Answer
                    </Button>
                  )}

                  <Button
                    onClick={questionDelete.openConfirm}
                    variant="danger-text"
                    size="sm"
                    disabled={isLocked}
                    title={sessionComplete ? 'Editing locked - session is complete' : 'Delete question and answer'}
                    aria-label={`Delete question and answer: ${pair.question.text}`}
                    className="min-h-[44px]"
                  >
                    <FiTrash2 className="w-4 h-4 sm:mr-2" aria-hidden="true" />
                    <span className="hidden sm:inline">Delete Question</span>
                  </Button>
                </div>
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
