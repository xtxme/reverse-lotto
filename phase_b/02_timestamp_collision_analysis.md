# Investigation 2 — Why Do 49–51 Submissions Share the Same Second?

Phase B, 2026-11-07. Inputs: complete sanitized row lists for periods 229–235 (rounds 53–59), 1,097 rows.

## 1. Audit of the Phase A numbers

Phase A reported for round 55:

- 51 submissions timestamped `19:31:59`,
- 49 submissions timestamped `19:31:43`.

Phase B re-fetched round 55 from the public round page and recomputed the per-second counts:

| Timestamp | Count | Offset from 19:30 close |
|---|---:|---:|
| 19:31:59 | 51 | +119 s |
| 19:31:43 | 49 | +103 s |
| 19:31:44 | 10 | +104 s |
| 19:31:42 | 8 | +102 s |
| 19:31:20 | 6 | +80 s |

**Both Phase A numbers are VERIFIED exactly.** The 19:31:59 group has 51 rows and the 19:31:43 group has 49 rows.

## 2. Timestamp precision

OBSERVED:

- Displayed and API timestamps have **one-second precision**: `YYYY-MM-DD HH:mm:ss`.
- **No milliseconds** are exposed anywhere in the normal member UI or JSON.
- The timestamp is server-side, Bangkok local time, without a timezone suffix in the string.
- The page does not sort by a displayed millisecond field; ties are resolved server-side.

Consequence: two submissions in the same second are indistinguishable by timestamp alone. The internal order within a tied second can only be inferred from row sequence, not from the timestamp.

## 3. Collision statistics per round

Definitions:

- **Tied timestamp:** a timestamp shared by ≥2 rows.
- **Rows in ties:** all rows whose timestamp is shared.
- **Collision pairs:** for a timestamp with `k` rows, `k(k−1)/2` unordered pairs.
- **Distinct seconds:** number of unique timestamps in the round.

| Round | n | Distinct seconds | Max rows/second | Timestamp of max | Tied timestamps | Rows in ties | Collision pairs |
|---|---:|---:|---:|---|---:|---:|---:|
| 53 | 173 | 44 | 51 | 19:01:43 | 12 | 141 | 2,468 |
| 54 | 164 | 36 | 49 | 19:16:43 | 10 | 138 | 2,457 |
| 55 | 151 | 23 | 51 | 19:31:59 | 11 | 139 | 2,552 |
| 56 | 146 | 27 | 53 | 19:46:43 | 9 | 128 | 2,341 |
| 57 | 145 | 23 | 49 | 20:01:43 | 11 | 133 | 2,055 |
| 58 | 150 | 21 | 50 | 20:16:43 | 11 | 140 | 2,519 |
| 59 | 168 | 23 | 65 | 20:31:59 | 10 | 155 | 3,444 |

Full per-timestamp list: `phase_b/timestamp_collisions.csv`.

## 4. The two fixed bursts

Every round has the same two dominant offsets from its betting close:

| Round | Burst 1 time | n | Offset | Burst 2 time | n | Offset |
|---|---|---:|---:|---|---:|---:|
| 53 | 19:01:43 | 51 | +103 s | 19:01:59 | 47 | +119 s |
| 54 | 19:16:43 | 49 | +103 s | 19:16:59 | 48 | +119 s |
| 55 | 19:31:43 | 49 | +103 s | 19:31:59 | 51 | +119 s |
| 56 | 19:46:43 | 53 | +103 s | 19:46:59 | 42 | +119 s |
| 57 | 20:01:43 | 49 | +103 s | 20:01:59 | 38 | +119 s |
| 58 | 20:16:43 | 50 | +103 s | 20:16:59 | 49 | +119 s |
| 59 | 20:31:43 | 51 | +103 s | 20:31:59 | 65 | +119 s |

The two seconds together contain **692 of 1,097 rows = 63.08%** of all submissions. The final 20 seconds (100–120 s) contain 84.14%. This is not a smooth arrival process.

Chart: `phase_b/charts/timestamp_burst_analysis.png`.

## 5. Composition of the bursts

For the largest burst in each round:

| Round | Rows | Distinct masked users | Unique numbers | Max rows per user |
|---|---:|---:|---:|---:|
| 53 | 51 | 51 | 51 | 1 |
| 54 | 49 | 49 | 49 | 1 |
| 55 | 51 | 51 | 51 | 1 |
| 56 | 53 | 53 | 53 | 1 |
| 57 | 49 | 49 | 49 | 1 |
| 58 | 50 | 50 | 50 | 1 |
| 59 | 65 | 64 | 64 | 2 |

The bursts are **multi-user and multi-number**:

- Each row in the top burst has a different masked username (except round 59, one user has 2 rows).
- Almost every row has a different 5-digit number.
- The +103 and +119 bursts share some users (intersection 12–41; Jaccard 0.16–0.55), so a subset of users appear in both bursts. This is consistent with users submitting multiple numbers in the same round, not with a single client owning all rows.

This directly contradicts a naive “one bot submitted 51 numbers” explanation.

## 6. Ordering stability

Repeated observations of round 55 page 1:

- Two independent fetches returned the **identical 50-row sequence**.
- Page 1 ends at sequence 50; page 2 starts at sequence 51 with no gap or overlap.
- The JSON endpoint with `limit=200&offset=0` returned the first 20 rows in the **same order** as page 1.
- The row sequence is contiguous: 1..50, 51..100, etc.

OBSERVED:

- The public order is deterministic and stable across repeated requests.
- Pagination preserves order.
- The API’s first page is the same view as the HTML table.

INFERRED:

- The server sorts by a stable key, most likely `created_at DESC` plus an internal tie-break (ID or insertion order).
- The exact intra-second tie-break is **UNKNOWN** because no submission ID is exposed.

## 7. Are collisions caused by duplicate numbers?

No.

- There are 44 duplicate-number groups (96 rows) across the seven rounds.
- **0 of 44 groups** have all copies in the same second.
- Only **2 of 61** colliding pairs share a timestamp; 59 pairs are in different seconds.
- Duplicate groups are mostly one user repeating the same number (see Investigation 3): 37 pairs, 6 triples, 1 quadruple.
- The largest bursts contain almost entirely unique numbers (unique = rows in six of seven rounds).

So timestamp collisions and duplicate values are **different phenomena**:

- collisions = many users’ rows sharing a second,
- duplicates = the same user submitting the same number at different times.

## 8. Statistical models

### Model A — uniform independent arrivals over the 120-second shoot window

If 151 arrivals were uniform over 120 seconds, the mean per second is 1.26 and the maximum of 120 Poisson(1.26) bins is typically 5–6. The observed max is 51. The probability of ≥49 in one specified second is astronomical. This model is decisively rejected.

### Model B — smooth non-uniform arrival (e.g. beta-shaped deadline rush)

A smooth deadline rush can produce a rising tail, but not two isolated one-second spikes containing 63% of all rows. The observed distribution is a mixture of a smooth background and two point masses at +103 and +119. A smooth model cannot reproduce the exact offsets in 7/7 rounds.

### Model C — two-point mass plus background

A descriptive model with point masses at +103 s and +119 s plus a small background fits the data. But a descriptive fit does not identify the cause: the point masses could be produced by a server-side batch flush or by synchronized external clients.

### Model D — one automated client

Rejected for the top bursts: distinct users and unique numbers per row. It could still explain a subset of duplicate-number behavior (one user repeating a number), but not the 49–65-row bursts.

## 9. What can and cannot be concluded

OBSERVED:

- Two fixed offsets (+103 s, +119 s) dominate every round.
- The bursts are multi-user and multi-number.
- Duplicates are same-user repeats at different times.
- Ordering is stable and paginated consistently.

HYPOTHESIS (not proven):

- **H1 — server-side batch/queue timestamp assignment.** Many queued submissions are committed at fixed processing ticks; `created_at` is the commit time, not the user action time.
- **H2 — synchronized multi-account automation.** Many accounts use the same script and submit at fixed offsets.
- **H3 — deadline rush plus server load.** Users all rush at the end; the server processes them in two large commits, producing the same offsets.

The evidence cannot distinguish H1–H3. In particular, a timestamp collision does **not** prove automation, and a multi-user burst does **not** prove human behavior.

## 10. Evidence that would distinguish the hypotheses

- Server request-arrival logs vs database commit times (the decisive test).
- Queue/worker metrics or transaction logs.
- Per-row IP/device/session identifiers (not available and not appropriate to collect here).
- Whether the same account appears in both +103 and +119 bursts across many rounds.
- Whether the +103/+119 offsets shift with server clock or load.
- Whether a round with unusually low volume still shows both spikes.

## 11. Verdict

| Claim | Verdict |
|---|---|
| Phase A 51@19:31:59 and 49@19:31:43 | **VERIFIED exactly** |
| Timestamps have second precision, no ms | **VERIFIED** |
| Same-second rows have a stable display order | **VERIFIED** (stable across fetches; tie-break key unknown) |
| Bursts are one automated client | **REJECTED** for the top bursts (distinct users/numbers) |
| Bursts are many users | **OBSERVED** |
| Bursts are caused by batch timestamp assignment | **HYPOTHESIS** |
| Bursts are caused by synchronized automation | **HYPOTHESIS** |
| Duplicates cause the collisions | **REJECTED** |
