import type { Question } from '../lib/types'
import { ScoreBadge } from './ScoreBadge'

export function QuestionCard({ question, index }: { question: Question; index: number }) {
  return (
    <li className="rounded-lg border border-slate-200 bg-white p-4 sm:p-5">
      <div className="flex items-start justify-between gap-4">
        <h3 className="font-medium text-slate-900">
          <span className="mr-2 text-slate-400">Q{index + 1}</span>
          {question.prompt}
        </h3>
        <div className="shrink-0">
          <ScoreBadge score={question.score} band={question.band} />
        </div>
      </div>

      <p className="mt-3 border-l-2 border-slate-200 pl-3 text-sm text-slate-700">{question.response}</p>

      <div className="mt-4 rounded-md bg-slate-50 p-3">
        <p className="text-xs font-medium uppercase tracking-wide text-slate-500">AI feedback</p>
        <p className="mt-1 text-sm text-slate-700">{question.feedback}</p>
      </div>
    </li>
  )
}
