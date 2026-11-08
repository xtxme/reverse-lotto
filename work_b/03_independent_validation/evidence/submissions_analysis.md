# Number Submission ("ยิงเลข") Analysis

Observed on 2026-11-07 with an authorized account. No submissions were made by the researcher; all data comes from pages the site renders normally and from GET endpoints the page itself calls.

## 1. UI and input contract

The round detail page exposes three tabs:

- **ระบุเลข** — enter numbers manually for betting.
- **เลือกเลข** — pick numbers from a grid.
- **ยิงเลข** — submit a 5-digit number into the round pool.

The “ยิงเลข” tab contains:

- A text input with `name="ykn"`, `type="tel"`, `maxlength="5"`, placeholder `กรอกเลข 5 หลัก`.
- Client validation rules `required|numeric|digits:5` (VeeValidate).
- A “สุ่มเลข” (random number) button that animates 5 digits generated with `Math.random()`.
- A “เพิ่มเลข” (add) button.
- A live “ผลรวม” (total) counter.
- A “เหลือเวลายิงเลข” countdown.

Classification: OBSERVED.

## 2. Submission economics

The published rules state number submission is free and unlimited. No price, stake, or credit deduction is associated with the “ยิงเลข” action in the UI. Betting and number submission are separate actions.

Classification: OBSERVED in the UI and rules text.

## 3. What is publicly visible

The round detail page lists submissions with:

- a row number (sequence),
- the 5-digit number,
- a partially masked username (e.g. `Ab***cd`),
- a `DD/MM/BBBB HH:mm:ss` timestamp.

The list is paginated server-side at 50 rows per page. All rows for a published round are accessible through `?page=N`.

The JSON list endpoint returns at most 20 items regardless of the requested `limit=19`/`offset=0` pattern, with fields:

```
username (masked), number (5 digits, string or int), bet_category_id,
bet_period_id, created_at
```

and a top-level `sum` string.

No email, real name, balance, bet amount, IP address, or other member-private field was exposed in these responses.

Classification: OBSERVED.

## 4. Ordering — the “16th” row

The row list is **newest-first**:

- Round 55: rows 1–51 have `created_at = 19:31:59`; rows 52–100 have `19:31:43`; …; the last row (151) has `19:27:53` (the earliest submission).
- Round 54: row 1 = `19:16:59`; last row = `19:13:35`.
- Round 53: row 1 = `19:01:59`; last row = `18:58:55`.

Therefore “เลขลำดับที่ 16” (the 16th number) is the **16th row in the newest-first display**, not the 16th submission chronologically. In all three observed rounds, row 16 fell inside the final-second batch.

Tie-break order within the same `created_at` second is UNKNOWN; the API does not expose a submission ID, and the displayed order within a second is not distinguishable from timestamp data alone.

Classification: OBSERVED for the newest-first order and for row 16 = display row 16; UNKNOWN for the intra-second tie-break.

## 5. Timing of the pool

The pool is not static for 15 minutes. It opens shortly before betting closes and stays open for two minutes after:

| Round | Close | Earliest submission | Latest submission | Pool size |
|---|---|---|---|---|
| 53 | 19:00:00 | 18:58:55 (≈ −65 s) | 19:01:59 (≈ +119 s) | 173 |
| 54 | 19:15:00 | 19:13:35 (≈ −85 s) | 19:16:59 (≈ +119 s) | 164 |
| 55 | 19:30:00 | 19:27:53 (≈ −127 s) | 19:31:59 (≈ +119 s) | 151 |

The earliest submissions cluster around `close − 2 minutes`, and the last submissions cluster at `close + 2 minutes − 1 second`. The server’s `closeDateYeekee` field is exactly `close_date + 2 minutes`.

Interpretation: the acceptance window appears to be approximately `[close − 2 min, close + 2 min]`, not the “after close, for 2 minutes” wording in the rules. The end boundary matches the rules and the client code; the start boundary is earlier than the prose suggests.

Classification: OBSERVED for the timestamps; INFERRED for the window rule; UNKNOWN for the exact server-side open trigger.

## 6. Submission volume and burstiness

- Pool sizes observed: 151–173 submissions per round.
- Submissions are highly bursty: round 55 had 51 submissions in the single second `19:31:59`, 49 at `19:31:43`, and only 5 submissions before the 19:30 close (7 before 19:31).
- Round 53 had 173 submissions compressed into only 44 distinct seconds; the final second (19:01:59) contained the largest cluster (at least 20 rows, the maximum returned by the API view).
- The same second can contain dozens of submissions, so a single member or automated client can plausibly submit many numbers.

Classification: OBSERVED for counts and timestamps; INFERRED for automation (not proven).

## 7. Duplicate numbers and non-uniformity

Duplicates are far more common than chance under uniform 5-digit draws:

| Round | n | unique | duplicate excess | expected excess under uniform |
|---|---|---|---|---|
| 53 (229) | 173 | 164 | 9 | ≈0.15 |
| 54 (230) | 164 | 151 | 13 | ≈0.13 |

Most frequent values:

- Round 53: `37553` ×3, `55014` ×3, plus 5 numbers ×2.
- Round 54: `37553` ×4, `55555` ×3, `55014` ×3, plus 6 numbers ×2.

The same “favorite” numbers (`37553`, `55014`, `55555`, `62839`, `11323`) recur across rounds. This indicates a non-uniform submission process (habitual members, fixed number sets, or automated shooting), not a uniform random pool.

Classification: OBSERVED for the duplicate statistics; INFERRED for the behavioral explanation.

## 8. Sequence-dependent bonuses

The rules grant credit to the members at display positions 1, 16, and 100:

- position 1: 100 credit,
- position 16: 200 credit,
- position 100: 100 credit,
- requires ≥100 THB of bets in that round; one bonus per account per day.

The round page displays the masked usernames of the position-1, position-16, and position-100 members after publication.

Note: because the list is newest-first, “position 1” is the most recent submission, not the earliest. Whether this is intentional is UNKNOWN, but it is what the site displays and rewards.

Classification: OBSERVED for the displayed winners and positions; INFERRED that position 1 = newest submission.

## 9. What changes at close

| Phase | Pool visible | Sum visible | 16th row visible | Result visible |
|---|---|---|---|---|
| During betting (before close−2 min) | no (empty) | no (0) | no | no |
| Last ~2 min before close | yes, partial | yes, partial | yes, current row 16 | no |
| Close → close+2 min (shoot window) | yes, growing | yes, growing | yes, may change | no |
| After close+2 min | yes, final | yes, final | yes, final | yes, within seconds |

This table is the core of the predictability question: the result-determining inputs are not final until `close + 2 minutes`, i.e. after betting has closed.

Classification: OBSERVED.

## 10. Validation and abuse controls

- Client-side validation is present (`digits:5`, numeric, required).
- Whether the server independently enforces the same rules is INFERRED but not directly tested (no invalid submissions were sent).
- Rate limiting, CAPTCHA, device fingerprinting, or duplicate-submission limits were not observed in the delivered UI.
- The site enforces a single active login session; repeated logins invalidated the research session (observed repeatedly). This is a session-control measure, not a submission control.

Classification: OBSERVED for client validation and single-session behavior; UNKNOWN for server-side anti-abuse controls (not tested).

