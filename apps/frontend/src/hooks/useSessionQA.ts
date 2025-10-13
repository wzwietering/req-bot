import { useState, useCallback, useRef, useEffect } from 'react';
import { sessionsApi } from '@/lib/api/sessions';
import { SessionQAResponse } from '@/lib/api/types';

interface UseSessionQAResult {
  data: SessionQAResponse | null;
  isLoading: boolean;
  error: string | null;
  loadQA: () => Promise<void>;
}

function isAbortError(error: unknown): boolean {
  return error instanceof Error && error.name === 'AbortError';
}

export function useSessionQA(sessionId: string): UseSessionQAResult {
  const [data, setData] = useState<SessionQAResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const loadQA = useCallback(async () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    try {
      setIsLoading(true);
      setError(null);
      const qaData = await sessionsApi.getSessionQA(sessionId);
      setData(qaData);
    } catch (err) {
      if (isAbortError(err)) {
        return;
      }
      setError(err instanceof Error ? err.message : 'Failed to load Q&A data');
    } finally {
      setIsLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  return {
    data,
    isLoading,
    error,
    loadQA,
  };
}
