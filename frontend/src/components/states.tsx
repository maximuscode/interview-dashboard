export function ErrorState({
  message,
  onRetry,
  onClear,
}: {
  message: string
  onRetry?: () => void
  onClear?: () => void
}) {
  // A rejected filter is a slip, not a fault; "Something went wrong" overstates
  // it and tells the user nothing they can act on. The message does that.
  const isFilterProblem = Boolean(onClear)

  return (
    <div
      role="alert"
      className={`rounded-lg border p-6 text-center ${
        isFilterProblem ? 'border-amber-300 bg-amber-50' : 'border-rose-200 bg-rose-50'
      }`}
    >
      <p className={`font-medium ${isFilterProblem ? 'text-amber-900' : 'text-rose-900'}`}>
        {isFilterProblem ? 'That filter needs a tweak' : 'Something went wrong'}
      </p>
      <p className={`mt-1 text-sm ${isFilterProblem ? 'text-amber-800' : 'text-rose-700'}`}>
        {message}
      </p>
      <div className="mt-4 flex justify-center gap-3">
        {onClear && (
          <button
            type="button"
            onClick={onClear}
            className="rounded-md bg-amber-600 px-4 py-2 text-sm font-medium text-white hover:bg-amber-700"
          >
            Clear filters
          </button>
        )}
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className={`rounded-md px-4 py-2 text-sm font-medium ${
              isFilterProblem
                ? 'border border-amber-400 text-amber-900 hover:bg-amber-100'
                : 'bg-rose-600 text-white hover:bg-rose-700'
            }`}
          >
            Try again
          </button>
        )}
      </div>
    </div>
  )
}

export function EmptyState({ onClear }: { onClear?: () => void }) {
  // Without filters there is nothing to widen, so do not blame filters or
  // offer a Clear button that would change nothing.
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-10 text-center">
      <p className="font-medium text-slate-900">
        {onClear ? 'No interviews match these filters' : 'No interviews yet'}
      </p>
      <p className="mt-1 text-sm text-slate-500">
        {onClear
          ? 'Try widening the date range or lowering the minimum score.'
          : 'Seed the database with `python -m app.seed` to load sample data.'}
      </p>
      {onClear && (
        <button
          type="button"
          onClick={onClear}
          className="mt-4 rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          Clear filters
        </button>
      )}
    </div>
  )
}

/** Skeleton rows sized like the real table, so loading does not shift the layout. */
export function TableSkeleton({ rows = 6 }: { rows?: number }) {
  return (
    <div className="divide-y divide-slate-100" aria-busy="true" aria-label="Loading interviews">
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="flex items-center gap-4 px-4 py-4">
          <div className="h-4 w-40 animate-pulse rounded bg-slate-200" />
          <div className="h-4 w-36 animate-pulse rounded bg-slate-200" />
          <div className="ml-auto h-6 w-10 animate-pulse rounded-full bg-slate-200" />
        </div>
      ))}
    </div>
  )
}

export function DetailSkeleton() {
  return (
    <div className="space-y-4" aria-busy="true" aria-label="Loading interview">
      <div className="h-24 animate-pulse rounded-lg bg-slate-200" />
      {Array.from({ length: 3 }, (_, i) => (
        <div key={i} className="h-32 animate-pulse rounded-lg bg-slate-200" />
      ))}
    </div>
  )
}
