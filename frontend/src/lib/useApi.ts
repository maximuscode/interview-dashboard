import { useCallback, useEffect, useState } from 'react'

type State<T> = {
  data: T | null
  loading: boolean
  error: string | null
}

/**
 * Runs `fetcher` whenever `deps` change, exposing the three states every page
 * needs to render. `retry` re-runs the same request after a failure.
 */
export function useApi<T>(fetcher: () => Promise<T>, deps: unknown[]) {
  const [state, setState] = useState<State<T>>({ data: null, loading: true, error: null })
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    // Ignore a resolved request whose inputs have since changed, otherwise a
    // slow early response can overwrite a newer one.
    let active = true
    setState((previous) => ({ ...previous, loading: true, error: null }))

    fetcher()
      .then((data) => active && setState({ data, loading: false, error: null }))
      .catch(
        (error: Error) =>
          // Keep the last good data. A rejected filter should surface the
          // message beside the previous results, not blank the page.
          active &&
          setState((previous) => ({ ...previous, loading: false, error: error.message })),
      )

    return () => {
      active = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, attempt])

  const retry = useCallback(() => setAttempt((n) => n + 1), [])

  // Stable identity, so callers can list it in a dependency array.
  const setData = useCallback((data: T) => setState({ data, loading: false, error: null }), [])

  return { ...state, retry, setData }
}
