'use client';

import { useState } from 'react';
import { FiCheck, FiCopy, FiX, FiLoader } from 'react-icons/fi';
import { QuestionAnswerPair } from '@/lib/api/types';
import { Card } from '@/components/ui/Card';
import { CategoryBadge } from '@/components/ui/CategoryBadge';
import { copyToClipboard } from '../utils/categoryHelpers';

interface QAPairCardProps {
  pair: QuestionAnswerPair;
}

export function QAPairCard({ pair }: QAPairCardProps) {
  const [showCopyFeedback, setShowCopyFeedback] = useState(false);
  const [isCopying, setIsCopying] = useState(false);
  const [copyError, setCopyError] = useState(false);

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

  const isAnswered = pair.answer !== null;

  return (
    <Card
      padding="md"
      className={`relative group ${!isAnswered ? 'border-dashed border-2 border-amber-200 bg-amber-50' : ''}`}
    >
      <article className="space-y-3">
        <div className="flex justify-between items-start gap-4">
          <div className="flex-1 space-y-2">
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
            className="opacity-60 group-hover:opacity-100 focus:opacity-100 transition-opacity p-2 rounded hover:bg-deep-indigo-50 focus:outline-none focus:ring-2 focus:ring-benzol-green-500 focus:ring-offset-2"
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
          {/* Screen reader announcements */}
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
        </div>

        <div
          className={`pt-3 border-t ${isAnswered ? 'border-deep-indigo-100' : 'border-amber-200'}`}
        >
          <div role="definition">
            <p className={`text-base ${isAnswered ? 'text-deep-indigo-500' : 'text-amber-800 italic'}`}>
              <span className="font-medium text-deep-indigo-500 text-sm">A:</span>{' '}
              {pair.answer?.text || 'Not answered yet'}
            </p>
          </div>
        </div>
      </article>
    </Card>
  );
}
