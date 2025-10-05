import { useState, useCallback } from 'react';
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

  const loadSessions = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const data = await sessionsApi.listSessions();
      setSessions(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load sessions');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const deleteSession = useCallback(async (id: string) => {
    try {
      await sessionsApi.deleteSession(id);
      setSessions((prev) => prev.filter((s) => s.id !== id));
    } catch (err) {
      throw err;
    }
  }, []);

  return {
    sessions,
    isLoading,
    error,
    loadSessions,
    deleteSession,
  };
}
