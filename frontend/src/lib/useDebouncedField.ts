import { useEffect, useRef, useState } from 'react'

/**
 * Keeps a text field responsive while its committed value lives in the URL.
 *
 * Writing to the URL on every keystroke re-renders the input mid-edit, which
 * drops the caret and any selection: typing "85" over a selected value yields
 * "05". Local state owns the keystrokes; the URL is updated on a pause.
 */
export function useDebouncedField(committed: string, commit: (value: string) => void, delay = 300) {
  const [value, setValue] = useState(committed)

  // A pending timer must commit against the CURRENT url, not the one captured
  // when typing began. Without this, picking a position while a search debounce
  // is in flight loses the position when the timer fires.
  const latest = useRef(commit)
  useEffect(() => {
    latest.current = commit
  })

  // Follow external changes (Clear filters, back button) without clobbering typing.
  useEffect(() => setValue(committed), [committed])

  useEffect(() => {
    if (value === committed) return
    const timer = setTimeout(() => latest.current(value), delay)
    return () => clearTimeout(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value])

  return [value, setValue] as const
}
