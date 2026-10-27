# Scale plan

Current state is measured, not estimated: 100,000 interviews (~500,000
questions, 299MB SQLite file). Everything below is what is left to do, with the
threshold that should trigger it.

## Where we are

| Path | DB | End to end |
|---|---|---|
| Default list | 0.01 ms | 14 ms |
| Position filter | 0.01 ms | 2 ms |
| Reviewed filter | 0.01 ms | 10 ms |
| Date range | 0.01 ms | 10 ms |
| Deep page (OFFSET 99990) | 1.14 ms | 10 ms |
| Detail by id | <1 ms | <10 ms |
| `count(*)` for `total` | 0.4 ms | n/a |
| **`min_score` ≥95** | **35 ms** | n/a |
| **Search, no match** | **76 ms** | **114 ms** |

100k is comfortable. The two bold rows are the open items.

## Open items

### 1. Move to Postgres, the only one that blocks growth

Do this as soon as there is more than one concurrent writer, or on any real
deployment.

SQLite takes a database-wide lock on every write. One `PATCH` blocks every other
write, and read performance is irrelevant to that. This is the first hard wall,
and it arrives long before any query gets slow.

The change itself is small: point `database_url` in `config.py` at Postgres. The
ORM already runs real queries, so nothing else moves. Re-measure afterwards,
because Postgres plans differently and the index choices below should be
re-confirmed rather than assumed. This is the highest priority item here, and
not because of speed.

### 2. Full-text search

Revisit past roughly 500k rows, or if search stops being debounced.

`LIKE '%term%'` cannot use an index, by definition. A term that matches nothing
scans every row: 76ms at 100k, growing linearly. A term that matches early exits
fast, so this is a worst case rather than a typical one.

Fixing it means SQLite FTS5, or Postgres `pg_trgm` and `tsvector` once item 1 is
done. Either is a real feature with its own index to maintain, not a tweak, and
at 114ms end to end behind a 300ms debounce the cost does not yet buy anything.

### 3. `min_score` with a rare threshold

Revisit only if high thresholds become a common query.

`min_score=99` matches 17 rows out of 100k and costs 35ms. A range predicate
(`>=`) cannot use the sort columns of a composite index, so the planner scans
the date index until the LIMIT fills, which is nearly the whole table when
matches are rare. Common thresholds are unaffected: `>=90` is 0.35ms.

A composite `(overall_score, interview_date, id)` was tested and did not help,
for the reason above. A real fix means a different query shape, probably sorting
by score when a score filter is active. Since this only bites above about 95 and
the UI has no reason to send that, it stays on the list rather than in the code.

## Explicitly not planned

Each of these looks like an optimisation and is not:

- **Keyset pagination.** Was the plan until the covering index dropped deep
  paging to 1ms. Keyset also breaks "jump to page N", so the trade is now a
  loss.
- **Caching `count(*)`.** 0.4ms at 100k. Caching would add invalidation for
  nothing.
- **An index on `reviewed`.** Tested and removed: a boolean splits the table in
  half, so scanning the date index and filtering (0.01ms) beats seeking and
  sorting (4.7ms).
- **A composite index for `overall_score`.** See item 3.
- **Virtualising the table.** Server-side pagination already caps the DOM at
  `per_page` rows.
- **Splitting the detail query.** `selectinload` already avoids an N+1: two
  queries regardless of question count.

## Constraints to preserve

The current speed rests on two composite indexes in `db.py`:

```python
Index("ix_interviews_date_id", interview_date.desc(), id)
Index("ix_interviews_position_date", position, interview_date.desc(), id)
```

They cover both the filter and the `ORDER BY interview_date DESC, id` that every
list query ends with. An index on the filter column alone makes the planner sort
every matching row in a temp B-tree first.

Three rules follow, and `TestIndexes` in `tests/test_interviews.py` enforces the
first two by asserting query plans:

1. **Never wrap a filter column in a function.** `lower(position)` makes the
   index unusable. The router resolves casing against the known position list
   instead, so the query compares the column directly.
2. **Do not change the list's sort order** without changing these indexes.
3. **Do not add single-column indexes** for `position` or `interview_date`. A
   composite already serves lookups on its leading column.

Plan assertions are the right seam: a timing assertion would be flaky on shared
CI, and these indexes are invisible to behavioural tests. Dropping one changes
nothing a functional test can see, only the speed.

## What this benchmark does not cover

Single process, single user, local SQLite, warm cache. It measures query and
serialisation cost only. Concurrency, network latency and lock contention are
all absent, which is precisely why item 1 is first despite every read being
fast.
