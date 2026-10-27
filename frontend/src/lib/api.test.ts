import { afterEach, describe, expect, it, vi } from 'vitest'
import { listInterviews } from './api'

afterEach(() => vi.unstubAllGlobals())

function respondWith(status: number, body: unknown) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: status >= 200 && status < 300,
      status,
      json: () => Promise.resolve(body),
    }),
  )
}

describe('api error handling', () => {
  it('surfaces the API message so the UI can show it to a person', async () => {
    respondWith(422, { detail: 'Minimum score must be 100 or less.' })
    await expect(listInterviews(new URLSearchParams())).rejects.toThrow(
      'Minimum score must be 100 or less.',
    )
  })

  it('explains an unreachable API rather than showing a bare network error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))
    await expect(listInterviews(new URLSearchParams())).rejects.toThrow(/Cannot reach the API/)
  })

  it('falls back to the status when the body is not the usual JSON', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 502,
        json: () => Promise.reject(new Error('not json')),
      }),
    )
    await expect(listInterviews(new URLSearchParams())).rejects.toThrow('Request failed (502).')
  })

  it('ignores a non-string detail instead of rendering an object', async () => {
    respondWith(422, { detail: [{ msg: 'machine readable' }] })
    await expect(listInterviews(new URLSearchParams())).rejects.toThrow('Request failed (422).')
  })
})
