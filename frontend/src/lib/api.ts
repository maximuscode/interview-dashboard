import type { InterviewDetail, InterviewPage } from './types'

const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export const PER_PAGE = 10

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${BASE}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      ...init,
    })
  } catch {
    // fetch only rejects on network failure, so the API being down lands here.
    throw new Error(`Cannot reach the API at ${BASE}. Is the backend running?`)
  }

  if (!response.ok) {
    // Every error from the API is JSON with a `detail` field; fall back in case
    // something upstream (a proxy, say) returns HTML instead.
    const detail = await response
      .json()
      .then((body) => body.detail)
      .catch(() => null)
    throw new Error(
      typeof detail === 'string' ? detail : `Request failed (${response.status}).`,
    )
  }

  return response.json() as Promise<T>
}

export function listInterviews(params: URLSearchParams) {
  return request<InterviewPage>(`/interviews?${params}`)
}

export function getInterview(id: string) {
  return request<InterviewDetail>(`/interviews/${id}`)
}

export function listPositions() {
  return request<string[]>('/interviews/positions')
}

export function setReviewed(id: string, reviewed: boolean) {
  return request<InterviewDetail>(`/interviews/${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ reviewed }),
  })
}
