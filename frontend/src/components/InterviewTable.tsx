import { Link } from 'react-router-dom'
import { formatDate } from '../lib/format'
import type { InterviewSummary } from '../lib/types'
import { ScoreBadge } from './ScoreBadge'

function ReviewedTag({ reviewed }: { reviewed: boolean }) {
  return reviewed ? (
    <span className="rounded-full bg-slate-900 px-2 py-0.5 text-xs font-medium text-white">Reviewed</span>
  ) : (
    <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-500">Pending</span>
  )
}

export function InterviewTable({ items, search }: { items: InterviewSummary[]; search: string }) {
  return (
    <>
      {/* Table on desktop, stacked cards below md where columns stop fitting. */}
      <table className="hidden w-full md:table">
        <thead>
          <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500">
            <th className="px-4 py-3 font-medium">Candidate</th>
            <th className="px-4 py-3 font-medium">Position</th>
            <th className="px-4 py-3 font-medium">Date</th>
            <th className="px-4 py-3 font-medium">Status</th>
            <th className="px-4 py-3 text-right font-medium">Score</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {items.map((item) => (
            <tr key={item.id} className="hover:bg-slate-50">
              <td className="px-4 py-3">
                <Link
                  to={`/interviews/${item.id}${search}`}
                  className="font-medium text-slate-900 hover:underline"
                >
                  {item.candidate_name}
                </Link>
                <div className="text-xs text-slate-500">{item.candidate_email}</div>
              </td>
              <td className="px-4 py-3 text-slate-700">{item.position}</td>
              <td className="px-4 py-3 whitespace-nowrap text-slate-700">{formatDate(item.interview_date)}</td>
              <td className="px-4 py-3">
                <ReviewedTag reviewed={item.reviewed} />
              </td>
              <td className="px-4 py-3 text-right">
                <ScoreBadge score={item.overall_score} band={item.band} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <ul className="divide-y divide-slate-100 md:hidden">
        {items.map((item) => (
          <li key={item.id}>
            <Link to={`/interviews/${item.id}${search}`} className="block px-4 py-4 hover:bg-slate-50">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-medium text-slate-900">{item.candidate_name}</p>
                  <p className="text-sm text-slate-600">{item.position}</p>
                  <p className="mt-1 text-xs text-slate-500">{formatDate(item.interview_date)}</p>
                </div>
                <div className="flex shrink-0 flex-col items-end gap-2">
                  <ScoreBadge score={item.overall_score} band={item.band} />
                  <ReviewedTag reviewed={item.reviewed} />
                </div>
              </div>
            </Link>
          </li>
        ))}
      </ul>
    </>
  )
}
