import { useMemo, useState } from 'react';
import { SessionSummary } from '@/lib/api/types';

type FilterType = 'all' | 'active' | 'completed';
type SortType = 'newest' | 'oldest' | 'name';

export function useSessionFilters(sessions: SessionSummary[]) {
  const [filter, setFilter] = useState<FilterType>('all');
  const [sort, setSort] = useState<SortType>('newest');

  const filteredSessions = useMemo(() => {
    let result = [...sessions];

    if (filter === 'active') {
      result = result.filter((s) => !s.conversation_complete);
    } else if (filter === 'completed') {
      result = result.filter((s) => s.conversation_complete);
    }

    result.sort((a, b) => {
      if (sort === 'newest') {
        return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      }
      if (sort === 'oldest') {
        return new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
      }
      return a.project.localeCompare(b.project);
    });

    return result;
  }, [sessions, filter, sort]);

  return {
    filteredSessions,
    filter,
    setFilter,
    sort,
    setSort,
  };
}
