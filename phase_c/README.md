# Phase C — Historical Access & Submission Pattern Audit

Continuation of Phase A/B for `https://thlotto.com/member/lottery/yeekee`.

**Status: complete for the permitted, publicly accessible scope.** Historical 88-round archives and cross-day comparison are ACCESS BLOCKED.

## Read first

- **`PHASE_C_FINAL_REPORT.md`** — full Thai report, findings, evidence, limitations.
- `HISTORICAL_AVAILABILITY.md` — 53 snapshot, 88-round archive, date filter, 404s, retention.
- `MASKED_ACCOUNT_PATTERN_AUDIT.md` — 16-round hash-only account patterns.
- `SUBMISSION_ORDERING_AUDIT.md` — 13/18 inversions, tie-break, row 16.
- `REA_EVIDENCE_VERIFICATION.md` — exact REA operations/evidence IDs.
- `STATISTICAL_VALIDITY_C.md` — predefined hypotheses and negative findings.

## Key numbers

| Metric | Value |
|---|---:|
| Completed rounds analyzed | 16 (periods 229–244, rounds 53–68) |
| Sanitized rows | 2,474 |
| Distinct masked hashes | 469 |
| Hashes in ≥2 rounds | 286 (61.0%) |
| Duplicate groups | 104 |
| Same-user duplicate groups | 94 (90.4%) |
| Same-second duplicate groups | 0 |
| Same-user permutation p | <1e-4 |
| +103/+119 burst rows | 1,526 (61.68%) |
| Row 16 in +119 s group | 16/16 |
| Row-16 random-position probability | ≈4.3e-9 |
| Ordering inversions (7 rounds) | 13 |
| Ordering inversions (16 rounds) | 18 (all +1 s) |
| Grid results at 18:58 / 19:23 / 20:55 / 21:30 / 23:49 / 00:00 | 51 / 53 / 59 / 62 / 71 / 72 |
| Oldest 88-round date verified | 2026-11-07 (current day only) |
| Oldest 264-round date verified (comparison only) | 2026-01-01 |

## Reproduce

```bash
cd phase_c
python3 scripts/build_c_dataset.py
python3 scripts/account_pattern_audit.py
```

Inputs are hash-only: `evidence/raw_rounds_hash/round_*.json` → `evidence/combined_events.csv`.

## Files

```text
phase_c/
├── HISTORICAL_AVAILABILITY.md
├── HISTORICAL_ACCESS_MATRIX.csv
├── MASKED_ACCOUNT_PATTERN_AUDIT.md
├── SUBMISSION_ORDERING_AUDIT.md
├── REA_EVIDENCE_VERIFICATION.md
├── STATISTICAL_VALIDITY_C.md
├── PHASE_C_FINAL_REPORT.md
├── c_round_summary.csv
├── c_ordering_inversions.csv
├── charts/
│   ├── list_71_results_2349.png
│   └── rea_round_249.png
├── scripts/
│   ├── build_c_dataset.py
│   ├── account_pattern_audit.py
│   └── collect_round_hash.js
└── evidence/
    ├── combined_events.csv
    ├── raw_rounds_hash/          (16 rounds, hash-only)
    ├── c_burst_overlap.csv
    ├── c_same_user_duplicates.csv
    ├── c_account_summary.csv
    └── c_account_patterns.json
```

## Caveats

- One lottery day only; cross-day persistence is UNTESTABLE.
- 88-round historical archive is unavailable; old period IDs return 404.
- Masked names can collide; 469 is a display-identifier count, not verified persons.
- `created_at` semantics and the internal ordering key remain UNKNOWN.
- No bets, no submissions, no authentication bypass, no private member data.

## Repository status

Files were added to `/Users/icy/reverse-lotto/phase_c` and staged with `git add`.
The environment blocked the final git commit step as a risky shell command, so the
commit/push must be completed by the user in the repository. No credentials or raw
masked usernames are included in the staged files.
