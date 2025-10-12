import { useState, useCallback, useRef, useEffect } from 'react';
import { sessionsApi } from '@/lib/api/sessions';
import { SessionQAResponse } from '@/lib/api/types';

interface UseSessionQAResult {
  data: SessionQAResponse | null;
  isLoading: boolean;
  error: string | null;
  loadQA: () => Promise<void>;
}

export function useSessionQA(sessionId: string): UseSessionQAResult {
  const [data, setData] = useState<SessionQAResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const isMountedRef = useRef(false);

  const loadQA = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const qaData = await sessionsApi.getSessionQA(sessionId);
      if (isMountedRef.current) {
        setData(qaData);
      }
    } catch (err) {
      if (isMountedRef.current) {
        setError(err instanceof Error ? err.message : 'Failed to load Q&A data');
      }
    } finally {
      if (isMountedRef.current) {
        setIsLoading(false);
      }
    }
  }, [sessionId]);

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  return {
    data,
    isLoading,
    error,
    loadQA,
  };
}
