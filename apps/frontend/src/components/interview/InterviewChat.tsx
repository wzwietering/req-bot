'use client';

import React, { useEffect, useState, useRef } from 'react';
import { useInterview } from '@/hooks/useInterview';
import { QuestionCard } from './QuestionCard';
import { AnswerInput } from './AnswerInput';
import { ProgressBar } from './ProgressBar';
import { RequirementsView } from './RequirementsView';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';

export function InterviewChat() {
  const {
    currentQuestion,
    isComplete,
    isLoading,
    error,
    progress,
    requirements,
    project,
    sessionId,
    getNextQuestion,
    submitAnswer,
    loadRequirements,
    updateProgress,
    retryRequirements,
  } = useInterview();

  const [loadingDuration, setLoadingDuration] = useState(0);
  const [lastAnswer, setLastAnswer] = useState<string>('');
  const loadingRequirementsRef = useRef(false);

  useEffect(() => {
    if (!currentQuestion && !isComplete && !isLoading) {
      getNextQuestion();
    }
  }, [currentQuestion, isComplete, isLoading, getNextQuestion]);

  useEffect(() => {
    if (isComplete && requirements.length === 0 && !isLoading && !loadingRequirementsRef.current) {
      loadingRequirementsRef.current = true;
      loadRequirements().finally(() => {
        loadingRequirementsRef.current = false;
      });
    }
  }, [isComplete, requirements.length, isLoading, loadRequirements]);

  // Track loading duration
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isLoading) {
      setLoadingDuration(0);
      interval = setInterval(() => {
        setLoadingDuration(prev => prev + 1000);
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [isLoading]);

  // Navigation protection
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (sessionId && !isComplete) {
        e.preventDefault();
        e.returnValue = 'You have an interview in progress. Are you sure you want to leave?';
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [sessionId, isComplete]);

  const handleSubmitAnswer = async (answerText: string) => {
    setLastAnswer(answerText);
    await submitAnswer(answerText);
    await updateProgress();
    await getNextQuestion();
  };

  const handleSkip = async () => {
    await submitAnswer('(Skipped)');
    await updateProgress();
    await getNextQuestion();
  };

  const handleRetry = async () => {
    if (lastAnswer) {
      await submitAnswer(lastAnswer);
      await updateProgress();
      await getNextQuestion();
    } else {
      window.location.reload();
    }
  };

  // Aria-live region for screen readers
  const getLoadingMessage = () => {
    if (!isLoading) return '';
    if (loadingDuration < 3000) return 'Processing your answer, please wait';
    if (loadingDuration < 8000) return 'This is taking longer than usual, still processing';
    return 'Almost there, just a few more seconds';
  };

  if (error) {
    return (
      <div className="space-y-6">
        {progress && (
          <ProgressBar
            current={progress.answeredQuestions}
            total={progress.totalQuestions}
            percentage={progress.completionPercentage}
          />
        )}

        <Card padding="lg">
          <div role="alert" aria-live="assertive" className="text-center space-y-4">
            <div className="flex justify-center">
              <div className="w-12 h-12 bg-jasper-red-100 rounded-full flex items-center justify-center">
                <svg className="w-6 h-6 text-jasper-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
            </div>
            <h3 className="text-xl font-semibold text-deep-indigo-500">
              Something went wrong
            </h3>
            <p className="text-deep-indigo-400">{error}</p>
            <p className="text-sm text-deep-indigo-400">
              Your progress has been saved. You can try again or restart the interview.
            </p>
            <div className="flex gap-3 justify-center flex-wrap">
              <Button onClick={() => window.location.reload()} variant="secondary">
                Restart Interview
              </Button>
              <Button onClick={handleRetry} variant="primary">
                Try Again
              </Button>
            </div>
          </div>
        </Card>
      </div>
    );
  }

  if (isComplete) {
    // Check if this is a failed state with 0 requirements
    if (requirements.length === 0) {
      return (
        <div className="space-y-6">
          <Card padding="lg">
            <div role="alert" aria-live="assertive" className="text-center space-y-4">
              <div className="flex justify-center">
                <div className="w-12 h-12 bg-jasper-red-100 rounded-full flex items-center justify-center">
                  <svg className="w-6 h-6 text-jasper-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
              </div>
              <h3 className="text-xl font-semibold text-deep-indigo-500">
                Requirements Generation Failed
              </h3>
              <p className="text-deep-indigo-400">
                We encountered an issue while analyzing your interview responses.
                This might be due to high demand on our service.
              </p>
              <p className="text-sm text-deep-indigo-400">
                Your interview answers have been saved. You can retry generating requirements.
              </p>
              <div className="flex gap-3 justify-center flex-wrap">
                <Button onClick={() => window.location.reload()} variant="secondary">
                  Go Back
                </Button>
                <Button onClick={retryRequirements} variant="primary" disabled={isLoading}>
                  {isLoading ? 'Retrying...' : 'Retry Generation'}
                </Button>
              </div>
            </div>
          </Card>
        </div>
      );
    }

    return <RequirementsView requirements={requirements} projectName={project || 'Your Project'} />;
  }

  return (
    <div className="space-y-6">
      {/* Screen reader announcements */}
      <div aria-live="polite" aria-atomic="true" className="sr-only">
        {getLoadingMessage()}
      </div>

      {progress && (
        <ProgressBar
          current={progress.answeredQuestions}
          total={progress.totalQuestions}
          percentage={progress.completionPercentage}
        />
      )}

      {isLoading && !currentQuestion ? (
        <Card padding="lg">
          <LoadingSpinner size="lg" label="Loading next question..." />
        </Card>
      ) : currentQuestion ? (
        <>
          <QuestionCard question={currentQuestion} questionNumber={progress?.answeredQuestions} totalQuestions={progress?.totalQuestions} />
          <AnswerInput
            onSubmit={handleSubmitAnswer}
            onSkip={handleSkip}
            isLoading={isLoading}
            canSkip={!currentQuestion.required}
            questionId={currentQuestion.id}
          />
          {isLoading && (
            <Card padding="md">
              <div className="space-y-3">
                <LoadingSpinner size="sm" label="Analyzing your answer..." />

                {loadingDuration > 3000 && (
                  <p className="text-xs text-deep-indigo-400 text-center">
                    This is taking longer than usual. We&apos;re still processing...
                  </p>
                )}

                {loadingDuration > 8000 && (
                  <p className="text-xs text-benzol-green-500 text-center font-medium">
                    Almost there! Just a few more seconds...
                  </p>
                )}
              </div>
            </Card>
          )}
        </>
      ) : null}
    </div>
  );
}
