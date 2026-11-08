# work_b — Independent Audit of Lottery Screenshot Rules and Hourly Forecasts

This folder is deliberately **outside** the `reverse-lotto` repository. It contains an independent,
reproducible audit of:

- 87 trading days of LINE-exported Yeekee results (2026-08-13 → 2026-11-07);
- 886 hourly "เลขนิ่ง" forecast posts (86 daily tables);
- 17 numbered rules in the first screenshot and the number sets in the other two screenshots;
- the public/authorized THLotto result pages used to verify the LINE data.

## Headline findings

| Question | Answer |
|---|---|
| Any screenshot rule beats random? | **No.** All 17 primary rules are null; smallest primary binomial p = 0.193; all BH q ≥ 0.974. |
| Image 1 set after a bottom double? | 49/730 = 6.71% vs 7.0% baseline. |
| Image 2 set after 69 / 65 / 69→65? | 6.67% / 8.97% / 7.84% vs 9.0%; the 69→65 sequence occurred once. |
| Hourly provider skill? | Bottom null (56.57% vs 56.81%, p = 0.60). Top +2.39 pp, nominal p ≈ 0.019, but p ≈ 0.059 after 3-outcome correction and not stable over time. |
| Reproducible patterns? | None. 76 tests, 4 nominal p < 0.05, **0 survive BH** (smallest q = 0.805). |
| Out-of-sample? | No model beats uniform. Test log loss: 4.6117–4.6215 vs uniform 4.60517. |

## Privacy

`data/line_export_raw.txt` is a private LINE chat export. It must **never** be committed or uploaded.
`.gitignore` excludes `data/` and `outputs/`. The public report files contain only aggregate statistics
and the two public group handles needed to describe the forecast table; no phone numbers, account
credentials, or private messages are included.

## Layout

```
work_b/
├── DATA_QUALITY_REPORT.md
├── DEDUPLICATED_RESULTS.csv
├── FIRST_SEEN_FORECASTS.csv
├── IMAGE_RULE_DEFINITIONS.csv
├── IMAGE_RULE_BACKTEST.csv
├── HOURLY_FORECAST_AUDIT.md
├── PATTERN_DISCOVERY_REPORT.md
├── OUT_OF_SAMPLE_VALIDATION.md
├── FINAL_INDEPENDENT_REPORT_TH.md
├── REPRODUCIBLE_SCRIPTS/
│   ├── parse_line_export.py
│   ├── parse_hourly_forecasts.py
│   ├── audit_hourly_provider.py
│   ├── define_image_rules.py
│   ├── backtest_image_rules.py
│   ├── pattern_discovery.py
│   ├── oos_validation.py
│   ├── verify_against_site.py
│   └── verify_all_site_days.py
├── data/                 # private; not for publication
└── outputs/              # intermediate CSV/JSON; local
```

## Reproduce

```bash
cd work_b
python3 -m pip install -r requirements.txt
python3 REPRODUCIBLE_SCRIPTS/parse_line_export.py
python3 REPRODUCIBLE_SCRIPTS/parse_hourly_forecasts.py
python3 REPRODUCIBLE_SCRIPTS/audit_hourly_provider.py
python3 REPRODUCIBLE_SCRIPTS/define_image_rules.py
python3 REPRODUCIBLE_SCRIPTS/backtest_image_rules.py
python3 REPRODUCIBLE_SCRIPTS/pattern_discovery.py
python3 REPRODUCIBLE_SCRIPTS/oos_validation.py
```

`verify_against_site.py` and `verify_all_site_days.py` require the authorized result-page captures in
`data/site_days/`; they do not perform any login and contain no credentials.

## Method notes

- Trading day, not calendar day: rounds 1–72 are on the trading date, rounds 73–88 after midnight.
- Leading zeros are preserved as strings.
- Every result row keeps its source line in the export.
- The hourly forecast is evaluated only if its **first appearance** was before the first draw of the hour.
- The two main forecast accounts repost the **same** daily table; inference treats the day as the unit,
  uses within-day permutation and a day bootstrap.
- "หมา" in the screenshot is treated as **หาม** (ABA top-3 pattern), based on the published formula text;
  "พี่น้อง" is the canonical 10-pair set 01,12,23,34,45,56,67,78,89,90.
- The two screenshots' rules have no date, author, or formal definition. Even a positive backtest would
  not be evidence of a prospective prediction.

## No betting advice

This is a statistical audit. It does not provide lottery numbers, betting advice, or any guarantee of
winning. A +2.4 pp fluctuation is within the noise of this dataset and is far below any plausible
house margin.
