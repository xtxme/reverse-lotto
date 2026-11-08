#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p outputs
for script in parse_line_export parse_hourly_forecasts define_image_rules audit_hourly_provider backtest_image_rules pattern_discovery oos_validation audit_inputs hourly_sensitivity oos_comparisons build_reports; do
  python3 "REPRODUCIBLE_SCRIPTS/${script}.py" > "outputs/${script}.log" 2>&1
done
python3 REPRODUCIBLE_SCRIPTS/test_validation.py
