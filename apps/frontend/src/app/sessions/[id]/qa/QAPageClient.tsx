'use client';

import { useEffect, useState, useCallback, useMemo } from 'react';
import { useSessionQA } from '@/hooks/useSessionQA';
import { Navigation } from '@/components/layout/Navigation';
import { Container } from '@/components/ui/Container';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { ErrorDisplay } from '@/components/ui/ErrorDisplay';
import { CategorySection } from './components/CategorySection';
import { QAHeader } from './components/QAHeader';
import { EmptyQAState } from './components/EmptyQAState';
import {
  groupByCategory,
  calculateProgress,
  exportToMarkdown,
  downloadMarkdownFile,
} from './utils/categoryHelpers';

interface QAPageClientProps {
  sessionId: string;
}

export function QAPageClient({ sessionId }: QAPageClientProps) {
  const { data, isLoading, error, loadQA } = useSessionQA(sessionId);
  const [isExporting, setIsExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const [sessionComplete, setSessionComplete] = useState(false);

  useEffect(() => {
    loadQA();

    // Fetch session details to get conversation_complete status
    const fetchSessionStatus = async () => {
      try {
        const { sessionsApi } = await import('@/lib/api/sessions');
        const session = await sessionsApi.getSession(sessionId);
        setSessionComplete(session.conversation_complete);
      } catch (err) {
        console.error('Failed to fetch session status:', err);
        // Session status is optional, continue with default (not complete)
      }
    };

    fetchSessionStatus();
  }, [loadQA, sessionId]);

  const handleExport = useCallback(() => {
    if (!data) return;

    setIsExporting(true);
    setExportError(null);

    try {
      const markdown = exportToMarkdown(data.project, data.qa_pairs);
      const filename = `${data.project.replace(/[^a-z0-9]/gi, '_')}_QA.md`;
      downloadMarkdownFile(filename, markdown);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to export file';
      setExportError(message);
      console.error('Failed to export:', err);
    } finally {
      setIsExporting(false);
    }
  }, [data]);

  const categoryGroups = useMemo(
    () => (data ? groupByCategory(data.qa_pairs) : []),
    [data]
  );

  const progress = useMemo(() => (data ? calculateProgress(data.qa_pairs) : null), [data]);

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
              <QAHeader
                projectName={data.project}
                answeredCount={progress?.answered || 0}
                totalCount={progress?.total || 0}
                onExport={handleExport}
                isExporting={isExporting}
                exportError={exportError}
              />

              {categoryGroups.length === 0 ? (
                <EmptyQAState sessionId={sessionId} />
              ) : (
                <div className="space-y-8">
                  {categoryGroups.map((group) => (
                    <CategorySection
                      key={group.category}
                      group={group}
                      sessionId={sessionId}
                      sessionComplete={sessionComplete}
                      onRefresh={loadQA}
                    />
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
