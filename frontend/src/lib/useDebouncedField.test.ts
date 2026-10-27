import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useDebouncedField } from './useDebouncedField'

beforeEach(() => vi.useFakeTimers())
afterEach(() => vi.useRealTimers())

describe('useDebouncedField', () => {
  it('commits once after typing stops, not per keystroke', () => {
    const commit = vi.fn()
    const { result } = renderHook(() => useDebouncedField('', commit))

    for (const value of ['8', '85', '857']) {
      act(() => result.current[1](value))
    }
    expect(commit).not.toHaveBeenCalled()

    act(() => void vi.advanceTimersByTime(300))
    expect(commit).toHaveBeenCalledTimes(1)
    expect(commit).toHaveBeenCalledWith('857')
  })

  it('uses the newest commit, so a pending timer cannot drop another filter', () => {
    // The bug: the timer held the commit captured when typing began, which
    // wrote the URL as it was then and lost a filter set in between.
    const stale = vi.fn()
    const fresh = vi.fn()
    const { result, rerender } = renderHook(
      ({ commit }) => useDebouncedField('', commit),
      { initialProps: { commit: stale } },
    )

    act(() => result.current[1]('tanaka'))
    rerender({ commit: fresh })
    act(() => void vi.advanceTimersByTime(300))

    expect(stale).not.toHaveBeenCalled()
    expect(fresh).toHaveBeenCalledWith('tanaka')
  })

  it('follows an external change, so Clear filters empties the box', () => {
    const { result, rerender } = renderHook(
      ({ committed }) => useDebouncedField(committed, vi.fn()),
      { initialProps: { committed: 'tanaka' } },
    )
    expect(result.current[0]).toBe('tanaka')

    rerender({ committed: '' })
    expect(result.current[0]).toBe('')
  })

  it('does not commit a value that already matches the URL', () => {
    const commit = vi.fn()
    renderHook(() => useDebouncedField('tanaka', commit))
    act(() => void vi.advanceTimersByTime(300))
    expect(commit).not.toHaveBeenCalled()
  })
})
