'use client';

import { useRouter } from 'next/navigation';
import { SessionSummary } from '@/lib/api/types';
import { Button } from '@/components/ui/Button';
import { useSessionFilters } from '@/hooks/useSessionFilters';
import { SessionCard } from './SessionCard';
import { SessionFilters } from './SessionFilters';
import { EmptyState } from './EmptyState';

interface SessionsListProps {
  sessions: SessionSummary[];
  onDeleteSession: (id: string) => Promise<void>;
}

export function SessionsList({ sessions, onDeleteSession }: SessionsListProps) {
  const router = useRouter();
  const { filteredSessions, filter, setFilter, sort, setSort } = useSessionFilters(sessions);

  if (sessions.length === 0) {
    return <EmptyState />;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold text-deep-indigo-500">Your Sessions</h1>
          <p className="text-base text-deep-indigo-400 mt-1">
            Manage your requirements gathering sessions
          </p>
        </div>
        <Button onClick={() => router.push('/interview/new')} variant="primary" size="lg">
          New Session
        </Button>
      </div>

      <SessionFilters filter={filter} sort={sort} onFilterChange={setFilter} onSortChange={setSort} />

      {filteredSessions.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-deep-indigo-400">No sessions match your filters</p>
          <Button onClick={() => setFilter('all')} variant="secondary" size="md" className="mt-4">
            Clear Filters
          </Button>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filteredSessions.map((session) => (
            <SessionCard key={session.id} session={session} onDelete={onDeleteSession} />
          ))}
        </div>
      )}
    </div>
  );
}
