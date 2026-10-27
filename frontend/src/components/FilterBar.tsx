import type { Filters } from '../lib/types'
import { useDebouncedField } from '../lib/useDebouncedField'

const inputClass =
  'w-full rounded-md border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-500'

type Props = {
  filters: Filters
  positions: string[]
  onChange: (patch: Partial<Filters>) => void
  onClear: () => void
}

export function FilterBar({ filters, positions, onChange, onClear }: Props) {
  const [search, setSearch] = useDebouncedField(filters.q, (q) => onChange({ q }))
  // Clamp here rather than letting the API reject it: a typed "101" is a slip,
  // not a question worth an error message.
  const [minScore, setMinScore] = useDebouncedField(filters.min_score, (value) => {
    const trimmed = value.trim()
    if (trimmed === '') return onChange({ min_score: '' })
    const number = Number(trimmed)
    if (!Number.isFinite(number)) return
    onChange({ min_score: String(Math.min(100, Math.max(0, Math.round(number)))) })
  })

  const active =
    filters.position || filters.min_score || filters.date_from || filters.date_to ||
    filters.q || filters.reviewed

  return (
    <div className="grid grid-cols-1 gap-3 rounded-lg border border-slate-200 bg-white p-4 sm:grid-cols-2 lg:grid-cols-6">
      <label className="lg:col-span-2">
        <span className="mb-1 block text-xs font-medium text-slate-600">Search</span>
        <input
          type="search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Candidate or position"
          className={inputClass}
        />
      </label>

      <label>
        <span className="mb-1 block text-xs font-medium text-slate-600">Position</span>
        <select
          value={filters.position}
          onChange={(e) => onChange({ position: e.target.value })}
          className={inputClass}
        >
          <option value="">All positions</option>
          {positions.map((position) => (
            <option key={position} value={position}>
              {position}
            </option>
          ))}
        </select>
      </label>

      <label>
        <span className="mb-1 block text-xs font-medium text-slate-600">Min score</span>
        <input
          type="number"
          min={0}
          max={100}
          value={minScore}
          onChange={(e) => setMinScore(e.target.value)}
          placeholder="0-100"
          className={inputClass}
        />
      </label>

      <label>
        <span className="mb-1 block text-xs font-medium text-slate-600">From</span>
        <input
          type="date"
          value={filters.date_from}
          onChange={(e) => onChange({ date_from: e.target.value })}
          className={inputClass}
        />
      </label>

      <label>
        <span className="mb-1 block text-xs font-medium text-slate-600">To</span>
        <input
          type="date"
          value={filters.date_to}
          onChange={(e) => onChange({ date_to: e.target.value })}
          className={inputClass}
        />
      </label>

      <div className="flex items-end gap-4 sm:col-span-2 lg:col-span-6">
        <label className="flex items-center gap-2 text-sm text-slate-700">
          <input
            type="checkbox"
            checked={filters.reviewed === 'true'}
            onChange={(e) => onChange({ reviewed: e.target.checked ? 'true' : '' })}
            className="h-4 w-4 rounded border-slate-300"
          />
          Reviewed only
        </label>

        {active && (
          <button
            type="button"
            onClick={onClear}
            className="ml-auto text-sm font-medium text-slate-600 underline hover:text-slate-900"
          >
            Clear filters
          </button>
        )}
      </div>
    </div>
  )
}
