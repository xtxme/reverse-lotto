# Statistical Validation — Phase B

This document separates three different things that are easy to conflate:

1. **A deterministic formula for completed rounds** — verified.
2. **A statistical model of historical outcomes** — exploratory and underpowered.
3. **A genuinely validated prospective prediction** — not demonstrated.

## 1. Data provenance and record assignment

| Item | Value | Audit |
|---|---|---|
| Results dataset | `evidence/sanitized_observations/results_2026-11-07.json` | 53 records, rounds 1–53, each round exactly once |
| Top/bottom format | 3 digits / 2 digits | all 53 valid |
| Result source | server-rendered `/member/lottery/yeekee` cards | collected 2026-11-07 19:23 |
| Raw pool dataset | periods 229–235 (rounds 53–59) | 1,097 rows, 7 complete rounds |
| Timestamps | Bangkok local, second precision | server-rendered; no ms |
| Round mapping | period 229→53 … 235→59 | verified against `data-href` and page titles |
| Formula check | rounds 53, 54, 55 | exact match of sum, row 16, result, top3, bottom2 |
| Additional checks | rounds 56–59 | exact match of top3/bottom2 |

The 53-result file was checked for duplicate or missing round numbers: 53 unique round numbers, 1–53. No record was assigned to the wrong round.

## 2. Input audit: the 337-number pool

Phase A’s Monte Carlo used `ROUND_229` (173 numbers) + `ROUND_230` (164 numbers) = 337 values.

- Both lists are complete public submissions, not samples.
- The pool contains the observed duplicates (e.g. `37553` ×3 in 229, ×4 in 230; `55014` ×3; `55555` ×3).
- `random.choice(pool)` preserves those frequencies by construction.
- The pool is **not** a random sample of all possible 5-digit numbers; it is two consecutive rounds from one evening.
- The pool overlaps the 53-result dataset (rounds 53 and 54). This is in-sample overlap, not future leakage, but it means the simulation and the outcomes are not independent.

A positional digit model was added in Phase B to test whether marginal digit preferences (not whole-number frequencies) explain the duplicates; it did not (mean 0.90 duplicate entries vs 52 observed).

## 3. Position-16 audit

The published rule and the live pages use the **16th row of the newest-first table**, not the 16th chronological submission.

Counter-test:

| Round | Display row 16 | Result with it | 16th chronological | Result with it | Published |
|---|---|---|---|---|---|
| 53 | 80308 | **9,201,269** ✓ | 78956 | 9,202,621 ✗ | 9,201,269 |
| 54 | 62839 | **7,661,325** ✓ | 86868 | 7,637,296 ✗ | 7,661,325 |

The simulation uses `draw[15]` (16th synthetic draw). Under iid draws this is distributionally equivalent to any fixed position, but it is **not** a faithful representation of the real newest-first, tied-timestamp ordering. Phase B therefore tested four rules (`16th chronological`, `16th from end`, `last`, `random row`); all produced p-values consistent with the simulation null. The exact rule does not change the conclusion, but the simulation should not be described as reproducing the real ordering.

## 4. Ordering and duplicate audit

- Public row order is stable across repeated fetches.
- Page 1 and page 2 are contiguous (seq 1–50, 51–100).
- The JSON first page matches the HTML first page.
- 44 duplicate-number groups, 96 rows; 0 groups all in the same second; 59/61 colliding pairs at different seconds.
- Duplicates are mostly same-user repeats, not population-wide collisions.

The Phase A Monte Carlo does not model same-user repeats or the two fixed +103/+119 bursts. Its output is therefore a model of the arithmetic, not a generative model of the live pool.

## 5. What the real-data tests actually show

| Test | Statistic | p / interval | Correct interpretation |
|---|---|---|---|
| Last-digit χ² | 8.321, df=9 | p=0.5022 | No gross bias; underpowered |
| Runs | 29 vs 27.49 | z=0.419, p=0.6753 | No serial dependence |
| Lag-1 autocorrelation | −0.1205 | bootstrap −0.285..0.247; perm p=0.3805 | No first-order dependence |
| Hot digit out-of-sample | 3/23 = 13.0% | Wilson 4.5%–32.1%; p=0.408 | No advantage over 10% |
| Bottom-2 distinct | 39/100 | uniform expected 41.3 | Consistent with uniform |
| Split-half last digits | χ²=8.127, df=9 | p=0.5214 | No change between halves |

The Cramér’s V for the last-digit test is 0.132. Under the null with n=53 and 10 bins, the expected V is about √(1/53)=0.137. The observed value is indistinguishable from finite-sample noise.

## 6. The Monte Carlo p-value is not stable

The Phase A p=0.1208 is reproducible only when the RNG state is replayed exactly (test 2 consumed 20,000×53 draws before test 6). Fresh seeds produce:

| Run | χ² | p |
|---|---:|---:|
| Replayed Phase A | 14.044 | 0.1208 |
| Fresh Python seed | 4.027 | 0.9096 |
| Fresh NumPy seed | 11.082 | 0.2701 |
| 200,000 iterations | 8.849 | 0.4513 |

Across 100 seeds (main configuration): mean p=0.4816, median 0.4995, 5th 0.0334, 95th 0.9543, P(p<0.05)=0.070. This is consistent with a uniform p-value distribution under the simulation null.

Therefore, “p≈0.12” should not be presented as a stable empirical result. It is one Monte Carlo draw.

## 7. Multiple testing

Seven exploratory p-values were corrected:

- Holm-adjusted minimum: 0.8456 (Monte Carlo).
- Benjamini–Hochberg-adjusted minimum: 0.7031.
- No test is significant at 0.05 after correction.

This is expected given the small effects and the small sample.

## 8. Out-of-sample validation

- Hot-digit rule: trained on rounds 1–30, tested on 31–53; 3/23 hits, p=0.408. No advantage.
- Split-half digit homogeneity: first 26 vs last 27; p=0.5214. No distribution change.
- No model was fitted on the test period; no future results were used.

No genuinely prospective validation (tomorrow’s or next week’s unseen rounds) was performed. That is the only test that could establish a predictive relationship.

## 9. Power and sample size

- n=53 is enough to detect only a very large last-digit bias.
- For a 3-digit outcome (1,000 categories), expected count per category is 0.053; the test has essentially no power. Tens of thousands of rounds would be needed for a meaningful uniformity test.
- The 53 results are one day, not a random sample across days/times/regimes. Confidence intervals are wide.
- Failure to reject randomness is **not** proof of perfect randomness.

## 10. Reproducibility failures and limitations

1. **RNG-state dependence**: the published p=0.1208 is not reproducible from a fresh seed; it requires replaying prior test consumption.
2. **Finite-pool model**: resampling from 337 observed values cannot generate unseen numbers and over-predicts duplicates (mean 102 vs observed 52). It is a bounding sensitivity, not a credible null.
3. **Ordering**: the simulation uses a synthetic iid order, not the real newest-first/tied timestamp order.
4. **Same-user structure**: not modeled; duplicates are mostly same-user repeats.
5. **In-sample overlap**: the pool includes rounds 53/54, which are also in the 53-result dataset.
6. **No prospective test**: no model was evaluated on unseen future rounds.
7. **Multiple testing**: Phase A did not correct; Phase B does.
8. **No 3-digit power**: the sample cannot support claims about 3-digit uniformity.

## 11. Verdict

| Claim | Status |
|---|---|
| The formula is deterministic for completed rounds | **VERIFIED** (3 rounds exact; 7 rounds top/bottom exact) |
| The historical sequence shows a gross last-digit bias | **NOT SUPPORTED** (p=0.50; V≈null expectation) |
| The historical sequence shows serial dependence | **NOT SUPPORTED** (runs p=0.68; autocorr p=0.38) |
| A simple hot-digit rule has an out-of-sample advantage | **NOT SUPPORTED** (3/23, p=0.41) |
| The formula transforms the observed pool into a near-uniform output | **CONSISTENT WITH SIMULATION**, but the simulation is not the live process |
| A validated prospective prediction exists | **NOT DEMONSTRATED** |
| Any public pre-cutoff variable predicts the final result | **NO VALIDATED RELATIONSHIP**; at cutoff the pool has 0–5 rows, so row 16 is not even defined |

## 12. What would constitute real evidence

- A pre-registered model, frozen before a future round.
- Evaluation on genuinely unseen rounds (not the same day).
- A proper scoring rule (log loss / Brier) against the uniform baseline.
- Confidence intervals and a power calculation.
- Full submission pools and timestamps for each evaluated round.
- Correction for multiple comparisons.

Until then, the correct statement is: **the arithmetic is known; the outcome distribution is statistically indistinguishable from uniform in the available sample; no predictive advantage has been demonstrated.**
