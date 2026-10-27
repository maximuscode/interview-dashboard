import type { Band } from '../lib/types'

// The cutoffs live in backend/app/ai.py and arrive with each score, so the two
// sides cannot disagree about which colour a number gets.
const BAND_CLASSES: Record<Band, string> = {
  strong: 'bg-emerald-100 text-emerald-800 ring-emerald-600/20',
  adequate: 'bg-amber-100 text-amber-800 ring-amber-600/20',
  weak: 'bg-rose-100 text-rose-800 ring-rose-600/20',
}

export function ScoreBadge({
  score,
  band,
  size = 'sm',
}: {
  score: number
  band: Band
  size?: 'sm' | 'lg'
}) {
  return (
    <span
      className={`inline-flex items-center rounded-full font-semibold ring-1 ring-inset tabular-nums ${BAND_CLASSES[band]} ${
        size === 'lg' ? 'px-3 py-1 text-base' : 'px-2 py-0.5 text-sm'
      }`}
    >
      {score}
    </span>
  )
}
