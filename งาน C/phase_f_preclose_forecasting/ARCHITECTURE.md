# Phase F architecture

```
pf.py
 ├─ pfconfig      validated settings; loads Phase D's config through Phase D's own validator
 ├─ pfsession
 │   ├─ read_identity      read-only lookup of Phase D's period/source/close evidence
 │   ├─ acquire_lock       flock on phase_d/worker.lock with a deadline
 │   ├─ budget_headroom    reads phase_d/research.sqlite3 `requests` ledger
 │   ├─ fetch_page         page.goto with UTC + monotonic bounds, Phase D's guards
 │   ├─ parse_observation  Phase D parser, plus the pre-close shell (escaped betconfig)
 │   └─ capture            atomic snapshot + page intervals + rows + first_seen
 ├─ pfstore        SQLite WAL; append-only forecast ledger (UPDATE/DELETE triggers)
 ├─ pfaudit        recomputes ordering, pagination, first-seen and reorder invariants
 └─ models / scoring / walkforward   retrospective A/B/C and proper scoring
```

## Concurrency contract

Phase D runs `cli.py collect --once` every 15 seconds. That process takes
`phase_d/worker.lock` (flock, non-blocking) and launches Chromium on
`phase_d/browser_profile`. Phase F takes the **same** lock with a deadline before
opening the same profile, so the two can never hold Chromium simultaneously.

Phase F never holds the lock while sleeping between horizons: it locks, reads,
releases. If Phase D is mid-collection, Phase F waits (default 25 s) and records
`LOCK_TIMEOUT` rather than forcing the profile.

## Budget contract

Every document read goes through Phase D's `Browser`, whose route handler calls
Phase D's `Store.reserve()`; that is the same `requests` table Phase D counts.
Before each page read, Phase F checks `used + 1 <= hourly_budget - 4`, so it can
never consume the last four requests of the hour. A rejected read is recorded as
`BUDGET` and does not create a partial snapshot silently.

## Observation contract

A snapshot is valid when the page identity matches Phase D's saved identity
(period, round, close time) and every page read has both clock readings. Two page
states are recorded:

| `page_state` | Meaning | Rows |
|---|---|---|
| `PUBLISHED` | Result published; full list present | all pages |
| `PRE_CLOSE_SHELL` | Round page reachable, list absent | 0 |
| `ROWS_VISIBLE` | List present, result not yet published | all pages |

`PRE_CLOSE_SHELL` is a real observation, not an error: it proves the round page
was reachable and nothing was visible at that instant.

## First-seen contract

`first_seen` is written only inside `capture()`, using the `response_received_utc`
of the page that contained the row. `displayed_created_at` is stored separately
in `snapshot_rows` and never copied into `first_seen`. The audit fails a row whose
`first_seen` predates its snapshot start or reaches the close, and fails any
snapshot whose claimed first sighting is not the earliest snapshot containing it.

## Order-change contract

Each snapshot stores `order_hash = sha256(seq:event_key ...)` sorted by the
observed sequence, plus `row16_seq_present`, `row16_number`, `row16_event_key`.
The next snapshot recomputes the move count against the previous one. A moved
event is the same submission in a new position, which is why row 16 must be
treated as latent when rows reorder. The audit recomputes both counters.

## Immutability contract

`forecasts` rejects UPDATE and DELETE with SQLite triggers. A forecast stores the
snapshot hash, model version, information set, training cutoff, generated time
(UTC + monotonic), distribution bytes (float32) and its hash, plus a checksum.
Re-fitting creates a new row; it never rewrites history.
