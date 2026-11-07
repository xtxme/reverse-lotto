# Investigation 3 — Why Are Five-Digit Numbers Repeated So Frequently?

Phase B, 2026-11-07. Inputs: 1,097 sanitized rows from periods 229–235 (rounds 53–59). No usernames are stored; user-level statements use aggregate counts computed in-browser.

## 1. Definition audit (Phase A)

Phase A reported “9 excess duplicate entries” (round 53) and “13” (round 54). Phase B recomputes:

```
duplicate_entries = n − unique_within_round
colliding_pairs   = Σ_v C(freq_v, 2)
```

| Round | n | Unique | Duplicate entries | Duplicate rate | Colliding pairs | Max frequency |
|---|---:|---:|---:|---:|---:|---:|
| 53 | 173 | 164 | **9** | 5.20% | 11 | 3 |
| 54 | 164 | 151 | **13** | 7.93% | 18 | 4 |
| 55 | 151 | 146 | 5 | 3.31% | 5 | 2 |
| 56 | 146 | 142 | 4 | 2.74% | 5 | 3 |
| 57 | 145 | 142 | 3 | 2.07% | 3 | 2 |
| 58 | 150 | 141 | 9 | 6.00% | 9 | 2 |
| 59 | 168 | 159 | 9 | 5.36% | 10 | 3 |
| **All** | **1,097** | **1,023** | **52** | **4.74%** | **61** | — |

The Phase A 9 and 13 figures are **VERIFIED** as duplicate entries. They are not colliding pairs: 9 entries produce 11 pairs in round 53, and 13 entries produce 18 pairs in round 54. Future reports must state which metric is used.

## 2. What the duplicates actually are

Aggregate user-level analysis (computed in-browser; raw usernames not stored):

| Round | Duplicate groups | All copies same user | Mixed users | All different users | Rows in duplicate groups |
|---|---:|---:|---:|---:|---:|
| 53 | 7 | 6 | 0 | 1 | 15 |
| 54 | 9 | 7 | 1 | 1 | 22 |
| 55 | 5 | 5 | 0 | 0 | 10 |
| 56 | 3 | 2 | 1 | 0 | 7 |
| 57 | 3 | 2 | 0 | 1 | 6 |
| 58 | 9 | 9 | 0 | 0 | 18 |
| 59 | 8 | 8 | 0 | 0 | 18 |

- **44 duplicate groups** across 7 rounds, containing **96 rows**.
- **37 groups are pairs, 6 are triples, 1 is a quadruple.**
- The majority of groups are one user submitting the same number multiple times; only 3 groups are all-different users.
- Top repeated values and their user structure:
  - `37553` ×3 in round 53 — **1 user** (3 copies).
  - `37553` ×4 in round 54 — **1 user** (4 copies).
  - `66666` ×3 in round 56 — 2 users (one user 2 copies).
  - `55359` ×3 in round 59 — **1 user**.
- Maximum rows per user in a round: 8 (round 53), 7 (54), 6 (55), 5 (56/59), 4 (57), 3 (58).

This is the central correction to the Phase A interpretation: the duplicates are **not primarily many independent users choosing the same “lucky” number**. They are mostly **one account repeating a number**, often several times in the same round.

## 3. Are duplicates concentrated at specific times?

- **0 of 44 duplicate groups** have all copies in the same second.
- Only **2 of 61 colliding pairs** share a timestamp; **59 of 61** are at different seconds.
- No duplicate group is a single-second batch artifact.
- Duplicate groups often have one copy inside a large burst because most rows are in the bursts, but the copies themselves are spread across different seconds.

Example: `37553` in round 54 has 4 copies, one user, at different timestamps. This is repeated submission over time, not a batch of identical rows.

## 4. Cross-round persistence

Number-set overlap between rounds:

- Observed pairwise intersections: **34** across 21 round pairs.
- Uniform expectation: **5.15**.
- Ratio: **6.6×**.
- 18 of 21 pairs share at least one number.
- Strongest pairs: 54–56 (3 observed vs 0.24 expected), 53–56 (3 vs 0.25), 54–59 (3 vs 0.28), 53–54 (3 vs 0.28).

Top recurring values across 7 rounds:

| Number | Count | Rounds present | Uniform expected | Family-wise p |
|---|---:|---|---:|---:|
| 37553 | 8 | 53, 54, 59 | 0.011 | <1e-9 |
| 66666 | 8 | 54, 55, 56, 59 | 0.011 | <1e-9 |
| 55014 | 6 | 53, 54 | 0.011 | 2.3e-10 |
| 85858 | 5 | 53, 55, 56, 57, 58 | 0.011 | 1.3e-7 |
| 88888 | 5 | 53, 54, 57 | 0.011 | 1.3e-7 |
| 00000 | 4 | 54, 56, 59 | 0.011 | 6.0e-5 |
| 55555 | 3 | 54 | 0.011 | 0.022 |
| 55359 | 3 | 59 | 0.011 | 0.022 |

The tail is far above uniform. However, the same-user structure means this is likely **persistent accounts repeating their own numbers**, not a population-wide number preference. `37553` appears 8 times but is one user in each observed round; `66666` appears across four rounds and is consistent with a user or a small set of users repeating a favorite.

Multiple-testing caveat: the pairwise overlap p-values are not corrected in the raw table. With 21 pairs, the smallest p (0.0019) becomes ~0.04 under Holm, so the pairwise evidence is marginal. The recurring-number tail is stronger (family-wise p < 1e-6 for the top values), but it is still only 7 rounds from one day.

The raw split-half Pearson correlation over all seen numbers is **not** used as evidence: with ~1,000 observed values spread over 100,000 categories, it is dominated by zeros and the two halves have different totals. It is not a valid persistence statistic; the pairwise overlap and the recurring-number tail are the appropriate summaries.

## 5. Pattern frequencies

| Pattern | Observed | Uniform expected | Ratio |
|---|---:|---:|---:|
| All five digits identical | 23 | 0.11 | 209.7× |
| Exactly four digits identical | 9 | 4.94 | 1.8× |
| Palindrome | 46 | 1.10 | 41.9× |
| At least one repeated digit | 795 | 765.27 | 1.04× |

Interpretation:

- There is a strong excess of **highly patterned** numbers (all-same, palindrome).
- The broad “at least one repeated digit” rate is only 4% above uniform, so the bias is not a general preference for repeated digits; it is concentrated in a few salient patterns and a few recurring values.
- The all-same excess is dominated by `66666` (8), `88888` (5), `55555` (3), `00000` (4) — the same values that recur across rounds.

## 6. Null models and simulations

Script: `phase_b/duplicate_simulation.py`; seed 20261107; 20,000 simulations per round/model.

| Model | Description | Aggregate mean duplicate entries | 95% sim interval | Observed 52 | Verdict |
|---|---|---:|---|---:|---|
| A — uniform iid | independent uniform 00000–99999 | 0.86 | 0–3 | 52 | **Rejected** (p < 1e-4) |
| B — finite-pool other rounds | draw from the other six rounds’ observed multiset | 102.3 | 85–120 | 52 | Over-predicts; cannot generate unseen numbers; not a credible generative null |
| C — smoothed empirical, ε=0.5 | 50% finite-pool, 50% uniform | 27.4 | 18–38 | 52 | **Rejected** (p < 1e-4) |
| C — smoothed empirical, ε=0.9 | 10% finite-pool, 90% uniform | 1.95 | 0–5 | 52 | **Rejected** (p < 1e-4) |
| D — positional digits | independent digit distributions estimated from other rounds | 0.90 | 0–3 | 52 | **Rejected** (p < 1e-4) |
| E — pooled in-sample | draw from all seven rounds | 90.0 | 73–107 | 52 | Over-predicts; in-sample, not a test |

Key point: **no population-level number distribution that can generate unseen numbers comes close to 52 duplicates.** The observed value is far above uniform, digit-marginal, and smoothed models. A finite-pool model can be tuned to produce ~52 by construction (ε≈0.33), but it does so by reusing observed values and cannot reproduce the same-user grouping or the “different seconds” structure.

**Model-naming note.** The prompt’s model D (“repeated submissions of the same number, only if supported by data”) is supported by the aggregate evidence, but it is not simulated row-by-row because the sanitized dataset intentionally omits per-row user links. The `D_positional_digits` model above is an additional population-level model, not the same-user model. A faithful same-user model would require retaining user hashes and would likely reproduce the 39/44 same-user groups; it would not make the outcome predictable.

The correct explanatory model is **per-user repetition**:

- Each round has ~93–104 distinct users and 145–173 rows.
- 38–68 users submit at least two rows.
- The duplicate groups are mostly one user repeating a number.
- A per-user repeat model would require per-row user links, which the sanitized dataset intentionally does not retain.

## 7. Do duplicate patterns change near closure?

- Duplicates occur at different seconds throughout the submission window; there is no evidence that they cluster in the final 20 seconds more than non-duplicates.
- The two large bursts contain mostly unique numbers; the duplicate copies are not the burst itself.
- The number of duplicate groups per round varies 3–9 without a clear trend toward closure.

## 8. Hypotheses

| Hypothesis | Support | Status |
|---|---|---|
| Many independent users choose the same favorite numbers | Recurring values exist | **Weakened**: most groups are same-user; only 3/44 are all-different users |
| One user repeats their own number | 41/44 groups involve one user; 0 all-same-second; top duplicates one user | **OBSERVED** |
| Automated/scripted number sets | Same-user repeats, max 8 rows/user, bursty timing | **HYPOTHESIS**, not proven |
| Population-wide number bias | All-same/palindrome excess | **PARTIAL**: pattern bias exists but does not explain 52 duplicates under any tested population model |
| Batch timestamp assignment causes duplicates | — | **REJECTED**: duplicates span different seconds |

## 9. Statistical limitations

- 7 rounds from one day; not enough for seasonal/day-of-week effects.
- Per-row user links were not retained; model E is aggregate, not simulated.
- Models B/C/D are approximations; a more elaborate human-preference model could be fitted, but fitting the duplicate count alone would not explain the same-user structure.
- The recurring-number p-values are post-hoc selected; family-wise correction is reported but the selection itself is data-driven.
- Number frequencies are not evidence that future lottery results can be predicted; the result depends on the sum and row 16, not on any single favorite number.

## 10. Verdict

- **Duplicates are real and far above uniform**: 52 duplicate entries vs 0.86 expected over 1,097 rows.
- **They are not primarily a population-wide choice of the same numbers**: 41/44 groups involve one user; only 3/44 are all-different users.
- **They are repeated submissions by the same user at different times**: 0/44 groups share a single second; 59/61 colliding pairs are at different seconds.
- **A per-user repeat mechanism is required**; no tested population-level model explains the data.
- **This does not imply predictability**: knowing that a user repeats `37553` says nothing about the sum modulo 100,000 or the final row 16.
