'use client';

interface SessionFiltersProps {
  filter: 'all' | 'active' | 'completed';
  sort: 'newest' | 'oldest' | 'name';
  onFilterChange: (filter: 'all' | 'active' | 'completed') => void;
  onSortChange: (sort: 'newest' | 'oldest' | 'name') => void;
}

export function SessionFilters({ filter, sort, onFilterChange, onSortChange }: SessionFiltersProps) {
  return (
    <div className="flex flex-col sm:flex-row gap-4 mb-6">
      <div className="flex-1">
        <label htmlFor="filter" className="block text-sm font-medium text-deep-indigo-500 mb-2">
          Filter
        </label>
        <select
          id="filter"
          value={filter}
          onChange={(e) => onFilterChange(e.target.value as 'all' | 'active' | 'completed')}
          className="w-full px-4 py-2 border border-deep-indigo-200 rounded-lg text-deep-indigo-500 bg-white focus:outline-none focus:ring-2 focus:ring-benzol-green-500"
        >
          <option value="all">All Sessions</option>
          <option value="active">Active Only</option>
          <option value="completed">Completed Only</option>
        </select>
      </div>

      <div className="flex-1">
        <label htmlFor="sort" className="block text-sm font-medium text-deep-indigo-500 mb-2">
          Sort By
        </label>
        <select
          id="sort"
          value={sort}
          onChange={(e) => onSortChange(e.target.value as 'newest' | 'oldest' | 'name')}
          className="w-full px-4 py-2 border border-deep-indigo-200 rounded-lg text-deep-indigo-500 bg-white focus:outline-none focus:ring-2 focus:ring-benzol-green-500"
        >
          <option value="newest">Newest First</option>
          <option value="oldest">Oldest First</option>
          <option value="name">Project Name (A-Z)</option>
        </select>
      </div>
    </div>
  );
}
