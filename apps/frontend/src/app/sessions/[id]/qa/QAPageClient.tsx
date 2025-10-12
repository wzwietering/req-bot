'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useSessionQA } from '@/hooks/useSessionQA';
import { Navigation } from '@/components/layout/Navigation';
import { Container } from '@/components/ui/Container';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { ErrorDisplay } from '@/components/ui/ErrorDisplay';
import { Button } from '@/components/ui/Button';
import { CategorySection } from './components/CategorySection';
import { groupByCategory, calculateProgress, exportToMarkdown } from './utils/categoryHelpers';

interface QAPageClientProps {
  sessionId: string;
}

export function QAPageClient({ sessionId }: QAPageClientProps) {
  const router = useRouter();
  const { data, isLoading, error, loadQA } = useSessionQA(sessionId);
  const [isExporting, setIsExporting] = useState(false);

  useEffect(() => {
    loadQA();
  }, [loadQA]);

  const handleExport = () => {
    if (!data) return;

    setIsExporting(true);
    try {
      const markdown = exportToMarkdown(data.project, data.qa_pairs);
      const blob = new Blob([markdown], { type: 'text/markdown' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${data.project.replace(/[^a-z0-9]/gi, '_')}_QA.md`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Failed to export:', err);
    } finally {
      setIsExporting(false);
    }
  };

  const categoryGroups = data ? groupByCategory(data.qa_pairs) : [];
  const progress = data ? calculateProgress(data.qa_pairs) : null;

  return (
    <div className="min-h-screen bg-gradient-to-br from-deep-indigo-50 to-white">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:px-4 focus:py-2 focus:bg-benzol-green-500 focus:text-white focus:rounded"
      >
        Skip to main content
      </a>
      <Navigation />
      <main id="main-content" className="py-12">
        <Container size="lg">
          {isLoading ? (
            <LoadingSpinner size="lg" label="Loading Q&A..." />
          ) : error ? (
            <ErrorDisplay error={error} onRetry={loadQA} />
          ) : data ? (
            <div className="space-y-6">
              {/* Header */}
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                <div className="flex-1">
                  <nav className="text-sm text-deep-indigo-400 mb-2" aria-label="Breadcrumb">
                    <ol className="flex items-center space-x-2">
                      <li>
                        <button
                          onClick={() => router.push('/sessions')}
                          className="hover:text-deep-indigo-500 focus:outline-none focus:underline"
                        >
                          Sessions
                        </button>
                      </li>
                      <li aria-hidden="true">/</li>
                      <li>
                        <span className="text-deep-indigo-500 font-medium">{data.project}</span>
                      </li>
                      <li aria-hidden="true">/</li>
                      <li>
                        <span className="text-deep-indigo-500 font-medium">Q&A</span>
                      </li>
                    </ol>
                  </nav>
                  <h1 className="text-3xl font-bold text-deep-indigo-500">{data.project}</h1>
                  {progress && (
                    <p className="text-base text-deep-indigo-400 mt-1">
                      {progress.answered} of {progress.total} questions answered
                    </p>
                  )}
                </div>
                <div className="flex flex-col sm:flex-row gap-2 w-full sm:w-auto">
                  <Button
                    onClick={() => router.push('/sessions')}
                    variant="secondary"
                    size="md"
                    className="w-full sm:w-auto"
                  >
                    Back to Sessions
                  </Button>
                  <Button
                    onClick={handleExport}
                    variant="primary"
                    size="md"
                    disabled={isExporting}
                    className="w-full sm:w-auto"
                    aria-label="Export all questions and answers as Markdown file"
                  >
                    {isExporting ? 'Exporting...' : 'Export Markdown'}
                  </Button>
                </div>
              </div>

              {/* Q&A Content */}
              {categoryGroups.length === 0 ? (
                <div className="text-center py-12 max-w-md mx-auto">
                  <p className="text-deep-indigo-500 font-medium mb-2 text-lg">No Questions Yet</p>
                  <p className="text-deep-indigo-400 mb-4">
                    Questions will appear here after you start your interview session.
                  </p>
                  <Button onClick={() => router.push(`/interview/${sessionId}`)} variant="primary" size="md">
                    Start Interview
                  </Button>
                </div>
              ) : (
                <div className="space-y-8">
                  {categoryGroups.map((group) => (
                    <CategorySection key={group.category} group={group} />
                  ))}
                </div>
              )}
            </div>
          ) : null}
        </Container>
      </main>
    </div>
  );
}
