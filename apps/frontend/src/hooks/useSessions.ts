import { useState, useCallback, useRef, useEffect } from 'react';
import { sessionsApi } from '@/lib/api/sessions';
import { SessionSummary } from '@/lib/api/types';

interface UseSessionsResult {
  sessions: SessionSummary[];
  isLoading: boolean;
  error: string | null;
  loadSessions: () => Promise<void>;
  deleteSession: (id: string) => Promise<void>;
}

export function useSessions(): UseSessionsResult {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const isMountedRef = useRef(true);

  const loadSessions = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const data = await sessionsApi.listSessions();
      if (isMountedRef.current) {
        setSessions(data);
      }
    } catch (err) {
      if (isMountedRef.current) {
        setError(err instanceof Error ? err.message : 'Failed to load sessions');
      }
    } finally {
      if (isMountedRef.current) {
        setIsLoading(false);
      }
    }
  }, []);

  const deleteSession = useCallback(async (id: string) => {
    try {
      await sessionsApi.deleteSession(id);
      if (isMountedRef.current) {
        setSessions((prev) => prev.filter((s) => s.id !== id));
      }
    } catch (err) {
      throw err;
    }
  }, []);

  useEffect(() => {
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  return {
    sessions,
    isLoading,
    error,
    loadSessions,
    deleteSession,
  };
}
