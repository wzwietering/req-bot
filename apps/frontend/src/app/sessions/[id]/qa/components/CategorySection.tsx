'use client';

import { CategoryGroup, categoryConfig } from '../utils/categoryHelpers';
import { QAPairCard } from './QAPairCard';
import { StatusBadge } from './StatusBadge';
import { QuestionCreateForm } from './QuestionCreateForm';
import { useQuestionCreate } from '@/hooks/useQuestionCreate';
import { FiPlus, FiInfo } from 'react-icons/fi';

interface CategorySectionProps {
  group: CategoryGroup;
  sessionId: string;
  sessionComplete: boolean;
  sessionStatusLoading: boolean;
  onRefresh: () => void;
}

function getStatusVariant(answeredCount: number, totalCount: number) {
  if (answeredCount === totalCount) {
    return 'complete';
  }

  if (answeredCount > 0) {
    return 'partial';
  }

  return 'notStarted';
}

export function CategorySection({ group, sessionId, sessionComplete, sessionStatusLoading, onRefresh }: CategorySectionProps) {
  const config = categoryConfig[group.category];
  const statusVariant = getStatusVariant(group.answeredCount, group.totalCount);

  const questionCreate = useQuestionCreate(sessionId, () => {
    onRefresh();
    questionCreate.closeForm();
  });

  return (
    <section
      className={`border-l-4 ${config.borderColor} pl-6 py-4`}
      aria-labelledby={`category-${group.category}`}
    >
      <div className="space-y-4">
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <div className="flex items-center gap-3">
            <StatusBadge variant={statusVariant} />
            <h2
              id={`category-${group.category}`}
              className="text-xl font-semibold text-deep-indigo-500"
            >
              {group.label}
            </h2>
            <span className={`px-3 py-1 rounded-full text-sm font-medium ${config.colors}`}>
              {group.answeredCount}/{group.totalCount}
            </span>
          </div>

          {!sessionComplete && !questionCreate.showForm && (
            <button
              onClick={() => questionCreate.openForm(group.category)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-benzol-green-700 hover:text-benzol-green-800 hover:bg-benzol-green-50 rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-benzol-green-500 focus:ring-offset-2 min-h-[44px]"
              aria-label={`Add question to ${group.label} category`}
            >
              <FiPlus className="w-4 h-4" aria-hidden="true" />
              <span>Add Question</span>
            </button>
          )}
        </div>

        {/* Session Complete Banner */}
        {sessionComplete && (
          <div
            className="flex items-start gap-3 p-4 bg-amber-50 border-2 border-amber-400 rounded-lg shadow-sm"
            role="alert"
          >
            <FiInfo className="w-6 h-6 text-amber-700 flex-shrink-0 mt-0.5" aria-hidden="true" />
            <div>
              <p className="text-base font-semibold text-amber-900 mb-1">
                Session Complete - Read Only
              </p>
              <p className="text-sm text-amber-800">
                This session is locked. Questions and answers cannot be edited. To make changes, create a new session.
              </p>
            </div>
          </div>
        )}

        {/* Question Creation Form */}
        {questionCreate.showForm && (
          <QuestionCreateForm
            category={group.category}
            questionText={questionCreate.formData.text}
            isRequired={questionCreate.formData.required}
            charCount={questionCreate.charCount}
            charCountColor={questionCreate.charCountColor}
            isCreating={questionCreate.isCreating}
            error={questionCreate.error}
            isCreateDisabled={questionCreate.isCreateDisabled}
            onTextChange={questionCreate.updateText}
            onRequiredChange={questionCreate.updateRequired}
            onCreate={questionCreate.createQuestion}
            onCancel={questionCreate.closeForm}
          />
        )}

        {/* Q&A Pairs */}
        {group.pairs.length === 0 ? (
          <div className="text-center py-6 text-deep-indigo-400 text-sm">
            No questions in this category yet.
            {!sessionComplete && ' Click "Add Question" to get started.'}
          </div>
        ) : (
          <div className="space-y-3">
            {group.pairs.map((pair) => (
              <QAPairCard
                key={pair.question.id}
                pair={pair}
                sessionId={sessionId}
                sessionComplete={sessionComplete}
                sessionStatusLoading={sessionStatusLoading}
                onRefresh={onRefresh}
              />
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
