# Submission Ordering Audit

Phase C, 2026-11-07. Inputs: 16 completed rounds (periods 229–244, rounds 53–68), **2,474 rows**, sanitized with `user_hash` only.

## 1. The 13 observed inversions

The Phase B 7-round dataset contained exactly **13** adjacent pairs where the next displayed row has a **newer** timestamp than the current row:

| Round | seq → seq | Timestamps | Delta |
|---|---|---|---|
| 53 | 135 → 136 | 19:01:39 → 19:01:40 | +1 s |
| 53 | 151 → 152 | 19:01:19 → 19:01:20 | +1 s |
| 54 | 133 → 134 | 19:16:39 → 19:16:40 | +1 s |
| 54 | 146 → 147 | 19:16:19 → 19:16:20 | +1 s |
| 55 | 127 → 128 | 19:31:39 → 19:31:40 | +1 s |
| 55 | 141 → 142 | 19:31:19 → 19:31:20 | +1 s |
| 56 | 114 → 115 | 19:46:42 → 19:46:43 | +1 s |
| 56 | 126 → 127 | 19:46:39 → 19:46:40 | +1 s |
| 56 | 136 → 137 | 19:46:19 → 19:46:20 | +1 s |
| 56 | 139 → 140 | 19:46:19 → 19:46:20 | +1 s |
| 57 | 125 → 126 | 20:01:39 → 20:01:40 | +1 s |
| 59 | 144 → 145 | 20:31:39 → 20:31:40 | +1 s |
| 59 | 162 → 163 | 20:31:19 → 20:31:20 | +1 s |

**The 13 count is VERIFIED** for the 7-round Phase B dataset.

### Additional rounds

Adding rounds 60–68 (periods 236–244) adds 5 more inversions:

| Round | seq → seq | Timestamps | Delta |
|---|---|---|---|
| 60 | 109 → 110 | 20:46:39 → 20:46:40 | +1 s |
| 60 | 126 → 127 | 20:46:19 → 20:46:20 | +1 s |
| 61 | 135 → 136 | 21:01:39 → 21:01:40 | +1 s |
| 61 | 152 → 153 | 21:01:19 → 21:01:20 | +1 s |
| 65 | 134 → 135 | 22:01:39 → 22:01:40 | +1 s |

Total across 16 rounds: **18 inversions**, all exactly **+1 second**. Rate: 18 / 2,458 adjacent pairs = **0.73%**.

## 2. What the inversions have in common

- Every inversion is a **one-second** increase; there are no inversions of 2+ seconds.
- The timestamps cluster at the **19→20** and **39→40** second boundaries, with one **42→43** case (round 56).
- The two rows in every inversion have **different masked hashes** and **different numbers**.
- Therefore the inversion is **not** explained by a user tie or a numeric tie.

This is consistent with a server-side order key that is **highly correlated with `created_at` but not identical to it** — for example an internal insertion ID, a batch/commit sequence, or a timestamp assigned at a different stage. The exact key is not exposed.

## 3. Is the order consistent with any observable field?

| Candidate order key | Evidence | Verdict |
|---|---|---|
| `created_at` descending | 18 one-second inversions out of 2,458 pairs | **Almost**, but not strictly |
| Numeric value ascending/descending within a second | 164 same-timestamp groups: 28 ascending, 28 descending, **108 neither** | **Rejected** |
| Masked user / hash | Inversion pairs have different hashes | **Rejected** |
| Row number / seq | Sequence is contiguous and stable; inversions are between adjacent seq values | Trivially true, not explanatory |
| Internal ID or batch sequence | Not exposed | **UNKNOWN** |

The public order is deterministic and stable across repeated fetches, but the tie-break key cannot be established from public data.

## 4. Pagination consistency

Phase B checks:

- Two fetches of page 1 returned the identical 50-row sequence.
- Page 1 ends at seq 50; page 2 starts at seq 51; no gap or overlap.
- The JSON `limit=200&offset=0` first 20 rows match the HTML page 1 first 20 rows.
- Sequence numbers are contiguous.

This means the ordering is not random per request; it is a stable server-side order.

## 5. Row 16 and the +119-second group

Across all **16** rounds:

```
row16 offset = +119 s in 16/16 rounds
```

| Round | n | +119 rows | Row 16 offset |
|---|---:|---:|---:|
| 53 | 173 | 47 | +119 s |
| 54 | 164 | 48 | +119 s |
| 55 | 151 | 51 | +119 s |
| 56 | 146 | 42 | +119 s |
| 57 | 145 | 38 | +119 s |
| 58 | 150 | 49 | +119 s |
| 59 | 168 | 65 | +119 s |
| 60 | 141 | 39 | +119 s |
| 61 | 169 | 50 | +119 s |
| 62 | 171 | 54 | +119 s |
| 63 | 156 | 42 | +119 s |
| 64 | 177 | 54 | +119 s |
| 65 | 148 | 52 | +119 s |
| 66 | 140 | 40 | +119 s |
| 67 | 132 | 34 | +119 s |
| 68 | 143 | 44 | +119 s |

If row 16 were a random position within the round, the probability of landing in the +119 group in all 16 rounds is approximately:

```
∏ (b119 / n) ≈ 4.3 × 10^-9
```

So this is not a coincidence. The 16th displayed row is systematically chosen from the **final-second batch**.

## 6. Why this matters

- The “16th number” is not known until the final second of the shooting window.
- It is not the 16th chronological submission; it is the 16th row of the newest-first table.
- Because row 16 is always in the +119s group, any pre-cutoff computation is impossible: at betting close the pool has only 0–5 rows (Phase B), and row 16 does not exist.

## 7. What cannot be established

- The internal sort/tie-break field.
- Why the 19→20 and 39→40 boundaries produce one-second inversions.
- Whether the inversions are caused by batch commit order, clock granularity, or a secondary key.
- Whether the same pattern holds on a different day (historical access is blocked; see `HISTORICAL_AVAILABILITY.md`).

## 8. Verdict

| Claim | Verdict |
|---|---|
| 13 inversions in the 7-round dataset | **VERIFIED** |
| 18 inversions in 16 rounds | **OBSERVED** |
| All inversions are +1 s | **OBSERVED** |
| Order is strictly timestamp-descending | **REJECTED** |
| Order is numeric within ties | **REJECTED** |
| Row 16 is in the +119 s group | **OBSERVED 16/16** |
| Internal sort key | **UNKNOWN** |
| Pattern persists across days | **UNTESTABLE** (no historical archive) |
