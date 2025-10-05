import React from 'react';
import { Question } from '@/lib/api/types';
import { Card } from '@/components/ui/Card';

interface QuestionCardProps {
  question: Question;
  questionNumber?: number;
  totalQuestions?: number;
}

const categoryColors: Record<string, string> = {
  scope: 'bg-indigo-100 text-indigo-700 border border-indigo-200',
  users: 'bg-purple-100 text-purple-700 border border-purple-200',
  constraints: 'bg-amber-100 text-amber-800 border border-amber-200',
  nonfunctional: 'bg-blue-100 text-blue-700 border border-blue-200',
  interfaces: 'bg-teal-100 text-teal-700 border border-teal-200',
  data: 'bg-cyan-100 text-cyan-800 border border-cyan-200',
  risks: 'bg-orange-100 text-orange-700 border border-orange-200',
  success: 'bg-benzol-green-100 text-benzol-green-700 border border-benzol-green-200',
};

export function QuestionCard({ question, questionNumber, totalQuestions }: QuestionCardProps) {
  const categoryColor = categoryColors[question.category] || categoryColors.scope;

  return (
    <Card padding="lg">
      <div className="space-y-4">
        <div className="flex flex-wrap items-center gap-3">
          {questionNumber && totalQuestions && (
            <span className="text-sm font-semibold text-deep-indigo-400">
              Question {questionNumber + 1} of {totalQuestions}
            </span>
          )}
          <span className={`px-4 py-2.5 rounded-full text-sm font-medium ${categoryColor} min-h-[44px] inline-flex items-center`}>
            {question.category}
          </span>
          {question.required && (
            <span className="text-xs text-deep-indigo-400 font-medium px-2 py-1">Required</span>
          )}
        </div>
        <h2 className="text-xl sm:text-2xl font-semibold text-deep-indigo-500 leading-snug break-words">
          {question.text}
        </h2>
      </div>
    </Card>
  );
}
