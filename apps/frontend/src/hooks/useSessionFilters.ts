import { useMemo, useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { SessionSummary } from '@/lib/api/types';

type FilterType = 'all' | 'active' | 'completed';
type SortType = 'newest' | 'oldest' | 'name-asc' | 'name-desc';

export function useSessionFilters(sessions: SessionSummary[]) {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [filter, setFilterState] = useState<FilterType>(() => {
    const urlFilter = searchParams.get('filter') as FilterType;
    return ['all', 'active', 'completed'].includes(urlFilter) ? urlFilter : 'all';
  });

  const [sort, setSortState] = useState<SortType>(() => {
    const urlSort = searchParams.get('sort') as SortType;
    return ['newest', 'oldest', 'name-asc', 'name-desc'].includes(urlSort) ? urlSort : 'newest';
  });

  // Update URL when filter or sort changes
  useEffect(() => {
    const params = new URLSearchParams();
    if (filter !== 'all') params.set('filter', filter);
    if (sort !== 'newest') params.set('sort', sort);

    const queryString = params.toString();
    router.replace(`/sessions${queryString ? `?${queryString}` : ''}`, { scroll: false });
  }, [filter, sort, router]);

  const setFilter = (newFilter: FilterType) => {
    setFilterState(newFilter);
  };

  const setSort = (newSort: SortType) => {
    setSortState(newSort);
  };

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
      if (sort === 'name-asc') {
        return a.project.localeCompare(b.project, undefined, { sensitivity: 'base' });
      }
      if (sort === 'name-desc') {
        return b.project.localeCompare(a.project, undefined, { sensitivity: 'base' });
      }
      return 0;
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
