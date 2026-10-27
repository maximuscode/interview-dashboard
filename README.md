# AI-Powered Candidate Interview Dashboard

A FastAPI backend serving candidate interview data with mocked AI scoring, and a React SPA for
browsing and reviewing it.

## Running it

```bash
./dev.sh
```

Installs what is missing, seeds the database, and starts both halves:

- Dashboard: http://localhost:5173
- API docs (Swagger): http://localhost:8000/docs

Ctrl-C stops both. `./dev.sh --reseed` regenerates the database first.

<details>
<summary>Running the two halves separately</summary>

```bash
# Backend -> http://localhost:8000
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m app.seed          # once; the server will not start unseeded
uvicorn app.main:app --reload

# Frontend -> http://localhost:5173
cd frontend
bun install
bun run dev
```

Seeding is a separate step rather than something the server does at startup.
A check-then-insert at startup races across workers: under `uvicorn --workers 4`
every worker finds an empty table and inserts its own copy of the dataset.

The frontend reads `VITE_API_URL`, defaulting to `http://localhost:8000`. See
`frontend/.env.example`.

</details>

### Checks

```bash
./check.sh
```

Runs everything CI would: backend lint (ruff) and tests (pytest, 43), frontend
types (tsc), lint (oxlint) and tests (vitest, 19). Individually:

```bash
cd backend  && .venv/bin/ruff check . && .venv/bin/python -m pytest -q
cd frontend && bun run typecheck && bun run lint && bun run test
```

## API

| Method | Path | Notes |
|---|---|---|
| `GET` | `/interviews` | Paginated list with filters |
| `GET` | `/interviews/positions` | Feeds the position dropdown |
| `GET` | `/interviews/{id}` | Full detail with questions; 404 if unknown |
| `PATCH` | `/interviews/{id}` | `{"reviewed": bool}` |
| `GET` | `/health` | Liveness |

List query params, all optional and combined with AND: `page`, `per_page` (max 100),
`position`, `min_score`, `date_from`, `date_to`, `q` (searches name and position), `reviewed`.

Responses carry `total` and `total_pages` so the UI renders real pagination. Errors are always
JSON with a `detail` field.

```bash
curl "localhost:8000/interviews?min_score=85&position=Data%20Scientist"
```

## How the mocked AI works

`backend/app/ai.py` is the only place scoring happens. It is the single seam where a real
model call would go. Three decisions matter:

**Scores are generated once, at seed time.** Not per request. A per-request random score makes
the list and detail views disagree about the same candidate, which reads as a bug rather than
as mocking.

**An interview's overall score is the mean of its question scores**, so the two views always
agree. Each candidate also carries a `calibre` offset that shifts all their answers together;
without it, averaging 4–6 independent draws collapses every score toward the mean and
`min_score` stops discriminating.

**Scores carry their band.** Each score arrives with `band` (`strong` / `adequate` / `weak`),
so the UI colours badges from the backend's cutoffs instead of duplicating them.

**Feedback is tied to the score band and the role.** Each role has a stated requirement, and
feedback names it: "Strong evidence of designing systems that hold up under load." Feedback
that contradicts its own number is the detail view's most visible failure mode.

## Error handling

Validation failures come back as one readable sentence, not FastAPI's default
list of objects: `min_score=101` gives "Minimum score must be 100 or less."

The UI tries not to need them. The min-score box clamps to 0–100 as you type,
and a page number past the end snaps to the last real page. When an error does
arrive, the last good results stay on screen with the message above them; only
a first load with nothing to show takes over the page. A rejected filter is
styled as a tweak with a Clear filters button, not as a failure.

## Mobile

The table becomes stacked cards below `md`; the filter bar goes from six
columns to two to one. Verified at 390px (iPhone) for the list, detail and
error states, with the breakpoints pinned by tests in
`src/components/InterviewTable.test.tsx`.

## Frontend notes

No state library. Filters and page live in the URL (`useSearchParams`), so a filtered view is
shareable, survives reload, and works with the back button.

Text inputs are debounced 300ms. `useApi` drops responses whose inputs have since changed, so a
slow early request cannot overwrite a newer one. Loading renders skeletons sized like the real
content rather than a spinner, so nothing shifts on load.

## Project layout

```
backend/app/
  main.py         FastAPI app, CORS, startup checks
  routers/        endpoints (HTTP concerns only)
  queries.py      filtering and paging, reusable by other consumers
  models.py       Pydantic wire schemas
  db.py           SQLAlchemy models
  seed.py         deterministic dataset
  ai.py           mocked scoring and feedback
frontend/src/
  pages/          InterviewList, InterviewDetail
  components/     table, filters, pagination, states
  lib/            api client, hooks, types
  test/           vitest setup
```

## Scope

Mock data, per the brief. Both optional bonuses are implemented: the reviewed flag (persisted
server-side) and search.

Deliberately out of scope: auth, real Postgres, real LLM inference, deployment, CI, caching,
rate limiting.

## Docs

- `evidence/`: screenshots of all 14 screen states, with an index
- `SCALE.md`: scale plan covering measured state at 100k, open items and their triggers
- `PLAN.md`: build plan and assumptions
- `CLAUDE.md`: architectural decisions and their reasoning
