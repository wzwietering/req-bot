'use client';

import React, { useState, FormEvent, useEffect, useRef } from 'react';
import { Button } from '@/components/ui/Button';

interface AnswerInputProps {
  onSubmit: (answer: string) => void;
  onSkip?: () => void;
  isLoading: boolean;
  disabled?: boolean;
  canSkip?: boolean;
  questionId?: string;
}

const MIN_CHARS = 50;
const IDEAL_CHARS = 150;
const MAX_CHARS = 1000;

export function AnswerInput({
  onSubmit,
  onSkip,
  isLoading,
  disabled = false,
  canSkip = false,
  questionId
}: AnswerInputProps) {
  const [answer, setAnswer] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Load draft answer on mount or question change
  useEffect(() => {
    if (questionId) {
      const draft = localStorage.getItem(`interview-draft-${questionId}`);
      if (draft) {
        setAnswer(draft);
      }
    }
  }, [questionId]);

  // Persist draft to localStorage
  useEffect(() => {
    if (questionId && answer) {
      localStorage.setItem(`interview-draft-${questionId}`, answer);
    }
  }, [answer, questionId]);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (answer.trim()) {
      onSubmit(answer.trim());
      if (questionId) {
        localStorage.removeItem(`interview-draft-${questionId}`);
      }
      setAnswer('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      e.preventDefault();
      if (answer.trim() && !isLoading && !disabled) {
        const syntheticEvent = { preventDefault: () => {} } as FormEvent;
        handleSubmit(syntheticEvent);
      }
    }
  };

  const handleFocus = () => {
    // Scroll into view on mobile to prevent keyboard covering button
    setTimeout(() => {
      textareaRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }, 300);
  };

  const charCount = answer.length;
  const getCountColor = () => {
    if (charCount < MIN_CHARS) return 'text-jasper-red-500';
    if (charCount < IDEAL_CHARS) return 'text-deep-indigo-400';
    if (charCount <= MAX_CHARS) return 'text-benzol-green-500';
    return 'text-jasper-red-500';
  };

  const getQualityLabel = () => {
    if (charCount === 0) return 'Start typing your answer';
    if (charCount < MIN_CHARS) return 'Too brief - add more detail';
    if (charCount < IDEAL_CHARS) return 'Good - more detail helps';
    if (charCount <= MAX_CHARS) return 'Great detail!';
    return 'Too long - consider being more concise';
  };

  const isSubmitDisabled = !answer.trim() || isLoading || disabled;

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label htmlFor="answer-input" className="block text-sm font-medium text-deep-indigo-500 mb-2">
          Your Answer
        </label>
        <textarea
          ref={textareaRef}
          id="answer-input"
          value={answer}
          onChange={(e) => setAnswer(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={handleFocus}
          placeholder="Type your answer here..."
          rows={6}
          disabled={isLoading || disabled}
          className="
            w-full px-4 py-3 rounded-lg border
            bg-white text-deep-indigo-500
            border-deep-indigo-200 focus:border-benzol-green-500
            focus:outline-2 focus:outline-benzol-green-500
            transition-colors duration-200
            disabled:bg-deep-indigo-50 disabled:cursor-not-allowed
            resize-none
          "
          aria-describedby="answer-helper answer-count"
        />
        <p id="answer-helper" className="mt-2 text-sm text-deep-indigo-400">
          Provide as much detail as possible. Press <kbd className="px-1 py-0.5 bg-deep-indigo-100 rounded text-xs">Cmd+Enter</kbd> (Mac) or <kbd className="px-1 py-0.5 bg-deep-indigo-100 rounded text-xs">Ctrl+Enter</kbd> (Windows) to submit.
        </p>
      </div>

      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <span id="answer-count" className={`text-xs ${getCountColor()} font-medium`}>
          {charCount} characters • {getQualityLabel()}
        </span>
        <div className="flex gap-3 justify-end">
          {canSkip && onSkip && (
            <Button
              type="button"
              variant="secondary"
              onClick={onSkip}
              disabled={isLoading || disabled}
              title="Skip this question. You won't be able to answer it later."
            >
              Skip Question
            </Button>
          )}
          <Button
            type="submit"
            disabled={isSubmitDisabled}
            className="min-w-32 sm:min-w-40 whitespace-nowrap"
          >
            {isLoading ? 'Submitting...' : 'Submit Answer'}
          </Button>
        </div>
      </div>
    </form>
  );
}
