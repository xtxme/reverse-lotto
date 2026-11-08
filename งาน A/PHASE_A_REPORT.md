# THLotto Yeekee — Phase A Research

Authorized, evidence-based reverse engineering of `https://thlotto.com/member/lottery/yeekee`.

**Status: Phase A complete.** No replica application, LINE dataset analysis, or betting automation was performed.

## What this is

A passive/observational study of the publicly delivered and authorized member-facing website, with three goals:

1. document the frontend, round system, submission flow, and APIs;
2. establish what can be verified about the result calculation;
3. determine whether public data supports any reproducible prediction of future results.

The headline result: **the published calculation rule was found and verified exactly on three live rounds**, and **no credible predictive advantage exists before a round’s inputs are final**.

## Directory

```
research/
├── README.md                      ← this file + final 14-question report
├── site_evidence.md               ← environment, timeline, evidence IDs
├── frontend_architecture.md       ← stack, rendering, countdown, storage
├── round_schedule.md              ← 88-round schedule and state machine
├── submissions_analysis.md        ← input rules, pool, ordering, timing
├── network_api_observations.md    ← endpoints, schemas, caching, WebSocket
├── client_exposure_review.md      ← passive exposure findings
├── result_algorithm_research.md   ← published rule + independent verification
├── timing_analysis.md             ← clock, close, publication measurements
├── predictive_feasibility.md      ← statistical and structural assessment
├── unknowns_and_limitations.md    ← what cannot be known and why
├── findings_register.md           ← every finding with the 8 required fields
└── evidence/
    ├── sanitized_observations/    ← CSV/JSON/MD, no credentials
    ├── screenshots/               ← page and rules captures
    └── reproducible_tests/        ← Python verifier and statistics
```

## Reproduce the core result

```bash
cd research/evidence/reproducible_tests
python3 verify_formula.py      # exact match for rounds 53, 54
python3 randomness_tests.py    # preliminary statistical tests
```

`verify_formula.py` reconstructs each round from the complete public submission list and checks the sum, 16th row, raw result, top-3, and bottom-2 against the site’s displayed values.

## Key findings at a glance

| Area | Finding | Class |
|---|---|---|
| Stack | Server-rendered pages + jQuery/Bootstrap + Vue bundle (2.x-style) + Pusher; no SPA framework | OBSERVED (Vue version inferred) |
| Schedule | 88 rounds/day, 15 min apart, first close 06:00, last 03:45 next day | OBSERVED (52–88) / INFERRED (1–51) |
| Round state | Server-provided `close_date`; shoot close = close + 2 min; page auto-reloads at shoot close | OBSERVED |
| Submission | 5-digit, free/unlimited, public newest-first list with masked usernames | OBSERVED |
| Pool timing | Opens ~2 min before betting close, closes 2 min after; 151–173 submissions | OBSERVED |
| API | `yeekee-list-number` (lists + sum), `yeekee-chart`, server-rendered round pages | OBSERVED |
| Real-time | Pusher only for agent notifications, not rounds/results | OBSERVED |
| Formula | `R = Σx − x₁₆` where x₁₆ is **display row 16** (newest-first); last 5 digits → bottom2 (left 2), top3 (right 3) | OBSERVED + verified |
| Verification | 3/3 rounds, 488 submissions, exact sum/16th/result/prizes | OBSERVED |
| Prediction | No evidence; final inputs arrive after betting close; tests consistent with uniform | OBSERVED / statistical |
| Exposure | Public source maps, JWT without `exp`, cookies without `Secure`/`SameSite`, no CSP/HSTS | OBSERVED |

## Final research report — the 14 required questions

### 1. What frontend architecture could be verified?

A classic server-rendered application with a Vue island (2.x-style render functions) for interactive betting/number-shooting UI. Concretely: server-rendered HTML (88-card grid, round pages, results), jQuery 3.5.1, Bootstrap bundle, Laravel-Mix-style `manifest.js`/`vendor.js`/`main.js?v=7.5`, PNotify, Nanobar, Hotkeys, Pusher JS 7.0, and Cloudflare in front. No Next.js, Nuxt, React root, Angular, or client-side router was found. The result block is in server HTML, not computed in the browser.

### 2. How does the observable 88-round schedule work?

88 rounds per day, one every 15 minutes. Round 1 closes at 06:00; betting opens at 05:00; round 88 closes at 03:45 the next calendar day. Rounds 52–88 were directly observed on 2026-11-07 (18:45 → 03:45 next day), all exactly 15 minutes apart. Rounds 73–88 carry the next date (08/11/2569) while numbering continues. Each round has a server-provided `close_date` and a `closeDateYeekee = close_date + 2 min`. The countdown is seeded from server time. The grid shows the just-closed round at `00:00:00`, then future rounds with live countdowns.

### 3. What is known about the submission process?

Members submit a 5-digit number in the “ยิงเลข” tab (`name=ykn`, `type=tel`, `maxlength=5`, validation `required|numeric|digits:5`). Submission is free and unlimited. The pool is public with masked usernames, numbers, row numbers, and timestamps, paginated at 50 rows per page. The list is newest-first, so “row 16” is the 16th newest submission. Observed pools: 151–173 submissions. The acceptance window runs from roughly 2 minutes before betting close to 2 minutes after. Display positions 1, 16, and 100 earn small credits (with a ≥100 THB bet condition and one bonus per account per day). A round with fewer than 20 submissions is supposed to be refunded.

### 4. Which API behaviors were directly observed?

- `GET /member/lottery/yeekee-list-number?id={periodId}&limit=19&offset=0` → `{lists:[{username, number, bet_category_id, bet_period_id, created_at}], sum:"..."}`; max 20 rows, newest-first, dynamic, ETag present.
- `GET /member/lottery/yeekee-chart?id={periodId}&limit=19&offset=0` → `{lists:[...]}`; empty for an unprocessed round.
- Server-rendered `GET /member/lottery/yeekee` and `/member/lottery/yeekee/{periodId}?page=N`.
- Server-rendered `GET /member/lottery/result?date=DD/MM/BBBB`.
- No polling of round state. Only Cloudflare RUM recurs while idle.
- Pusher subscribes to `notic.agentid.33` / `numbersets`, unrelated to rounds.
- `POST /member/lottery/yeekee` is documented in the bundle but was deliberately not invoked.

### 5. What client-side calculation logic was actually found?

Only the countdown and UI conveniences. The countdown uses a server timestamp embedded at render time and computes an offset against `Date.now()`. The “สุ่มเลข” button generates 5 digits with `Math.random()` for input convenience. No function computes the sum, subtracts the 16th number, takes a modulo, or derives top/bottom prizes. `axios` is configured with `/api`, the CSRF token, and a bearer JWT; Pusher auth uses the same JWT.

### 6. What backend behavior can be reasonably inferred?

The server is the sole authority for round state, submissions, sums, and results. It renders all state into HTML, accepts/validates submissions, maintains the newest-first ordering, computes the result at/after shoot close, and publishes it within seconds. It enforces a single active session. The stack is likely Laravel/PHP behind Cloudflare, but the language/version is not proven.

### 7. What backend behavior remains unknown?

Database engine/schema/keys; exact ordering tie-break within a one-second batch; whether submissions are inserted live or batched; server-side validation and rate limits; the shooting-window open trigger; cancelled-round and <20-submission handling; negative/underflow handling; whether the result is computed by a job or on demand; any hidden administrative adjustment. Older periods are not reachable, so archival behavior is also unknown.

### 8. Were any potential client-side information exposures observed?

Yes, but none grant prediction or private data:

- production `.map` files are served (no original sources or secrets inside),
- the page embeds a JWT with no `exp` claim (HS256, `uid` + `iat` only),
- session cookies are `HttpOnly` but lack `Secure` and `SameSite`, with ~30-day expiry,
- no CSP, HSTS, Referrer-Policy, or Permissions-Policy,
- `/api` and `/pusher/auth` are referenced in the bundle,
- masked usernames and full submission numbers are intentionally public.

No credentials, DB strings, admin interfaces, or private member records were exposed.

### 9. What published result calculation rules were found?

The site’s rules modal states: sum all 5-digit numbers submitted in the round, subtract the number in 16th position, and use the difference. The worked example is `2,543,565 − 34,529 = 2,509,036`, with top 3 = `036` and bottom 2 = `09`. Operationally, take the last five digits of the difference: the leftmost two are the bottom prize, the rightmost three are the top prize.

### 10. Can those rules reproduce independently verifiable examples?

Yes, exactly. Using the complete public lists:

| Round | n | Σ | 16th | Result | top3 | bottom2 |
|---|---|---|---|---|---|---|
| 53 | 173 | 9,281,577 | 80,308 | 9,201,269 | 269 | 01 |
| 54 | 164 | 7,724,164 | 62,839 | 7,661,325 | 325 | 61 |
| 55 | 151 | 7,422,657 | 58,470 | 7,364,187 | 187 | 64 |

All match the site’s displayed values. `verify_formula.py` reproduces rounds 53 and 54 from CSV; round 55 was reconstructed from all 151 rows.

### 11. Which result inputs are available before a round closes?

Only a partial pool and partial running sum, available from roughly 2 minutes before betting close, plus the current row 16. They are not final: the pool grows until 2 minutes after close, and the majority of submissions arrive after betting closes (146/151 in round 55). Row 16 can change with each new submission.

### 12. Is there credible evidence that future results can be predicted using only authorized public data?

No. The result is deterministic only once the final pool exists, and the final pool is fixed after betting closes. Statistical tests on 53 results show no dependence (last-digit χ² p = 0.50; runs p = 0.68; lag-1 r = −0.12 within ±0.27; hot-digit out-of-sample p = 0.41). A Monte Carlo using the real non-uniform submission pool still produced a near-uniform output. No model beat the uniform baseline.

### 13. What additional legitimately obtainable evidence would be required?

- A lawful archive of thousands of complete rounds (results plus full pools and timestamps).
- Operator documentation or an authorized audit for ordering, cancellation, refund, and negative-result edge cases.
- Authorized negative tests for betting/submission cut-off enforcement and server-side validation.
- Server logs/metrics to determine whether results are computed on demand or by a scheduled job.
- A responsible-disclosure response on the JWT/cookie/header issues.

### 14. Which findings are suitable for implementing an independent educational simulator in a later phase?

Suitable:

- the deterministic formula and digit extraction,
- the 88-round × 15-minute schedule and cross-midnight handling,
- the round state machine (open → closed → shoot → published),
- newest-first display ordering and the “row 16” concept,
- the masked-public submission model,
- the server-time countdown and reload behavior,
- the published rules and bonus positions.

Not suitable for a production replica without explicit authorization and compliance review:

- real-money betting, credit, or payout flows,
- automated number shooting,
- scraping at scale or bypassing rate limits,
- replicating the operator’s exact internal ordering when it is unknown (the simulator should label synthetic ordering).

## Limitations

- The site enforces a single active session; repeated invalidation interrupted long observations. Re-authentication was performed as instructed.
- Only 53 results were available in the reachable window; older period pages returned 404.
- No server code, database, or admin access was available or sought.
- The backend framework is inferred, not proven.
- All findings are a 2026-11-07 snapshot; the operator can change the rules or implementation.

## Ethical note

No authentication bypass, vulnerability exploitation, automated submissions, bets, or unauthorized data access occurred. Exposure findings are reported for responsible remediation and do not enable prediction or cheating. No betting recommendations are made.
