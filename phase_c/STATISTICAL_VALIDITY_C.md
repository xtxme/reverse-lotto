# Statistical Validity — Phase C

Phase C tests a small set of **predefined** hypotheses about submission patterns. It does not search for winning-number formulas, does not infer manipulation, and does not use post-hoc pattern mining.

## 1. Data and scope

| Item | Value |
|---|---|
| Rounds | 16 (rounds 53–68) |
| Periods | 229–244 |
| Rows | 2,474 |
| Dates | 2026-11-07 (lottery day crossing into 2026-11-08 00:00) |
| Account identifier | truncated SHA-256 of masked display name (`user_hash`) |
| Cross-day data | **NONE** (88-round archive unavailable) |

The data covers **one lottery day**, not multiple days. Any claim about day-to-day persistence is untestable with this evidence.

## 2. Predefined hypotheses and results

| ID | Hypothesis | Test | Result | Verdict |
|---|---|---|---|---|
| H1 | The +103 s and +119 s bursts occur in every round | Count per round | 16/16 rounds have both bursts | **SUPPORTED (within day)** |
| H2 | Display row 16 falls in the +119 s group | Row-16 offset | 16/16 at +119 s; random-position probability ≈4.3e-9 | **SUPPORTED** |
| H3 | Duplicate-number groups are same-user | Ownership + permutation of user labels | 94/104 same-user; null mean 0.56; max 6; p<1e-4 | **SUPPORTED** |
| H4 | The +103 and +119 bursts share more users than chance | Hypergeometric per round | Only round 59 p=0.011; 15/16 p>0.2; not significant after 16-test correction | **NOT SUPPORTED** |
| H5 | Submission patterns persist across different days | Cross-day comparison | No historical 88-round data | **UNTESTABLE / ACCESS BLOCKED** |
| H6 | Masked account recurrence persists across different days | Cross-day recurrence | No historical 88-round data | **UNTESTABLE / ACCESS BLOCKED** |

No other hypotheses were tested. No model was fitted to a test set and then evaluated on the same data.

## 3. Multiple testing

- H4 involved 16 hypergeometric tests. The smallest p (0.011) does not survive Holm or BH correction across 16 tests.
- The same-user duplicate permutation test is a single predefined test with p<1e-4; it does not rely on multiple comparisons.
- H1 and H2 are counting tests, not p-value searches.

## 4. Effect sizes

| Quantity | Value |
|---|---|
| Rounds with both bursts | 16/16 |
| Burst rows share of all rows | 1,526/2,474 = 61.68% |
| Row-16 +119 share | 16/16 |
| Same-user duplicate groups | 94/104 = 90.4% |
| Same-second duplicate groups | 0/104 |
| Same-second colliding pairs | 3/138 = 2.2% |
| Distinct masked hashes | 469 |
| Hashes in ≥2 rounds | 286/469 = 61.0% |
| Same hash + same number in ≥2 rounds | 19 pairs |

## 5. Negative findings

- The two bursts are **not** generally composed of the same users more than chance; the overlap is largely explained by the large active-user base.
- There is **no evidence** that burst composition or account repetition predicts future results.
- There is **no evidence** that account repetition implies manipulation, collusion, or automation; it is a behavioral observation.
- There is **no cross-day evidence** at all for the 88-round product; the historical archive is unavailable.
- The 16-row round-62 cadence is an outlier consistent with scripting, but it is only one identifier and one round; it is a HYPOTHESIS, not proof.

## 6. Power and limitations

- 16 rounds from one day are enough to show within-day regularity, not day-to-day persistence.
- 469 masked identifiers are display strings, not verified persons; masked-name collisions can undercount accounts.
- The +103/+119 offsets are exact to the second; the underlying cause (batch commit vs synchronized clients) is not identified.
- The data cannot distinguish “many users at the deadline” from “server batch commit” without operator logs.
- No prospective prediction was tested; no betting recommendation is made.

## 7. Verdict

**Within one lottery day**, the submission pattern is highly regular: two fixed bursts, row 16 in the final-second group, and same-user duplicate repetition far above chance.

**Across different days**, nothing can be concluded because the 88-round historical archive is not accessible through the normal UI. The correct label for the cross-day claims is **UNKNOWN / ACCESS BLOCKED**, not “persistent” or “manipulated.”
