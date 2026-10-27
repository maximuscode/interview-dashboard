import { useCallback, useEffect, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import { FilterBar } from '../components/FilterBar'
import { InterviewTable } from '../components/InterviewTable'
import { Pagination } from '../components/Pagination'
import { ErrorBanner } from '../components/ErrorBanner'
import { EmptyState, ErrorState, TableSkeleton } from '../components/states'
import { PER_PAGE, listInterviews, listPositions } from '../lib/api'
import type { Filters } from '../lib/types'
import { useApi } from '../lib/useApi'

const FILTER_KEYS = ['position', 'min_score', 'date_from', 'date_to', 'q', 'reviewed'] as const

export function InterviewList() {
  // Filters live in the URL so a filtered view is shareable and survives reload.
  const [searchParams, setSearchParams] = useSearchParams()

  // Derived from the URL, memoised so everything downstream has a stable
  // identity and the lint rule can see the real dependency.
  const filters: Filters = useMemo(
    () => ({
      page: Number(searchParams.get('page')) || 1,
      position: searchParams.get('position') ?? '',
      min_score: searchParams.get('min_score') ?? '',
      date_from: searchParams.get('date_from') ?? '',
      date_to: searchParams.get('date_to') ?? '',
      q: searchParams.get('q') ?? '',
      reviewed: searchParams.get('reviewed') ?? '',
    }),
    [searchParams],
  )

  const query = useMemo(() => {
    const params = new URLSearchParams({
      page: String(filters.page),
      per_page: String(PER_PAGE),
    })
    for (const key of FILTER_KEYS) {
      if (filters[key]) params.set(key, filters[key])
    }
    return params
  }, [filters])

  const key = query.toString()
  const { data, loading, error, retry } = useApi(() => listInterviews(query), [key])
  const positions = useApi(listPositions, [])

  // A page past the end means a stale link or a filter that narrowed under the
  // user. Snap to the last real page instead of showing a lying empty state.
  useEffect(() => {
    if (!data || data.total_pages === 0) return
    if (filters.page <= data.total_pages) return
    const next = new URLSearchParams(searchParams)
    next.set('page', String(data.total_pages))
    setSearchParams(next, { replace: true })
  }, [data, filters.page, searchParams, setSearchParams])

  const hasFilters = FILTER_KEYS.some((filterKey) => filters[filterKey])

  const update = useCallback(
    (patch: Partial<Filters>) => {
      const next = new URLSearchParams(searchParams)
      for (const [name, value] of Object.entries(patch)) {
        if (value) next.set(name, String(value))
        else next.delete(name)
      }
      // Any filter change resets paging, otherwise narrowing from page 3 can
      // land the user on a page that no longer exists.
      if (!('page' in patch)) next.delete('page')
      setSearchParams(next)
    },
    [searchParams, setSearchParams],
  )

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold text-slate-900">Candidate interviews</h1>
        <p className="mt-1 text-sm text-slate-600">
          AI-scored interview records. Select a candidate to see per-question feedback.
        </p>
      </header>

      <div className="mb-4">
        <FilterBar
          filters={filters}
          positions={positions.data ?? []}
          onChange={update}
          onClear={() => setSearchParams(new URLSearchParams())}
        />
      </div>

      {/* With results on screen the error rides above them; only a first
          failure, with nothing to show, takes over the page. */}
      {error && data && <ErrorBanner message={error} onRetry={retry} />}

      {error && !data ? (
        <ErrorState
          message={error}
          onRetry={retry}
          // A filter is at fault only when one is set; a dead API is not.
          onClear={hasFilters ? () => setSearchParams(new URLSearchParams()) : undefined}
        />
      ) : (
        <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
          {loading && !data && <TableSkeleton rows={PER_PAGE} />}
          {data && data.items.length === 0 && (
            <EmptyState
              onClear={hasFilters ? () => setSearchParams(new URLSearchParams()) : undefined}
            />
          )}
          {data && data.items.length > 0 && (
            <div className={loading ? 'opacity-60 transition-opacity' : undefined}>
              <InterviewTable items={data.items} search={`?${searchParams}`} />
            </div>
          )}
        </div>
      )}

      {data && data.total_pages > 0 && (
        <Pagination
          page={data.page}
          totalPages={data.total_pages}
          total={data.total}
          onPage={(page) => update({ page })}
        />
      )}
    </div>
  )
}
