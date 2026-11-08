# Phase B — Investigation Index

Continuation of Phase A, focused on five unresolved anomalies.

**Status: complete.** No submissions, bets, or unauthorized access were performed. Phase A files were not modified.

## Read first

- **`PHASE_B_FINAL_REPORT.md`** — full Thai report, executive summary, verified facts vs hypotheses, evidence index.
- `01_submission_timeline.md` — why 98.91% of submissions appear after betting close.
- `02_timestamp_collision_analysis.md` — why 49–51 rows share a second; +103 s/+119 s bursts.
- `03_duplicate_number_analysis.md` — why 5-digit values repeat; same-user repeats.
- `04_polling_and_frontend_runtime.md` — resolution of the 60-second polling contradiction.
- `05_monte_carlo_audit.md` — independent audit of Phase A’s Monte Carlo.
- `statistical_validation.md` — effect sizes, CIs, multiple testing, power, leakage.
- `06_pre_cutoff_information_matrix.csv` — what is knowable before the cutoff.

## Key numbers

| Metric | Value |
|---|---:|
| Rounds reconstructed | 7 (periods 229–235, rounds 53–59) |
| Sanitized submissions | 1,097 |
| Submissions before betting close | 12 (1.09%) |
| Submissions after betting close | 1,085 (98.91%) |
| Submissions in final 20 s | 923 (84.14%) |
| Submissions in the two fixed bursts (+103 s, +119 s) | 692 (63.08%) |
| Duplicate entries / colliding pairs | 52 / 61 |
| Duplicate groups all-same-user | 39 of 44 |
| Duplicate groups all in one second | 0 of 44 |
| Detail-page list poll interval | 60,000 ms (measured) |
| Grid refresh boundary | 15 minutes (observed 21:00, 21:15, 21:30) |
| Phase A Monte Carlo p | 0.1208 (one RNG draw; unstable) |
| Phase A p across 100 seeds | mean 0.4816, 5–95% 0.033–0.954 |
| At-cutoff pool size | 0–5 rows (row 16 undefined) |

## Files

```
phase_b/
├── PHASE_B_FINAL_REPORT.md
├── 01_submission_timeline.md
├── 02_timestamp_collision_analysis.md
├── 03_duplicate_number_analysis.md
├── 04_polling_and_frontend_runtime.md
├── 05_monte_carlo_audit.md
├── statistical_validation.md
├── submission_timeline.csv          (per-round summary)
├── submission_timeline_events.csv   (1,097 per-row events)
├── timestamp_collisions.csv
├── number_frequency.csv
├── simulation_comparison.csv
├── duplicate_model_comparison.csv
├── frontend_timers.csv
├── runtime_network_timeline.csv
├── 06_pre_cutoff_information_matrix.csv
├── evidence_index.csv
├── submission_timing_distribution.png
├── timestamp_burst_analysis.png
├── duplicate_distribution.png
├── duplicate_simulation.py
├── monte_carlo_reproduction.py
├── charts/                     (same PNGs + generators)
├── scripts/                    (data builders, chart builders)
└── evidence/
    ├── raw_rounds/             (sanitized 229–235)
    ├── submission_events.csv   (1,097 rows)
    ├── round_summary.csv
    ├── per_second.csv
    ├── user_concentration.json
    ├── burst_user_overlap.json
    ├── partial_vs_final.csv
    ├── cross_round_overlap.csv
    └── …                       (see evidence_index.csv)
```

## Reproduce

```bash
cd /Users/icy/research/phase_b
python3 scripts/build_datasets.py        # rebuild from raw_rounds
python3 scripts/analysis_core.py         # duplicates, cross-round, pre-cutoff
python3 duplicate_simulation.py          # 5 null models, 20k sims each
python3 monte_carlo_reproduction.py      # Phase A reproduction + sensitivity
python3 scripts/precutoff_test.py        # pre-cutoff correlations and LOO test
python3 scripts/make_charts.py           # timing + duplicate charts
python3 scripts/make_burst_chart.py      # burst chart
```

## Important caveats

- Seven rounds from one evening are not enough for a multi-day statistical claim.
- The 53-result dataset is one day and has very low power for 3-digit tests.
- `created_at` semantics (creation vs acceptance vs DB commit) remain UNKNOWN.
- The cause of the +103 s/+119 s bursts remains a HYPOTHESIS.
- Grid refresh at 15-minute boundaries is inferred from three consecutive boundaries; the server mechanism is UNKNOWN.
- No pre-cutoff predictive relationship was validated.
