# Investigation 5 — Independent Audit of the Phase A Monte Carlo

This audit re-ran the Phase A scripts, reproduced the published statistics, tested the implementation, and varied the model assumptions. The key finding is that **the Phase A Monte Carlo result is reproducible, but it is a simulation under a null model, not a test of the live process, and its p-value is not stable across random seeds.**

## 1. What was tested in Phase A

Phase A ran six exploratory checks on 53 published results (rounds 1–53 of 2026-11-07):

| # | Test | Null hypothesis |
|---|---|---|
| 1 | Last-digit uniformity, 10 bins | Each last digit has probability 0.1 |
| 2 | Bottom-2 occupancy, 100 bins | Each 2-digit value is equally likely |
| 3 | Runs test on top-3 above/below median | No serial dependence |
| 4 | Lag-1 autocorrelation of the 5-digit outcome | No first-order correlation |
| 5 | “Hot last digit” out-of-sample | The most frequent training digit has no advantage in the test period |
| 6 | Monte Carlo of the formula with the empirical submission pool | The formula’s output is uniform given the observed pool distribution |

Phase A did **not** test a prospective model against genuinely unseen future rounds. It tested whether the observed historical sequence shows gross deviations from randomness and whether the formula transforms a non-uniform pool into a near-uniform output.

## 2. Reproduction of the published statistics

Command:

```
python3 evidence/reproducible_tests/randomness_tests.py
```

Exact output reproduced in `phase_b/evidence/phase_a_randomness_reproduction.txt`:

| Test | Phase A result | Phase B reproduction |
|---|---|---|
| Last-digit χ² | 8.321, df=9, p=0.5022 | 8.321, p=0.5022 |
| Bottom-2 distinct/max | 39 distinct, max 3; P(max≥3)=0.842, P(distinct≤39)=0.225 | identical |
| Runs test | 29 runs, expected 27.49, z=0.419, p=0.6753 | identical |
| Lag-1 autocorrelation | r=−0.1205, SE≈0.1374 | identical |
| Hot last digit | digit 9, 3/23 hits, p=0.408 | identical |
| Monte Carlo | χ²=14.044, p=0.1208, counts [1953, 2084, 1967, 1923, 1983, 1980, 2008, 2086, 2050, 1966] | identical (when the RNG state is replayed) |

The χ² survival function was checked against known critical values:

```
χ²=16.919, df=9 → 0.05000
χ²=14.684, df=9 → 0.09999
χ²=21.666, df=9 → 0.01000
χ²=3.325,  df=9 → 0.95001
```

No implementation error was found in the survival function.

## 3. The reproduction requires replaying the RNG state

Phase A seeded `random` once, then ran test 2 (20,000 × 53 `randrange(100)` calls) before test 6. The published counts are reproduced **only** when that prior consumption is replayed.

If test 6 is started from a fresh `random.seed(20261107)`, the result changes:

| RNG path | χ² | p |
|---|---:|---:|
| Replayed Phase A state | 14.044 | 0.1208 |
| Fresh Python seed | 4.027 | 0.9096 |
| Fresh NumPy seed | 11.082 | 0.2701 |
| Same config, 200,000 iterations | 8.849 | 0.4513 |

This is not a bug in Phase A; it is the expected Monte Carlo variability. It does mean that quoting **p = 0.12** as if it were a stable property of the live process is misleading. The p-value is a draw from an approximately uniform distribution under the simulation null.

## 4. p-value distribution across 100 seeds

Main configuration: pool 229+230 (337 values), 168 draws, `draw[15]`, 20,000 iterations.

```
mean = 0.4816
median = 0.4995
5th percentile = 0.0334
95th percentile = 0.9543
P(p < 0.05) = 0.070
```

Under a correct null simulation, p-values are uniform and `P(p<0.05) ≈ 0.05`. The observed 7% is within Monte Carlo noise for 100 seeds (SE ≈ 1.6%; 7% is ~1.3σ). There is no evidence of a systematic bias in the simulation.

The Phase A p=0.1208 is therefore unremarkable: it is one draw from this distribution.

## 5. Sensitivity to pool, n, and the position-16 rule

`simulation_comparison.csv` contains 64 configurations: 4 pools × 4 draw counts × 4 position-16 rules, 20,000 iterations each, seed fixed.

| Dimension | Values | Mean p | Range | p<0.05 count |
|---|---|---:|---|---:|
| Pool | 229 | 0.463 | 0.064–0.986 | 0/16 |
| Pool | 230 | 0.440 | 0.009–0.934 | 3/16 |
| Pool | 229+230 | 0.494 | 0.102–0.965 | 0/16 |
| Pool | all 7 rounds | 0.537 | 0.031–0.967 | 1/16 |
| Draws | 151 | 0.429 | 0.009–0.937 | 2/16 |
| Draws | 164 | 0.338 | 0.020–0.986 | 2/16 |
| Draws | 168 | 0.561 | 0.102–0.965 | 0/16 |
| Draws | 173 | 0.606 | 0.065–0.967 | 0/16 |
| Rule | 16th chronological | 0.451 | 0.020–0.862 | 2/16 |
| Rule | 16th from end | 0.459 | 0.024–0.937 | 1/16 |
| Rule | last draw | 0.514 | 0.009–0.967 | 1/16 |
| Rule | random row | 0.510 | 0.063–0.986 | 0/16 |

Overall: 4 of 64 p-values < 0.05 (expected 3.2). Mean p = 0.484. No pool, n, or position-16 rule produces a systematic deviation. **No configuration survives multiple-testing correction.**

This is the expected result if the formula’s output is uniform given the pool: the choice of 16th rule changes the exact draw but not the distribution.

## 6. What the Monte Carlo does and does not model

Modeled:

- the 5-digit numbers and their empirical frequencies,
- the sum,
- subtraction of a selected row,
- modulo 100,000,
- last-digit outcomes.

Not modeled:

- the real timestamp ordering (newest-first),
- the two fixed +103/+119 bursts,
- same-user repeated numbers,
- the fact that the final pool is fixed only after the shooting window,
- server-side cancellation, refunds, or rounding.

The simulation is a **model of the arithmetic**, not a generative model of the live submission process. A failure to reject uniformity in this simulation does not prove that the live process is uniform; it only shows that the arithmetic washes out the observed pool’s marginal bias at this pool size.

## 7. Effect sizes and confidence intervals

The Phase A report emphasized p-values. The effect sizes are small and mostly compatible with noise:

| Quantity | Estimate | 95% interval / note |
|---|---|---|
| Last-digit Cramér’s V | 0.132 | bootstrap 0.116–0.267; null expected ≈0.137 |
| Runs z | 0.419 | not significant |
| Lag-1 autocorrelation | −0.1205 | bootstrap −0.285 to 0.247; permutation p=0.3805 |
| Hot-digit rate | 13.0% (3/23) | Wilson 4.5%–32.1%; expected 10% |
| Bottom-2 distinct values | 39/100 | uniform expected 41.3 |
| Split-half last-digit homogeneity | χ²=8.127, df=9, p=0.5214 | no evidence of a change between halves |

The Cramér’s V of 0.132 is almost exactly the value expected from finite-sample noise when the null is true (≈√(1/53)=0.137). It is not evidence of a real digit bias.

## 8. Multiple-comparison correction

Phase A ran at least six tests without correction. Applying Holm and Benjamini–Hochberg to the seven exploratory p-values:

| Test | p | Holm | BH |
|---|---:|---:|---:|
| Monte Carlo | 0.1208 | 0.8456 | 0.7031 |
| Bottom-2 distinct | 0.2250 | 1.0000 | 0.7031 |
| Autocorrelation | 0.3805 | 1.0000 | 0.7031 |
| Hot digit | 0.4080 | 1.0000 | 0.7031 |
| Last digit | 0.5022 | 1.0000 | 0.7031 |
| Runs | 0.6753 | 1.0000 | 0.7031 |
| Bottom-2 max | 0.8420 | 1.0000 | 0.8420 |

No result is significant after correction.

## 9. Was there future-information leakage?

- The 53 results were all published before the analysis; no future result was used.
- The Monte Carlo pool is rounds 229+230, which correspond to rounds 53+54 in the same 53-result dataset. This is **in-sample overlap**, not future leakage, but it means the simulation and the outcome dataset are not independent.
- The hot-digit test used rounds 1–30 for training and 31–53 for testing; this is a genuine chronological split.
- The split-half digit test used rounds 1–26 vs 27–53; no leakage.
- No model was fitted on the test period.

## 10. Sample size and power

- n=53 is enough to detect a very large last-digit bias, but not a subtle one.
- For a 3-digit outcome (1,000 categories), the expected count per category is 0.053. Even a perfect uniformity test has essentially no power; thousands of rounds would be needed.
- The 53 results are from one day. They are not a random sample across days, times of day, or submission regimes.
- The confidence intervals above are wide; the absence of significance is not proof of randomness.

## 11. Conclusion

- Phase A’s arithmetic is reproducible.
- The p=0.1208 Monte Carlo value is a single draw from an approximately uniform p-value distribution; it is not stable and not evidence about the live process.
- No effect survives multiple-testing correction.
- No validated prospective relationship was found.
- The simulation’s failure to reject uniformity does **not** prove perfect randomness; it is simply the expected result of the null model.
- The main unresolved statistical question is whether the final `(Σ − x16) mod 100000` distribution is uniform over a much larger, multi-day sample. The available 53 results cannot answer that.

## 12. Files

- `phase_b/monte_carlo_reproduction.py` — reproduction and sensitivity script.
- `phase_b/simulation_comparison.csv` — 64 configurations.
- `phase_b/evidence/mc_pvalue_distribution.csv` — 100 seeds.
- `phase_b/evidence/phase_a_randomness_reproduction.txt` — raw reproduction output.
- `phase_b/statistical_validation.md` — narrative validation and limitations.
