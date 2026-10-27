# CLAUDE.md

Project conventions and settled decisions for the AI-Powered Candidate Interview Dashboard.
Read this before changing code. `PLAN.md` holds the fuller build plan; this file holds the
decisions that are already locked and the reasoning behind them, so they do not get
relitigated or silently reversed.

## What this is

A take-home deliverable: a FastAPI backend serving candidate interview data with mocked AI
scoring, and a React SPA presenting it as a list view and a detail view. Mock data is
acceptable by the brief. The grading targets API and UI logic, code structure, usability,
error handling, and completeness, not deployment or security.

## Layout

```
test-mercor/
├── SCALE.md                   # measured performance at 100k rows
├── evidence/                  # screenshots of every screen state
├── dev.sh                     # one command: install, seed, run both halves
├── check.sh                   # lint + tests, both halves (what CI would run)
├── PLAN.md                    # build plan, assumptions, step order
├── CLAUDE.md                  # this file
├── README.md                  # how to run both halves
├── backend/
│   ├── pyproject.toml
│   ├── interviews.db          # SQLite, generated on first run, not source
│   ├── app/
│   │   ├── main.py            # FastAPI app, CORS, startup check, /health
│   │   ├── config.py          # Settings, APP_-prefixed env overrides
│   │   ├── models.py          # Pydantic wire schemas
│   │   ├── queries.py         # filtering + paging, reusable
│   │   ├── db.py              # SQLAlchemy engine, session, ORM models
│   │   ├── seed.py            # deterministic dataset generation
│   │   ├── ai.py              # mocked AI scoring, role requirements, feedback
│   │   └── routers/
│   │       └── interviews.py  # all interview endpoints
│   └── tests/
│       ├── conftest.py        # in-memory DB + hand-written fixture rows
│       └── test_interviews.py
└── frontend/
    ├── .env.example           # VITE_API_URL
    └── src/
        ├── main.tsx           # router
        ├── pages/             # InterviewList, InterviewDetail
        ├── components/        # table, filters, pagination, cards, states
        └── lib/               # api client, useApi, useDebouncedField, types
```

## Stack decisions (settled)

| Area | Choice | Why |
|---|---|---|
| Backend | FastAPI + SQLAlchemy 2.0 (typed `Mapped[]` style) | Required by the brief; Swagger comes free |
| Database | SQLite file, real ORM queries | Brief allows a simulated DB. Queries actually execute, so the ORM layer is exercised rather than decorative. Moving to Postgres is a connection-string change, and no Docker is needed to run the project |
| Frontend | Vite + React + React Router + Tailwind, installed with bun | The brief asks for an "SPA experience"; client-only routing delivers exactly that with no server-rendering concerns |
| State | URL query params + local state | Filters belong in the URL so a filtered view is shareable and survives refresh. Redux or Zustand here would be unrequested machinery |
| Tests | pytest + FastAPI `TestClient`, backend only | Cheapest proof the filters and pagination are correct |

## Architectural rules

**One seam per concern.** `ai.py` knows nothing about HTTP. `routers/` knows nothing about how
scores are produced. On the frontend, `lib/api.ts` is the only module that touches the network.
Keep it that way. It is what makes the mocked AI swappable for a real model call.

**Wire schemas are separate from ORM models.** `models.py` (Pydantic) and `db.py` (SQLAlchemy)
are deliberately distinct so the HTTP contract and the storage schema can move independently.
Do not return ORM objects shaped by storage convenience.

**The list endpoint omits `questions`.** `InterviewSummary` is the list shape, `InterviewDetail`
extends it with questions. This keeps list payloads small; do not merge them.

## Locked behavioural decisions

**Seeding is its own step, never at startup.** `python -m app.seed`, or `./dev.sh`. A
check-then-insert in the app's lifespan races across workers: with `uvicorn --workers 4`, all
four see an empty table and each inserts the dataset. Startup only *checks* the table exists
and refuses to boot with an actionable message if not.

**Search escapes LIKE wildcards.** `%` and `_` are wildcards, so unescaped user text made
`?q=%` return every row. `queries.py` escapes them and passes `escape="\\"`. Two tests pin it.

**Filtering and paging live in `queries.py`, not the handler.** Handlers do HTTP; `queries.py`
owns the rules so a second consumer reuses them instead of copying. Do not add a repository
class or service layer on top. One table does not need them.

**The API sends `band` with every score.** `strong` / `adequate` / `weak`, computed from the
cutoffs in `ai.py`. The UI colours badges from it rather than re-declaring 80/60, so the badge
colour cannot disagree with the feedback wording.

These were deliberate. Changing one means changing the reasoning too.

**Scores are generated once, at seed time.** Not per request. A per-request random score makes
the list and detail views disagree about the same candidate, which reads as a bug rather than
as mocking. There is a test asserting the two views agree.

**Overall score is derived, not drawn.** It is the rounded mean of the interview's per-question
scores, stored denormalised on the interview row so the list can filter and sort on it without
aggregating per request. Never assign it independently of the question scores.

**Each candidate has a `calibre` offset.** In `seed.py`, one offset shifts all of a candidate's
answer scores together. Without it, averaging 4–6 independent draws collapses every overall
score toward the mean, scores cluster in a narrow band, and `min_score` stops discriminating.
Current spread is 41–94 with all three badge bands populated.

**Feedback is band-matched to the score.** `ai.py` picks from strong (≥80), adequate (60–79) or
weak (<60) pools. Feedback that contradicts its number is the detail view's most visible failure
mode, so the pools are keyed off the score rather than drawn independently.

**Feedback names the role's requirement.** `REQUIREMENTS` in `ai.py` maps each position to the
competency it is assessed on, and feedback ends with "Strong/Partial/Little evidence of <it>".
The brief asks for scoring "based on specific job requirements", and generic praise tells a
recruiter nothing about fit. Unknown positions fall back to `DEFAULT_REQUIREMENT` rather than
raising. Three tests cover this.

**UUIDs are seeded too.** `uuid4` reads `os.urandom`, which an RNG seed cannot reach, so
`build_dataset` temporarily patches it with a seeded generator. Without this, reseeding
invalidates every bookmarked detail URL.

**Ordering is newest-first, tie-broken by id.** Without the id tie-break, rows sharing a date
can reshuffle between page requests and a user paging through sees duplicates or gaps.

**`total` and `total_pages` are in every page response.** The UI renders real pagination from
them instead of inferring whether a next page exists.

**No matches is an empty page, not a 404.** A filter that excludes everything is a normal
result. 404 is reserved for an unknown interview id.

**`per_page` is capped at 100.** Stops an unbounded read via a crafted query string.

## API surface

| Method | Path | Notes |
|---|---|---|
| `GET` | `/interviews` | Paginated list. Filters: `position`, `min_score`, `date_from`, `date_to`, `q`, `reviewed`. All optional, combined with AND |
| `GET` | `/interviews/positions` | Feeds the filter dropdown so the UI does not hard-code the list |
| `GET` | `/interviews/{id}` | Full detail with questions; 404 if unknown |
| `PATCH` | `/interviews/{id}` | Bonus: `{"reviewed": bool}`, persisted server-side |
| `GET` | `/health` | Liveness |

Docs at `/docs` (Swagger), `/redoc`, `/openapi.json`. Every endpoint carries a `summary`,
`description` and `response_model` so the generated docs are usable rather than bare.

Errors are always JSON with a `detail` field, so the frontend has one shape to handle. Validation
failures return FastAPI's standard 422.

**Route order matters**: `/interviews/positions` is declared before `/interviews/{interview_id}`.
Reversed, the literal path gets captured as an id. Keep static segments above parameterised ones.

## Frontend decisions

**The URL is the store.** Filters and page live in `useSearchParams`, not component state or a
store. Shareable, survives reload, back button works. Do not add Redux or Zustand. Two
endpoints do not need one.

**Text inputs are debounced through `useDebouncedField`.** This is not only a performance
measure. Writing to the URL on every keystroke re-renders the input mid-edit and drops the
caret: typing "85" over a selected value produced `min_score=05`. This was a real bug, caught
in the browser. Any new URL-bound text input uses this hook.

**The hook holds `commit` in a ref.** A pending timer must write against the current URL, not
the one captured when typing began. Without the ref, typing in search and then picking a
position within 300ms silently dropped the position when the timer fired.

**Anything returned from `useApi` is stable.** `retry` and `setData` are both wrapped in
`useCallback` so callers can list them in dependency arrays.

**`useApi` guards against stale responses.** Its `active` flag drops a resolved request whose
inputs have since changed, so a slow early response cannot overwrite a newer one.

**Loading renders skeletons, not spinners**, sized like the real content so nothing shifts.

**Three distinct states.** Error (with retry), empty (with clear-filters), and loading are
separate components. An empty filter result is not an error and must not render as one.

## Error handling

**Validation errors are one readable sentence.** `app/main.py` has a
`RequestValidationError` handler that collapses FastAPI's default list-of-objects into
`{"detail": "Minimum score must be 100 or less."}`. The UI shows `detail` to a person, so it
must always be a string. Tests pin the message for every parameter.

**Impossible filter combinations are rejected, not silently empty.** A backwards date range
returns 422 explaining itself, rather than an empty list that reads as "no such candidates".
`ImpossibleFilters` in `queries.py`.

**The UI avoids the error where it can.** Min-score clamps to 0–100 as you type; a page past
the end snaps to the last real page. Validation is a backstop, not the first line of defence.

**An error never blanks existing results.** `useApi` keeps the last good `data` on failure, so
the message rides above the table the user is reading. Only a first load with nothing to show
gets the full-page `ErrorState`.

**A filter problem is not a failure.** With filters set, `ErrorState` renders amber with a
Clear filters button; without them, red. Never offer Clear filters when none are set.

## Testing conventions

Tests target the HTTP surface, not internal functions, so they survive a refactor of the
storage layer.

Each test gets its own in-memory SQLite database seeded from `FIXTURE_ROWS` in `conftest.py`:
five hand-written interviews, not the generated dataset. The startup seeder is bypassed via a
`get_session` dependency override.

**Expected values are literals.** `EXPECTED_SCORES` is written out by hand rather than computed
with the same mean the endpoint uses. A test that reimplements the logic it is testing can never
disagree with the code.

Run: `cd backend && ./.venv/bin/python -m pytest -q`. Currently 43 passing.

Frontend: 19 vitest tests over the parts that had real bugs: API error shapes, the debounce
hook's stale-closure fix, `useApi` keeping data on error and dropping stale responses, and the
responsive breakpoint classes. Both bug-fix tests were confirmed to fail with the fix reverted.

`./check.sh` runs lint and tests for both halves. Keep it green.

Browser-verified: list, filters, search, pagination, detail, reviewed round-trip (confirmed
server-side), error states, and the 390px mobile layout for list, detail and errors.

## Conventions

- Python ≥3.11. Modern type syntax (`str | None`, `list[str]`), `Annotated` for FastAPI params.
- SQLAlchemy 2.0 declarative style with `Mapped[]` annotations. Not the legacy `Column()` style.
- TypeScript on the frontend. No `any` unless genuinely unavoidable.
- pnpm or bun. Never npm or yarn. This project uses bun for the frontend.
- Comments explain **why**, not what. Skip the obvious.
- No `@app.on_event` (deprecated). Use the `lifespan` context manager.
- No Pydantic `class Config` (deprecated). Use `model_config = SettingsConfigDict(...)`.
  The suite runs clean under `-W error::DeprecationWarning`; keep it that way.
- Lint is clean with no suppressions. A `react-hooks/exhaustive-deps` warning means the
  dependency is genuinely wrong. Fix the dependency, do not silence the rule.

## Known performance limits

Measured at 100k interviews; open items and triggers in `SCALE.md`.
Every filtered page is 0.01ms at the database, 2–14ms end to end.

**Two composite indexes carry this** (`db.py`): `ix_interviews_date_id` and
`ix_interviews_position_date`. They cover the filter *and* the
`ORDER BY interview_date DESC, id` that every list query ends with. An index on
the filter column alone makes the planner sort matches in a temp B-tree, which
cost 3.7ms versus 0.01ms. `TestIndexes` asserts the query plans so this cannot
silently regress.

- **Never wrap a filter column in a function.** `lower(position)` made the index
  unusable. The router resolves casing against the known position list instead.
- **`reviewed` has no index on purpose.** A boolean splits the table in half, so
  scanning the date index and filtering (0.01ms) beats seeking and sorting (4.7ms).
- **Do not add a composite for `overall_score`.** Tested; a range predicate
  cannot use the sort columns, so it changes nothing.
- **Search is 114ms worst case** (`LIKE '%term%'` is unindexable). Deliberate;
  needs FTS5 or `pg_trgm`. Revisit past ~500k rows.
- **Postgres is the real next step**, for the single-writer lock, not for speed.
- **Do not cache `count(*)`.** It is 0.4ms at 100k.
- **Keyset pagination is no longer needed.** The composite index dropped deep
  paging from 79ms to 1ms, and keyset would break "jump to page N".

## Out of scope

Stated so the omissions read as decisions, not oversights: authentication, a real Postgres
instance or migrations, real LLM inference, deployment or containerization, CI, frontend unit
tests, caching, rate limiting, observability.

## Status

Complete. Backend: all endpoints, filters, pagination, both bonus features, 27 passing tests.
Frontend: list and detail views, filters with URL sync, pagination, reviewed toggle, loading,
error and empty states, all verified in a browser against the live API.

`README.md` covers running it; `PLAN.md` holds the build plan and assumptions.
