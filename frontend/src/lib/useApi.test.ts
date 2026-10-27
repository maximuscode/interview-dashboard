import { act, renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { useApi } from './useApi'

describe('useApi', () => {
  it('keeps the last good data when a later request fails', async () => {
    // A rejected filter must not blank the table the user is reading.
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce('first page')
      .mockRejectedValueOnce(new Error('Minimum score must be 100 or less.'))

    const { result, rerender } = renderHook(({ key }) => useApi(fetcher, [key]), {
      initialProps: { key: 'a' },
    })
    await waitFor(() => expect(result.current.data).toBe('first page'))

    rerender({ key: 'b' })
    await waitFor(() => expect(result.current.error).toMatch(/100 or less/))
    expect(result.current.data).toBe('first page')
  })

  it('clears a previous error once a request succeeds', async () => {
    const fetcher = vi
      .fn()
      .mockRejectedValueOnce(new Error('boom'))
      .mockResolvedValueOnce('recovered')

    const { result, rerender } = renderHook(({ key }) => useApi(fetcher, [key]), {
      initialProps: { key: 'a' },
    })
    await waitFor(() => expect(result.current.error).toBe('boom'))

    rerender({ key: 'b' })
    await waitFor(() => expect(result.current.data).toBe('recovered'))
    expect(result.current.error).toBeNull()
  })

  it('ignores a slow early response that a newer request has superseded', async () => {
    let resolveFirst: (value: string) => void = () => {}
    const fetcher = vi
      .fn()
      .mockImplementationOnce(() => new Promise<string>((r) => (resolveFirst = r)))
      .mockResolvedValueOnce('second')

    const { result, rerender } = renderHook(({ key }) => useApi(fetcher, [key]), {
      initialProps: { key: 'a' },
    })
    rerender({ key: 'b' })
    await waitFor(() => expect(result.current.data).toBe('second'))

    await act(async () => resolveFirst('first'))
    expect(result.current.data).toBe('second')
  })

  it('retry re-runs the request', async () => {
    const fetcher = vi.fn().mockResolvedValue('ok')
    const { result } = renderHook(() => useApi(fetcher, []))
    await waitFor(() => expect(result.current.data).toBe('ok'))

    act(() => result.current.retry())
    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(2))
  })

  it('retry and setData keep a stable identity across renders', async () => {
    const { result, rerender } = renderHook(() => useApi(vi.fn().mockResolvedValue('ok'), []))
    await waitFor(() => expect(result.current.data).toBe('ok'))

    const { retry, setData } = result.current
    rerender()
    expect(result.current.retry).toBe(retry)
    expect(result.current.setData).toBe(setData)
  })
})
