# PLAN.md: AI-Powered Candidate Interview Dashboard

## 0. Background

Part of an AI-powered interview analysis platform for recruiters. The platform lets recruiters
review candidate interviews, view automated scoring and feedback for candidate responses based
on specific job requirements, and browse historical interview data in a performant, intuitive
web dashboard.

## 1. Goal

Build a two-part take-home deliverable:

1. **Backend**: FastAPI service exposing paginated, filterable interview data with mocked AI scoring and feedback, documented via Swagger/OpenAPI.
2. **Frontend**: React (Vite + React Router) SPA with an interview list view and an interview detail view, including filters, pagination, loading and error states.

Mock data is acceptable. The evaluation targets API/UI logic, code structure, usability, error handling, and completeness, not production deployment or security.

## 2. Assumptions

These are the judgment calls made where the problem statement left room. Each is cheap to reverse if wrong.

- **Database**: SQLAlchemy models run real queries against a SQLite file seeded deterministically at startup (fixed RNG seed). Filtering and pagination are real SQL, so the ORM layer is exercised rather than decorative, and moving to Postgres is a connection-string change. No Docker required. This satisfies "can simulate/mock DB connection as necessary" while keeping setup to two commands.
- **AI evaluation**: Scores and feedback are generated once at seed time, not per request, so the same interview returns the same score on every call. A per-request random score would make the list and detail views disagree, which reads as a bug. The "mocked logic" requirement is met by a dedicated scoring module that is the single place a real model call would slot in.
- **Overall score**: Computed as the rounded mean of per-question scores, so list and detail views are consistent with each other.
- **Stable ids**: `uuid4` reads `os.urandom`, which the seed cannot reach, so the seeder temporarily patches it with a seeded generator. Without this, reseeding would invalidate every bookmarked detail URL.
- **Dataset size**: 60 interviews across 6 positions, each with 4–6 questions. Enough to exercise pagination and filters meaningfully.
- **Reviewed flag (bonus)**: A column on the interview table, mutated via `PATCH`. Persists in the SQLite file across restarts.
- **Auth**: None. Explicitly out of scope per the problem statement.

## 3. Architecture

```
test-mercor/
├── PLAN.md
├── README.md                  # how to run both halves
├── backend/
│   ├── pyproject.toml
│   ├── app/
│   │   ├── main.py            # FastAPI app, CORS, router mount
│   │   ├── config.py          # settings (port, CORS origins, seed)
│   │   ├── models.py          # Pydantic response/request schemas
│   │   ├── db.py              # SQLAlchemy engine, session, ORM models
│   │   ├── seed.py            # deterministic fake data generation
│   │   ├── ai.py              # mocked AI scoring + feedback
│   │   └── routers/
│   │       └── interviews.py  # GET /interviews, GET /interviews/{id}, PATCH reviewed
│   └── tests/
│       └── test_interviews.py
└── frontend/
    ├── package.json
    ├── index.html
    ├── vite.config.ts
    └── src/
        ├── main.tsx                    # router setup
        ├── pages/
        │   ├── InterviewList.tsx       # route /
        │   └── InterviewDetail.tsx     # route /interviews/:id
        ├── components/
        │   ├── InterviewTable.tsx
        │   ├── FilterBar.tsx
        │   ├── Pagination.tsx
        │   ├── ScoreBadge.tsx
        │   ├── QuestionCard.tsx
        │   └── states.tsx              # Loading, ErrorState, EmptyState
        └── lib/
            ├── api.ts                  # typed fetch client
            ├── useApi.ts               # fetch + loading/error hook
            └── types.ts                # shared TS types mirroring the API
```

**Separation of concerns**: `ai.py` knows nothing about HTTP; `routers/` knows nothing about how scores are produced; the frontend `lib/api.ts` is the only module that talks to the network.

**Dependencies**: `fastapi`, `uvicorn[standard]`, `sqlalchemy`, `pydantic`, `pydantic-settings`; `pytest` and `httpx` under the `dev` extra.

## 4. Data model

```
Interview
  id: str (uuid)
  candidate_name: str
  candidate_email: str
  position: str
  interview_date: date
  overall_score: int        # 0-100, mean of question scores
  reviewed: bool
  questions: list[Question] # detail response only

Question
  id: str
  prompt: str
  response: str             # candidate's answer
  score: int                # 0-100
  feedback: str             # 1-2 sentences
```

The list endpoint returns `Interview` without `questions` to keep payloads small; the detail endpoint returns the full object.

## 5. API contract

### `GET /interviews`

| Param | Type | Default | Notes |
|---|---|---|---|
| `page` | int ≥ 1 | 1 | |
| `per_page` | int 1–100 | 20 | Capped to stop unbounded reads |
| `position` | str | n/a | Exact match, case-insensitive |
| `min_score` | int 0–100 | n/a | Inclusive lower bound on `overall_score` |
| `date_from` | date | n/a | Inclusive |
| `date_to` | date | n/a | Inclusive |
| `q` | str | n/a | Bonus: substring search over candidate name and position |
| `reviewed` | bool | n/a | Bonus: filter by review status |

Response:

```json
{
  "items": [ /* Interview without questions */ ],
  "page": 1,
  "per_page": 20,
  "total": 60,
  "total_pages": 3
}
```

Returning `total` and `total_pages` lets the UI render real pagination instead of guessing whether a next page exists.

### `GET /interviews/{id}`

Returns the full interview with `questions`. Returns `404` with a JSON error body when the id is unknown.

### `PATCH /interviews/{id}` *(bonus)*

Body `{"reviewed": true}`. Returns the updated interview. `404` on unknown id.

### Errors

Validation failures return FastAPI's standard `422`. All error responses are JSON with a `detail` field, so the frontend has one shape to handle.

### Docs

Swagger UI at `/docs`, ReDoc at `/redoc`, schema at `/openapi.json`, all enabled by default in FastAPI. Every endpoint carries a `summary`, `description`, and `response_model` so the generated docs are usable rather than bare.

## 6. Mocked AI layer

`ai.py` exposes two functions:

```python
def score_response(question: str, response: str, position: str) -> int
def generate_feedback(score: int, question: str) -> str
```

Scores are drawn from a seeded RNG, weighted so the distribution spans the full 0–100 range with most values in 55–90 (a realistic-looking spread rather than uniform noise). Feedback is selected from score-banded templates (strong ≥80, adequate 60–79, weak <60) so the text and the number never contradict each other. Contradictory feedback is the detail view's most visible failure mode, so this is worth the small extra structure.

This module is the single seam where a real LLM call would replace the mock.

## 7. Frontend design

**Stack**: Vite + React + React Router + Tailwind, installed with bun. Client-only SPA, as the brief asks for an "SPA experience". Both routes fetch on mount.

**List view (`/`)**

- Table: candidate name, position, interview date, overall score badge, reviewed status.
- Filter bar above the table: position dropdown, min-score input, date range pair, search box. Filters sync to URL query params so a filtered view is shareable and survives refresh.
- Pagination control below: previous/next plus page indicator, driven by `total_pages`.
- Clicking a row navigates to the detail view.
- Filter changes reset to page 1, otherwise a user on page 3 applies a filter and lands on an empty page.

**Detail view (`/interviews/[id]`)**

- Header: candidate name, position, date, overall score, reviewed toggle.
- Per-question cards: question prompt, candidate response, score badge, feedback.
- Back link to the list that preserves the prior filter state.

**UI/UX**

- Tailwind CSS. Responsive: table collapses to stacked cards under `md`.
- Score badge colour-coded by band (green ≥80, amber 60–79, red <60) with the number always shown, so the colour is reinforcement rather than the only signal.
- **Loading**: skeleton rows in the table, skeleton cards in detail. Not a bare spinner, because layout shift on load is the thing being avoided.
- **Error**: inline error panel with the message and a retry button. Network failure, 404, and 422 each produce a distinct message.
- **Empty**: distinct state for "no interviews match these filters" with a clear-filters action, separate from the error state.

**Data fetching**: client-side `fetch` through `lib/api.ts`, wrapped in a small `useApi` hook that returns `{data, loading, error, retry}` so every page handles the three states the same way. The search input is debounced 300 ms so typing does not fire a request per keystroke. No state library: URL params plus local state cover this app's needs, and Redux or Zustand here would be unrequested machinery.

## 8. Build order

Vertical slices, each verifiable before the next begins.

| # | Step | Verify |
|---|---|---|
| 1 | Backend scaffold: FastAPI app, config, health route | `uvicorn` starts, `/docs` loads |
| 2 | Data model + seed + `ai.py` | Seed produces 60 interviews, scores stable across two runs |
| 3 | `GET /interviews` with pagination | Test: page 2 returns the correct slice; `total` is right |
| 4 | Filters: position, min_score, date range | Test: each filter alone and combined narrows as expected |
| 5 | `GET /interviews/{id}` + 404 | Test: known id returns questions; unknown returns 404 |
| 6 | `PATCH` reviewed (bonus) | Test: flag flips and persists across subsequent GETs |
| 7 | Frontend scaffold (Vite, router, Tailwind) + typed API client | List page renders seeded rows |
| 8 | Filter bar + URL sync | Changing a filter updates URL and results; reload preserves |
| 9 | Pagination | Next/prev move pages; disabled at bounds |
| 10 | Detail view | Row click opens detail with all questions and feedback |
| 11 | Loading / error / empty states | Kill the backend: UI shows error with retry, not a blank page |
| 12 | Search (bonus) + reviewed toggle (bonus) | Search narrows results; toggle persists server-side |
| 13 | README | Fresh-clone run-through works from the written steps alone |

## 9. Testing

Backend tests via `pytest` + FastAPI `TestClient`, written against the HTTP endpoints, the public seam, rather than against internal functions, so they survive a refactor of the storage layer.

Covered:
- Pagination slices and `total` arithmetic, including the last partial page.
- Each filter independently, and position + min_score combined.
- `404` on unknown interview id.
- `422` on invalid params (`per_page=0`, `min_score=150`).
- `PATCH` round-trip: flag set, then visible on a subsequent `GET`.

Expected values come from fixture data constructed in the test, not recomputed with the same logic the endpoint uses. A test that reimplements the filter it is testing cannot disagree with the code.

No frontend test suite. For a take-home of this scope the time is better spent on the UI itself; this is a deliberate tradeoff, noted here rather than left silent.

## 10. Running locally

Full detail goes in `README.md`. Shape:

```bash
# Backend: http://localhost:8000, docs at /docs
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e .
uvicorn app.main:app --reload

# Frontend: http://localhost:5173
cd frontend
bun install
bun run dev
```

Frontend reads `VITE_API_URL`, defaulting to `http://localhost:8000`. Backend enables CORS for `http://localhost:5173`.

## 11. Out of scope

Stated explicitly so the omissions read as decisions:

- Authentication and authorization.
- A real Postgres instance or migrations (SQLite stands in; the ORM layer is real).
- Real LLM inference.
- Deployment, containerization, CI.
- Frontend unit tests.
- Caching, rate limiting, observability.

## 12. Status

Built and verified.

- Backend: all endpoints, every filter, pagination, both bonuses. 27 passing tests.
- Frontend: list and detail views, URL-synced filters, pagination, reviewed toggle, and
  distinct loading, error and empty states. Verified in a browser against the live API.
- One bug found and fixed during verification: the min-score input wrote to the URL on every
  keystroke, so typing "85" over a selection produced `min_score=05`. Fixed with a shared
  `useDebouncedField` hook.
- One gap closed after re-reading the brief: feedback now names the role requirement being
  assessed, since the brief asks for scoring "based on specific job requirements".

Audited afterwards; all 10 findings fixed:

- Search escapes LIKE wildcards (`?q=%` returned all 60 rows), with two tests pinning it.
- A pending search debounce no longer drops a filter set while it was in flight.
- Seeding moved out of app startup into `python -m app.seed`, so it cannot race across workers.
- Filtering and paging moved from the handler into `app/queries.py`.
- The API sends each score's band, so the UI no longer duplicates the 80/60 cutoffs.
- `setData` is stable; the unused `force` flag is gone; OFFSET paging's limit is documented.

Then hardened against the inputs users actually produce:

- Validation errors are one readable sentence ("Minimum score must be 100 or less."), not
  FastAPI's default list of objects, which the UI rendered as "Request failed (422)".
- Min-score clamps client-side; a page past the end snaps to the last real page; a backwards
  date range is rejected with an explanation instead of an empty list.
- An error no longer blanks the table: the last good results stay with the message above them.
  A filter problem is styled as a tweak, not a failure.
- 43 backend and 19 frontend tests, plus lint on both halves, all via `./check.sh`.
- Mobile verified at 390px for list, detail and error states; breakpoints pinned by tests.

Then benchmarked at 100k interviews and indexed accordingly: two composite
indexes covering both the filter and the sort took every filtered page from
0.35–4.7ms to 0.01ms, and deep pagination from 79ms to 1ms. The boolean index
on `reviewed` was deleted as a pessimisation. `SCALE.md` is the scale plan: current numbers,
remaining open items and the threshold that triggers each.

`./dev.sh` runs the whole thing, `./check.sh` verifies it. See `README.md` to run it and
`CLAUDE.md` for the decisions.
