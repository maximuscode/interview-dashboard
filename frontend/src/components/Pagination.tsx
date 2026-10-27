type Props = {
  page: number
  totalPages: number
  total: number
  onPage: (page: number) => void
}

const buttonClass =
  'rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40'

export function Pagination({ page, totalPages, total, onPage }: Props) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2 px-1 py-3 text-sm text-slate-600">
      <span>
        Page {page} of {totalPages} · {total} interview{total === 1 ? '' : 's'}
      </span>
      <div className="flex gap-2">
        <button type="button" className={buttonClass} disabled={page <= 1} onClick={() => onPage(page - 1)}>
          Previous
        </button>
        <button
          type="button"
          className={buttonClass}
          disabled={page >= totalPages}
          onClick={() => onPage(page + 1)}
        >
          Next
        </button>
      </div>
    </div>
  )
}
