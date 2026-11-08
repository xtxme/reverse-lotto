#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 REPRODUCIBLE_SCRIPTS/parse_line_export.py
python3 REPRODUCIBLE_SCRIPTS/parse_hourly_forecasts.py
python3 REPRODUCIBLE_SCRIPTS/audit_hourly_provider.py
python3 REPRODUCIBLE_SCRIPTS/define_image_rules.py
python3 REPRODUCIBLE_SCRIPTS/backtest_image_rules.py
python3 REPRODUCIBLE_SCRIPTS/pattern_discovery.py
python3 REPRODUCIBLE_SCRIPTS/oos_validation.py
