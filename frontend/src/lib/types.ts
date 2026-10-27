// Mirrors the Pydantic schemas in backend/app/models.py.

export type Band = 'strong' | 'adequate' | 'weak'

export type InterviewSummary = {
  id: string
  candidate_name: string
  candidate_email: string
  position: string
  interview_date: string
  overall_score: number
  band: Band
  reviewed: boolean
}

export type Question = {
  id: string
  prompt: string
  response: string
  score: number
  band: Band
  feedback: string
}

export type InterviewDetail = InterviewSummary & {
  questions: Question[]
}

export type InterviewPage = {
  items: InterviewSummary[]
  page: number
  per_page: number
  total: number
  total_pages: number
}

export type Filters = {
  page: number
  position: string
  min_score: string
  date_from: string
  date_to: string
  q: string
  reviewed: string
}
