# Masked Account Pattern Audit

Phase C, 2026-11-07/08. Inputs: 16 completed rounds (periods 229–244, rounds 53–68), **2,474 sanitized rows**. Account identifiers are truncated SHA-256 hashes of the site-masked display name, prefixed `phase_c:`. **No raw masked username is stored or reported.**

## 1. Privacy and interpretation

- `user_hash` is a **display identifier**, not a verified natural person.
- The site already masks usernames (e.g. `Ab***cd`). Two different accounts can render the same mask; if so, they collapse to one hash.
- Therefore:
  - **469 distinct hashes** = 469 distinct masked display identifiers.
  - The true number of accounts is **≥469**, exact count UNKNOWN.
  - Two accounts sharing a mask cannot be distinguished.
  - No attempt was made to reverse, de-anonymize, or identify anyone.

## 2. Within-round repetition

| Round | n | Distinct masked hashes | Users with 2+ rows | Max rows/user | Same-user dup groups | Mixed | All-different |
|---|---:|---:|---:|---:|---:|---:|---:|
| 53 | 173 | 97 | 55 | 8 | 6 | 0 | 1 |
| 54 | 164 | 98 | 53 | 7 | 7 | 1 | 1 |
| 55 | 151 | 93 | 50 | 6 | 5 | 0 | 0 |
| 56 | 146 | 96 | 44 | 5 | 2 | 1 | 0 |
| 57 | 145 | 104 | 38 | 4 | 2 | 0 | 1 |
| 58 | 150 | 96 | 52 | 3 | 9 | 0 | 0 |
| 59 | 168 | 92 | 68 | 5 | 8 | 0 | 0 |
| 60 | 141 | 88 | 41 | 7 | 6 | 0 | 1 |
| 61 | 169 | 102 | 60 | 7 | 7 | 0 | 1 |
| 62 | 171 | 97 | 57 | **16** | 5 | 0 | 0 |
| 63 | 156 | 100 | 48 | 5 | 8 | 1 | 0 |
| 64 | 177 | 102 | 67 | 4 | 10 | 1 | 1 |
| 65 | 148 | 88 | 58 | 3 | 1 | 0 | 0 |
| 66 | 140 | 95 | 45 | 2 | 6 | 0 | 0 |
| 67 | 132 | 90 | 41 | 3 | 5 | 0 | 0 |
| 68 | 143 | 93 | 48 | 4 | 7 | 0 | 0 |

- Every round has 38–68 users with at least two rows.
- The maximum is 8 rows for most rounds, but **16 rows by one masked identifier in round 62**.
- Distinct hashes per round: 88–104 (mean 95.7).

## 3. +103s / +119s burst composition

| Round | +103 rows | +103 users | +119 rows | +119 users | User intersection | Jaccard | Number intersection |
|---|---:|---:|---:|---:|---:|---:|---:|
| 53 | 51 | 51 | 47 | 47 | 27 | 0.380 | 0 |
| 54 | 49 | 49 | 48 | 48 | 24 | 0.329 | 1 |
| 55 | 49 | 49 | 51 | 51 | 24 | 0.316 | 0 |
| 56 | 53 | 53 | 42 | 42 | 19 | 0.250 | 0 |
| 57 | 49 | 49 | 38 | 38 | 12 | 0.160 | 0 |
| 58 | 50 | 50 | 49 | 49 | 21 | 0.269 | 0 |
| 59 | 51 | 51 | 65 | 64 | 41 | 0.554 | 1 |
| 60 | 48 | 48 | 39 | 39 | 21 | 0.318 | 0 |
| 61 | 48 | 48 | 50 | 50 | 25 | 0.342 | 0 |
| 62 | 52 | 52 | 54 | 54 | 28 | 0.359 | 2 |
| 63 | 48 | 48 | 42 | 42 | 15 | 0.200 | 0 |
| 64 | 50 | 50 | 54 | 53 | 28 | 0.373 | 0 |
| 65 | 41 | 41 | 52 | 52 | 26 | 0.388 | 0 |
| 66 | 47 | 47 | 40 | 40 | 17 | 0.243 | 0 |
| 67 | 48 | 48 | 34 | 34 | 14 | 0.206 | 0 |
| 68 | 43 | 43 | 44 | 44 | 15 | 0.208 | 0 |

- Within a burst, rows ≈ distinct users: +103 has **rows = users in all 16 rounds**; +119 has rows = users in 14/16 (rounds 59 and 64 have one user with 2 rows).
- Number intersection between the two bursts is 0–2; the bursts are essentially different numbers.
- User overlap is 12–41; Jaccard 0.16–0.554.

### Is the overlap greater than chance?

Hypergeometric test per round (universe = distinct users in the round, two bursts drawn without replacement):

| Round | Universe U | +103 a | +119 b | Observed k | Expected a·b/U | P(X≥k) |
|---|---:|---:|---:|---:|---:|---:|
| 53 | 97 | 51 | 47 | 27 | 24.71 | 0.234 |
| 54 | 98 | 49 | 48 | 24 | 24.00 | 0.580 |
| 55 | 93 | 49 | 51 | 24 | 26.87 | 0.921 |
| 56 | 96 | 53 | 42 | 19 | 23.19 | 0.974 |
| 57 | 104 | 49 | 38 | 12 | 17.90 | 0.996 |
| 58 | 96 | 50 | 49 | 21 | 25.52 | 0.980 |
| 59 | 92 | 51 | 64 | 41 | 35.48 | **0.011** |
| 60 | 88 | 48 | 39 | 21 | 21.27 | 0.631 |
| 61 | 102 | 48 | 50 | 25 | 23.53 | 0.350 |
| 62 | 97 | 52 | 54 | 28 | 28.95 | 0.723 |
| 63 | 100 | 48 | 42 | 15 | 20.16 | 0.990 |
| 64 | 102 | 50 | 53 | 28 | 25.98 | 0.274 |
| 65 | 88 | 41 | 52 | 26 | 24.23 | 0.291 |
| 66 | 95 | 47 | 40 | 17 | 19.79 | 0.914 |
| 67 | 90 | 48 | 34 | 14 | 18.13 | 0.978 |
| 68 | 93 | 43 | 44 | 15 | 20.34 | 0.993 |

Only round 59 is nominally significant (p=0.011); with 16 tests, this does not survive multiple-testing correction. The other 15 rounds are at or below chance.

**Negative finding:** the two bursts are generally **not** composed of the same users more than expected. The apparent overlap is mostly explained by the large fraction of the round’s users who submit in each burst.

## 4. Same-number repetition

Across 16 rounds:

- **104 duplicate groups**, **120 duplicate entries**, **138 colliding pairs**.
- Ownership:
  - **94 same-user** (90.4%),
  - **4 mixed**,
  - **6 all-different**.
- **0/104 groups** have all copies in the same second.
- **3/138 colliding pairs** share a timestamp; 135 are at different seconds.

Permutation test:

- Null: shuffle `user_hash` labels within each round, preserving the number multiset and each user’s row count.
- Observed same-user duplicate groups: **94**.
- Null mean: **0.56**; null SD: **0.74**; null max over 10,000 permutations: **6**.
- **P(null ≥ 94) < 1e-4.**

This is a very strong result: same-user duplicate groups are far above what random association of users and numbers would produce. The duplicate pattern is deliberate/behavioral, not a side effect of high-volume users or number frequencies.

## 5. Cross-round persistence

- 469 distinct masked hashes.
- 286 (61.0%) appear in **2 or more** rounds.
- Recurrence histogram:

```
1 round: 183
2: 68
3: 55
4: 51
5: 21
6: 26
7: 22
8: 15
9: 9
10: 7
11: 2
12: 4
13: 2
14: 1
15: 1
16: 2
```

- Two hashes appear in **all 16 rounds**; one in 15; one in 14.
- **19 same-hash + same-number pairs** appear in ≥2 rounds.
- Top same-hash + same-number recurrence:
  - `85858` — 6 rounds,
  - `11111` — 6 rounds,
  - `52525` — 5 rounds,
  - `37553` — 4 rounds,
  - `55014` — 4 rounds.

This explains the cross-round number overlap in Phase B: it is largely the same masked identifiers repeating the same numbers, not a population-wide preference.

## 6. Outlier: round 62’s 16-row identifier

One masked hash submitted **16 rows** in round 62:

- 14 unique numbers, 2 duplicate entries.
- Numbers include `66666` ×3, `77777`, `55555`, `88888`, `99999`, plus 11 varied numbers.
- Timestamps: 21:11:15, 21:11:32, 21:12:36, 21:13:02, 21:13:22, 21:13:38, 21:14:01, 21:14:31, 21:14:48, 21:15:05, 21:15:23, 21:15:40, 21:15:56, 21:16:26, 21:16:43, 21:16:59.
- Offsets from close: −225, −208, −144, −118, −98, −82, −59, −29, −12, +5, +23, +40, +56, +86, +103, +119 seconds.
- Many gaps are 16–18 seconds; some are 30 or 64 seconds.
- One row in +103 and one in +119.

This is consistent with a **scripted/automated submission cadence**, but it is only one identifier and one round. It could also be a determined human submitting a prepared set. Classification: **HYPOTHESIS**, not proven. No attempt was made to identify the account.

## 7. Cross-date comparison

The task asks whether burst composition changes across independently observed dates.

- Phase C has **one date only** (2026-11-07, with the lottery day crossing midnight to 2026-11-08).
- The 88-round submission list is not archived; older period IDs return 404; the results page date filter does not provide 88-round submission history.
- Therefore **cross-date comparison is UNTESTABLE** with authorized public data.
- The 264-round product has per-date history but is a different game; it was not used as a proxy.

Status: **ACCESS BLOCKED / UNKNOWN.**

## 8. Masked-name collisions

- The mask format preserves a prefix and suffix and replaces the middle with `***`.
- Different accounts can share the same rendered mask; the site does not expose a unique public account ID in the row.
- 469 is therefore a count of **distinct masked display strings**, not verified people.
- The recurrence and same-user results are valid for **display identifiers**; they may undercount true accounts.
- No reversal or identification was attempted.

## 9. Can the audit be independently reproduced?

Yes:

```bash
cd phase_c
python3 scripts/build_c_dataset.py
python3 scripts/account_pattern_audit.py
```

Inputs: `evidence/combined_events.csv` (round, period, seq, number, timestamp, `user_hash`, offset). No raw names are needed. Outputs: `evidence/c_account_patterns.json`, `c_account_summary.csv`, `c_same_user_duplicates.csv`, `evidence/c_burst_overlap.csv`.

## 10. Verdict

| Claim | Verdict | Class |
|---|---|---|
| Within-round account repetition is common | 38–68 users with 2+ rows per round | OBSERVED |
| Same-number duplicates are same-user | 94/104 groups; permutation p<1e-4 | OBSERVED |
| Duplicates are same-second batches | 0/104 groups; 3/138 pairs | REJECTED |
| Two bursts share more users than chance | Only 1/16 nominally significant; not after correction | **NOT SUPPORTED** |
| Bursts are one automated client | Rows ≈ distinct users in every burst | **REJECTED** |
| Some users follow a scripted cadence | One 16-row outlier with ~17 s cadence | HYPOTHESIS |
| Patterns persist across dates | No historical 88-round data | **UNTESTABLE** |
| Masked-name collisions can distort counts | Possible; 469 is a display-identifier count | UNKNOWN |
| Account repetition implies manipulation/prediction | No evidence; behavior only | **REJECTED** |
