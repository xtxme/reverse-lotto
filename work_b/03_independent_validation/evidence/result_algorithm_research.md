# Result Algorithm Research

Priority section. The goal is to establish what is actually verifiable about the Yeekee result calculation, not to assert backend knowledge that the evidence does not support.

## 1. Published rule (OBSERVED)

From the site’s own “กติกา” (rules) modal, captured in an authorized session on 2026-11-07:

> ระบบจะให้สมาชิกทุกๆท่านร่วมส่งตัวเลขจำนวน 5 หลัก
> ทางบริษัทฯจะนำตัวเลขที่สมาชิกส่งเข้ามาทั้งหมดในรอบนั้นๆมารวมกัน แล้วเอาผลรวมที่ได้นำไปลบกับเลขลำดับที่ 16 ของรอบนั้น และจะนำผลที่ได้มาเป็นผลในการออกรางวัล

Translation:

> Every member submits a 5-digit number. The company sums all numbers submitted in that round, subtracts the number in the 16th position, and uses the difference as the result.

Worked example published by the site:

```
total              = 2,543,565
16th number        =    34,529
result             = 2,543,565 - 34,529 = 2,509,036
3-digit top prize  = 036
2-digit bottom     = 09
```

The example’s highlighting makes the digit mapping explicit: from the last five digits `09036`, the first two (`09`) are the bottom prize and the last three (`036`) are the top prize.

## 2. Formal statement

Let:

- `x_1 … x_n` be the submitted 5-digit numbers, interpreted as integers (`00000`…`99999`),
- `x_16` be the number displayed in row 16 of the round’s submission table (newest-first order),
- `n` be the number of submissions in the round.

Then:

```
R = Σ x_i − x_16
d = R mod 100000            # 0 … 99999, zero-padded to 5 digits
top3    = d mod 1000        # last three digits
bottom2 = floor(d / 1000)   # first two of the five digits
```

Equivalently, take the last five decimal digits of `R`; the leftmost two are `bottom2`, the rightmost three are `top3`.

The published text does not mention a modulo. It does not need to: only the last five digits are used for prizes, so reducing modulo 100000 is observationally equivalent for all non-negative `R`. For negative `R`, the behavior is UNKNOWN and was not observed.

## 3. Independent verification

A standalone Python verifier is provided at `evidence/reproducible_tests/verify_formula.py`. It reconstructs each round from the complete public submission list (usernames removed) and compares the computed sum, 16th number, raw result, top-3, and bottom-2 with the site’s published values.

```
$ python3 verify_formula.py
round/period 229: PASS (n=173, sum=9281577, 16th=80308,
                        result=9201269, top3=269, bottom2=01)
round/period 230: PASS (n=164, sum=7724164, 16th=62839,
                        result=7661325, top3=325, bottom2=61)
All observed cases are reproduced exactly by the published rule.
```

A third round (55 / period 231) was reconstructed in-browser from all 151 rows:

```
n = 151
sum = 7,422,657
16th = 58,470
R = 7,422,657 − 58,470 = 7,364,187
last five digits = 64187
top3 = 187   bottom2 = 64
```

The site displayed exactly `ผลรวมยิงเลข 7422657`, `เลขแถวที่ 16 58470`, `ผลรางวัล 7364187`, `สามตัวบน 187`, `สองตัวล่าง 64`.

### Verification table

| Round | Period | n | Σ x_i | x_16 | R | top3 | bottom2 | Site match |
|---|---|---|---|---|---|---|---|---|
| 53 | 229 | 173 | 9,281,577 | 80,308 | 9,201,269 | 269 | 01 | exact |
| 54 | 230 | 164 | 7,724,164 | 62,839 | 7,661,325 | 325 | 61 | exact |
| 55 | 231 | 151 | 7,422,657 | 58,470 | 7,364,187 | 187 | 64 | exact |

Classification: OBSERVED that the published values are exactly reproducible from the complete public lists using the published rule. INFERRED (strong) that this is the production calculation for these rounds. It is not proof of every backend side-effect (rounding, cancellation, refunds), but the arithmetic is not in doubt for the observed cases.

## 4. Alternative interpretations tested

| Alternative | Result | Verdict |
|---|---|---|
| Sum of unique numbers only | Would differ materially (duplicates are common) | Rejected by exact match on all rows |
| Sum of bet amounts, not numbers | Amounts are not 5-digit numbers and are not exposed | Rejected |
| Subtract the 16th **from the end** | Would subtract a different row | Rejected |
| Use the first five digits of `R` | `R` has 7 digits; example uses the last five | Rejected |
| `top3` = first three digits of `R` | Example: 250 for 2,509,036, but site says 036 | Rejected |
| `bottom2` = last two digits | Example: 36, but site says 09 | Rejected |
| Sum reduced modulo 100000 before subtraction | `(Σ mod 100000 − x16) mod 100000 ≡ (Σ − x16) mod 100000` | Equivalent, not distinguishable |
| Leading zeros treated as text | Integer sum reproduces the published sum exactly, including rows like `00753`, `03002`, `00000` | Rejected as text concatenation; integers confirmed |

## 5. The 16th number is a display-order position

The submission table is newest-first:

- Round 55: row 1 = `19:31:59`; row 16 = `19:31:59`; row 151 = `19:27:53` (earliest).
- Round 54: row 1 = `19:16:59`; row 164 = `19:13:35`.
- Round 53: row 1 = `19:01:59`; row 173 = `18:58:55`.

Therefore `x_16` is the 16th row in the newest-first table, not the 16th person to submit. In all three observed rounds it belonged to the final-second batch. The exact tie-break within a one-second batch is UNKNOWN, because the API does not expose a submission ID; the server’s ordering is authoritative.

This is an important nuance for anyone reimplementing the rule: you must reproduce the site’s row order, not chronological order.

Counter-test against the alternative:

| Round | Display row 16 | Result with display row 16 | 16th chronological | Result with that value | Published |
|---|---|---|---|---|---|
| 53 | 80,308 | **9,201,269** ✓ | 78,956 | 9,202,621 ✗ | 9,201,269 |
| 54 | 62,839 | **7,661,325** ✓ | 86,868 | 7,637,296 ✗ | 7,661,325 |

The chronological interpretation is therefore rejected by the published data. The rule uses the 16th row of the newest-first table.

## 6. When is the result determined?

The inputs are not final at betting close:

- The number-shooting window runs until `close_date + 2 minutes` (`closeDateYeekee` in the server payload; `expireTimeOfShootNumber = 120000` in client code).
- Submissions are accepted before betting close as well (earliest observed 65–127 seconds before close), and the pool continues to grow after close.
- In round 55, 146 of 151 submissions arrived at or after 19:30:00, i.e. at or after the betting close; only 5 existed before it.

Therefore the final `Σ x_i` and the final row-16 value are only fixed at `close + 2 minutes`. The result cannot be computed from public data before that time.

Classification: OBSERVED.

## 7. Is the rule fully determined before the round closes?

No. The rule is deterministic **given** the final submission set, but the final submission set is not known at betting close. The missing inputs are:

- submissions arriving between betting close and shoot close,
- which submission ends up in display row 16,
- any server-side normalization, cancellation, or refund behavior.

## 8. What would be needed to compute a future result in advance?

To compute the result for a future round before its betting close, one would need, at minimum:

1. the complete set of numbers that will be submitted up to `close + 2 minutes`,
2. the exact ordering/tie-break that determines row 16,
3. confirmation that no post-processing (cancellation, adjustment, rounding) occurs.

Items 1–3 are not publicly available before the fact. Item 1 is the decisive blocker: it includes submissions that have not happened yet. No amount of historical analysis can supply future submissions.

## 9. Edge cases and unknowns

| Case | Status |
|---|---|
| Fewer than 20 submissions → refund | Published, not observed (all three rounds had >150) |
| Negative `R` or underflow handling | UNKNOWN; not observed |
| Result with leading zeros (e.g. `01269`) | OBSERVED; zero-padded to 5 digits |
| Duplicate numbers | OBSERVED; each occurrence is summed separately |
| Number `00000` | OBSERVED in round 54; contributes 0 |
| Leading-zero numbers (`00753`) | OBSERVED; treated as integer 753 in the sum |
| Round cancellation (`is_cancel`) | Field exists; no cancelled round observed |
| Tie for 16th position | UNKNOWN; ordering is server-defined |
| “16th” changes during the window | Yes; row 16 can change while new submissions arrive |
| Server-side rounding/truncation beyond the last 5 digits | Not observed; exact match on three rounds |

## 10. Confidence

- The formula’s arithmetic: **high confidence** for observed rounds (exact reproduction of sum, 16th row, result, and both prizes from 488 total submissions across three rounds).
- The formula’s generality: **medium-high**; it is the site’s own published rule and matches every observed case, but the backend could contain additional steps that happen to be identity on these samples.
- Any claim about the backend language, database, or code path: **not established** by the client evidence.

## 11. Implication for an educational simulator

A faithful offline simulator can be built from the published rule plus the observed display semantics:

1. accept a list of 5-digit numbers,
2. order them newest-first (or let the simulator define a documented order),
3. sum all values,
4. subtract the 16th row,
5. take the last five digits,
6. output `bottom2` and `top3`.

For historical replay, the simulator can reproduce any round for which the full submission list is available. For hypothetical rounds, it must clearly label the submission order as synthetic, because the real tie-break is unknown.

