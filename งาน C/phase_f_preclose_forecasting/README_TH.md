# Phase F — Pre-close forecasting (snapshot + ledger)

Phase F is a **separate** module. It never modifies Phase D's collector, database,
sheet delivery, browser profile, or keys. It reads Phase D's state read-only and
writes only to `~/Library/Application Support/ThlottoResearch/phase_f/`.

## Why this exists

The Deep Research report (13 Nov 2026) says a pre-close claim is only valid if
submissions are observed **before** `betting_close_at`, with `first_seen` recorded
prospectively. Historical rows cannot be backfilled from `displayed_created_at`.
Phase F implements that observation system and freezes predictions in an
append-only ledger before the cutoff.

## What is shared with Phase D (deliberately)

| Resource | How it is shared |
|---|---|
| Browser profile | `phase_d/browser_profile` (single profile, never two browsers) |
| Session lock | `phase_d/worker.lock` acquired with a deadline before every snapshot |
| Request budget | The same `requests` ledger; Phase F never takes the last 4 requests of the hour |
| HMAC key | `phase_d/hmac.key`, so display pseudonyms match Phase D exactly |
| Selectors | Loaded from Phase D's validated config, never duplicated |

Because both processes share one SQLite WAL ledger, Phase D's own budget check
counts Phase F requests automatically.

## Visibility finding (Stage-1 gate)

Live evidence collected on 2026-11-13:

| Observation | Rows in SSR |
|---|---|
| Round 66 at T−5 min (22:10, close 22:15) | 0 |
| Round 66 at T+36 s (22:15:36) | 0 |
| Round 67 at T−13 min (with and without `?page=1`) | 0 |
| Round 68 at T−25 min (smoke) | 0 |
| Round 65 (published) | 50 on page 1, 3 page links |

The pre-close page is a valid round shell (identity, title, close time, escaped
`betconfig`) but contains **no submission list**. The list appears only when the
round is published, which Phase D collects at `submission_close + 10 s`.
Conclusion: true pre-close first-seen from this route is **not observable**, so
Phase F must not report pre-close performance. The snapshot system records this
as `PRE_CLOSE_SHELL` with zero rows instead of failing, and the audit quantifies
it.

## Commands

```sh
cd '/Users/icy/reverse-lotto/งาน A/phase_f_preclose_forecasting'
CFG='/Users/icy/Library/Application Support/ThlottoResearch/phase_f/config.yaml'
.venv/bin/python pf.py --config "$CFG" init
.venv/bin/python pf.py --config "$CFG" status
.venv/bin/python pf.py --config "$CFG" schedule --round 68
.venv/bin/python pf.py --config "$CFG" session  --round 68                  # dry-run plan
.venv/bin/python pf.py --config "$CFG" smoke    --round 65 --live --authorized
.venv/bin/python pf.py --config "$CFG" session  --round 68 --live --authorized
.venv/bin/python pf.py --config "$CFG" audit    --round 68
.venv/bin/python pf.py --config "$CFG" test --offline
```

## Data model

* `snapshots` — one row per (day, round, horizon): UTC start/finish, monotonic
  start/finish, lock wait, status, pagination bounds, row count, row-16 fields,
  order hash, reorder counters, clock offset, page state.
* `page_reads` — per document: request/response UTC **and** monotonic bounds.
* `snapshot_rows` / `event_sequence` — rows as seen and the sequence at that sighting.
* `first_seen` — insert-only; written from the response time that first showed the
  row, never from `displayed_created_at`.
* `forecasts` — append-only ledger with model version, information set, training
  cutoff, snapshot hash, distribution bytes + hash, checksum; SQLite triggers
  reject UPDATE and DELETE.
* `audit_runs` — every audit verdict and its failing checks.

## Audit checks (all recomputed, not trusted)

`has_snapshots`, `clock_ordering`, `clock_agreement`, `pre_close_bound`,
`first_seen_prospective`, `first_seen_is_earliest`, `first_seen_not_displayed_time`,
`pagination_bounds`, `row_integrity`, `order_reproducible`, `reorder_recomputable`.

Any FAIL blocks pre-close use of the snapshot.

## Budget policy

A snapshot is allowed only while `used + 1 <= hourly_budget - 4`; the check runs
before every page read, so a long pagination run cannot starve Phase D's round
collection. `--live` also requires `automated_access_permitted: true` in Phase F's
private config plus `--authorized`.
