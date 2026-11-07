# Predictive Feasibility

Question: using only legally accessible public data and the authorized member view, is there reproducible evidence that future Yeekee results can be predicted?

Short answer: **no.** The result is deterministic once the final submission set exists, but the decisive inputs are only fixed two minutes after betting closes. Before that, they are unknown, and the observed outputs are statistically consistent with a uniform draw.

## 1. What is deterministic

Given the final pool:

```
R = (Σ all submitted numbers) − (number in display row 16)
top3    = last three digits of R
bottom2 = preceding two digits
```

This was verified exactly on three rounds (see `result_algorithm_research.md`). So the mapping from a known pool to a result is fully deterministic. The uncertainty is entirely in the inputs.

## 2. When the inputs become known

| Input | Available before betting close? | Available before result? |
|---|---|---|
| Numbers submitted before close | partly (pool opens ~2 min before close) | yes |
| Numbers submitted in the 2-minute shoot window after close | no | yes |
| Final display row 16 | no (it can change with every new submission) | yes |
| Final sum | no | yes |
| Server-side cancellation/refund decision | no | possibly only in the UI |

In round 55, only 5 of 151 submissions existed before 19:30:00; 146 arrived at or after betting closed. In round 53, 173 submissions were compressed into only 44 distinct seconds. The final pool is therefore dominated by submissions that did not exist at betting close.

**Conclusion:** the result cannot be computed before betting closes, because the majority of the determining inputs do not yet exist.

Classification: OBSERVED.

## 3. Structural argument for uniformity

Let the final sum be `S = Σ x_i` and the 16th value be `x_16`. The prize number is `(S − x_16) mod 100000`.

If at least one submitted number is uniformly distributed on `0…99999` and independent of the others, then `S mod 100000` is uniform, and subtracting a constant preserves uniformity. Human-submitted numbers are not uniform, but with 150+ submissions drawn from a broad distribution, the sum modulo 100000 concentrates toward uniform. The transform does not amplify any single member’s bias; it averages it.

This is a mathematical expectation, not a proof about this operator. It is testable with the empirical pool (section 5).

## 4. Statistical tests on observed results

Dataset: 53 published rounds on 2026-11-07 (rounds 1–53). Script: `evidence/reproducible_tests/randomness_tests.py`.

| Test | Result | Interpretation |
|---|---|---|
| Last-digit uniformity (10 bins) | χ² = 8.32, df = 9, p = 0.50 | No evidence of bias; expected 5.3/bin, underpowered |
| Bottom-2 (100 bins) Monte Carlo | observed 39 distinct, max bin 3; P(max ≥ 3) = 0.84 | Consistent with uniform |
| Runs test (top-3 above/below median) | 29 runs vs 27.5 expected, z = 0.42, p = 0.68 | No serial dependence |
| Lag-1 autocorrelation of 5-digit outcome | r = −0.12, 95% band ±0.27 | Not significant |
| “Hot last digit” out-of-sample | 3/23 hits vs 2.3 expected, p = 0.41 | No advantage |
| Monte Carlo of the formula with the empirical pool (337 real numbers, 20k simulations, 168 draws/round) | last-digit χ² = 14.04, df = 9, p = 0.12 | Near-uniform; no exploitable residue |

These are exploratory tests. With n = 53, power is very low, especially for 3-digit outcomes (1000 categories, expected 0.053 per category). A non-significant result does not prove randomness; it only fails to find dependence. Conversely, a p-value near 0.05 in a single test would not survive multiple-testing correction.

Classification: OBSERVED test outputs; interpretation is statistical, not proof of the backend.

## 5. Monte Carlo: does the non-uniform pool survive the transform?

The observed submission pool is clearly non-uniform:

- 9 duplicate-excess in 173 numbers (round 53), 13 in 164 (round 54); chance expectation is ~0.15.
- Recurring favorites: `37553`, `55014`, `55555`, `62839`, `11323`.
- First-digit and last-digit distributions are visibly uneven.

Nevertheless, resampling 168 numbers from the empirical pool and applying the published formula produced last-digit counts of 1923–2086 out of 20,000 (expected 2000), χ² = 14.04, p = 0.12. In other words, the arithmetic washes out the visible human bias at this pool size. A predictor would need to forecast the *sum of future submissions*, not merely the distribution of individual numbers, and the sum is dominated by volume.

Classification: OBSERVED simulation; INFERRED generality.

## 6. What about the public pre-close pool?

The pool is visible before betting closes (from roughly `close − 2 minutes`), including a running `sum` and the current row 16. Could that support a prediction?

- The pool is incomplete: most submissions arrive after close (146/151 in round 55).
- The sum grows monotonically as submissions are added; knowing it early says little about the final value.
- Row 16 can change with each new submission.
- The final two minutes contain heavy bursts (e.g. 49 submissions in one second, 51 in another).

To exploit the pre-close view, one would need a model that predicts the remaining submissions’ sum to within a narrow range. No such model is supported by the observed data; the arrival process is bursty and volume-driven, and the last-second batch is not observable in advance.

Classification: OBSERVED for the pool timing; no predictive model found.

## 7. Prediction vs influence (design risk, not prediction)

There is a separate, theoretical game-design concern: because the formula is public and submissions are free/unlimited until `close + 2 minutes`, a participant who could reliably submit at the very end and observe the running total might be able to *influence* the output rather than predict it. Their own submission changes both the sum and the row ordering, so the effect is computable in principle.

This report does **not** test, optimize, or provide a procedure for that. It is flagged as a HYPOTHESIS and a design risk for the operator. Mitigations would include a commit–reveal or cryptographic beacon for the 16th selection, a submission cut-off strictly before betting close, randomized ordering, or ignoring submissions after close. The site already rewards position 1 (the newest row), which arguably incentivizes last-second behavior.

Classification: HYPOTHESIS. Not verified; no attempt was made to influence a result.

## 8. Out-of-sample discipline

No model was fitted and deployed. The hot-digit test used the first 30 rounds for training and the next 23 for testing, and it failed to beat the uniform baseline. Any future claim should:

- be specified before looking at the test data,
- use a held-out period,
- report a proper scoring rule (log loss / Brier) against the uniform baseline,
- correct for multiple comparisons,
- report confidence intervals, not just point hits.

With 53 draws, even a genuine small bias would be undetectable. Thousands of draws and full submission data would be needed to test second-order effects; even then, the structural argument in section 3 predicts no exploitable edge.

## 9. Conclusion

- **Deterministic given the final pool:** yes.
- **Predictable before betting close from public data:** no evidence, and a structural reason why not (final inputs arrive after close).
- **Predictable from historical results alone:** no evidence; tests are consistent with uniformity.
- **Access to unpublished results:** none observed; no attempt was made.
- **Credible predictive advantage:** none found.

The correct statement is: *the result can be recomputed by anyone who can read the final public pool at `close + 2 minutes`; it cannot be predicted before the pool is final.*

## 10. What would change this conclusion

- A verified server-side leak of future submissions or the final sum before close (none observed).
- A measurable, stable bias in the final `(Σ − x16) mod 100000` distribution over tens of thousands of rounds (not testable with the available archive).
- A proven ability to forecast the final two minutes of submissions with low error (not supported by the bursty arrival data).
- A change in the rules that fixes the pool before betting close.

Until one of those is demonstrated with out-of-sample evidence, no betting recommendation can be justified.
