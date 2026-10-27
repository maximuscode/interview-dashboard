import { useCallback, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { QuestionCard } from '../components/QuestionCard'
import { ScoreBadge } from '../components/ScoreBadge'
import { DetailSkeleton, ErrorState } from '../components/states'
import { getInterview, setReviewed } from '../lib/api'
import { formatDate } from '../lib/format'
import type { InterviewDetail as Interview } from '../lib/types'
import { useApi } from '../lib/useApi'

export function InterviewDetail() {
  const { id = '' } = useParams()
  // Carries the list's filter query string, so Back returns to the same view.
  const { search } = useLocation()

  const { data, loading, error, retry, setData } = useApi<Interview>(() => getInterview(id), [id])
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)

  const toggleReviewed = useCallback(async () => {
    if (!data) return
    setSaving(true)
    setSaveError(null)
    try {
      setData(await setReviewed(data.id, !data.reviewed))
    } catch (err) {
      setSaveError((err as Error).message)
    } finally {
      setSaving(false)
    }
  }, [data, setData])

  return (
    <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6">
      <Link to={`/${search}`} className="text-sm font-medium text-slate-600 hover:text-slate-900">
        ← Back to interviews
      </Link>

      <div className="mt-4">
        {loading && <DetailSkeleton />}
        {error && <ErrorState message={error} onRetry={retry} />}

        {data && (
          <>
            <header className="rounded-lg border border-slate-200 bg-white p-6">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <h1 className="text-2xl font-semibold text-slate-900">{data.candidate_name}</h1>
                  <p className="mt-1 text-slate-600">
                    {data.position} · {formatDate(data.interview_date)}
                  </p>
                  <p className="text-sm text-slate-500">{data.candidate_email}</p>
                </div>

                <div className="flex flex-col items-end gap-3">
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-slate-500">Overall</span>
                    <ScoreBadge score={data.overall_score} band={data.band} size="lg" />
                  </div>
                  <button
                    type="button"
                    onClick={toggleReviewed}
                    disabled={saving}
                    className={`rounded-md px-3 py-1.5 text-sm font-medium disabled:opacity-50 ${
                      data.reviewed
                        ? 'bg-slate-900 text-white hover:bg-slate-700'
                        : 'border border-slate-300 text-slate-700 hover:bg-slate-50'
                    }`}
                  >
                    {data.reviewed ? '✓ Reviewed' : 'Mark as reviewed'}
                  </button>
                </div>
              </div>
              {saveError && <p className="mt-3 text-sm text-rose-700">{saveError}</p>}
            </header>

            <h2 className="mt-8 mb-3 text-sm font-medium uppercase tracking-wide text-slate-500">
              {data.questions.length} questions
            </h2>
            <ul className="space-y-4">
              {data.questions.map((question, index) => (
                <QuestionCard key={question.id} question={question} index={index} />
              ))}
            </ul>
          </>
        )}
      </div>
    </div>
  )
}
