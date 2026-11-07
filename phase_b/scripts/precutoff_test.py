#!/usr/bin/env python3
"""Pre-cutoff predictive audit (n=7 rounds).

At the betting close, the public pool contains only 0-5 rows in the observed
rounds, so row 16 is undefined. This script still tests whether the partial
sum has any reproducible relationship with the final result, and compares a
leave-one-out predictor with the uniform baseline.

Outputs evidence/precutoff_predictive_stats.json.
"""

import csv
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
EVID = os.path.join(ROOT, "evidence")


def main():
    rows = list(csv.DictReader(open(os.path.join(EVID, "partial_vs_final.csv"))))
    for r in rows:
        for k in ("partial_n_at_close", "partial_sum", "final_sum", "final_result", "future_sum"):
            r[k] = int(r[k])

    p = np.array([r["partial_sum"] for r in rows], dtype=float)
    pmod = p % 100000
    f = np.array([r["final_sum"] for r in rows], dtype=float)
    fr = np.array([r["final_result"] % 100000 for r in rows], dtype=float)

    def corr(a, b):
        if a.std() == 0 or b.std() == 0:
            return None
        return float(np.corrcoef(a, b)[0, 1])

    rng = np.random.default_rng(20261107)

    def perm_p(a, b, observed, B=50000):
        cnt = 0
        for _ in range(B):
            perm = rng.permutation(b)
            r = abs(np.corrcoef(a, perm)[0, 1])
            if r >= abs(observed):
                cnt += 1
        return (cnt + 1) / (B + 1)

    c_raw = corr(p, fr)
    c_mod = corr(pmod, fr)
    p_raw = perm_p(p, fr, c_raw)
    p_mod = perm_p(pmod, fr, c_mod)

    # Leave-one-out: predict final result mod 100k as
    # (partial_sum + mean future_sum of the other rounds) mod 100k.
    errs = []
    top_hits = 0
    bottom_hits = 0
    for i, r in enumerate(rows):
        others = [x for j, x in enumerate(rows) if j != i]
        mean_future = float(np.mean([x["future_sum"] for x in others]))
        pred = int(round((r["partial_sum"] + mean_future) % 100000))
        actual = r["final_result"] % 100000
        errs.append(min(abs(pred - actual), 100000 - abs(pred - actual)))
        p5, a5 = f"{pred:05d}", f"{actual:05d}"
        top_hits += int(p5[-3:] == a5[-3:])
        bottom_hits += int(p5[:2] == a5[:2])

    out = {
        "n_rounds": len(rows),
        "partial_n_values": [r["partial_n_at_close"] for r in rows],
        "partial_row16_defined_at_cutoff": sum(1 for r in rows if r["partial_n_at_close"] >= 16),
        "corr_partial_sum_raw_vs_final_sum": corr(p, f),
        "corr_partial_sum_raw_vs_final_result_mod": c_raw,
        "corr_partial_sum_mod_vs_final_result_mod": c_mod,
        "perm_p_partial_sum_raw_vs_final_result": p_raw,
        "perm_p_partial_sum_mod_vs_final_result": p_mod,
        "loo_mean_circular_abs_error": float(np.mean(errs)),
        "loo_top3_hits": top_hits,
        "loo_bottom2_hits": bottom_hits,
        "uniform_baseline_mean_circular_abs_error_approx": 25000.0,
        "uniform_baseline_top3_rate": 1 / 1000,
        "uniform_baseline_bottom2_rate": 1 / 100,
        "note": "At cutoff only 0-5 public rows existed; row 16 was undefined in all 7 rounds. The partial sum is therefore not a usable input to the published rule.",
        "rows": rows,
    }
    with open(os.path.join(EVID, "precutoff_predictive_stats.json"), "w") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False)
    print(json.dumps({k: out[k] for k in out if k != "rows"}, indent=2))


if __name__ == "__main__":
    main()
