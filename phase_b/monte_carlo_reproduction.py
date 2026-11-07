#!/usr/bin/env python3
"""
Independent reproduction and sensitivity audit of the Phase A Monte Carlo.

Phase A claimed:
  pool = 337 numbers (rounds 229 + 230)
  draws/round = 168
  iterations = 20,000
  result = (sum(draws) - draws[15]) mod 100000
  last-digit chi-square = 14.044, p = 0.1208

This script:
  1. reproduces that exact configuration and asserts the statistic;
  2. varies pool, pool size, position-16 rule, seed, and iterations;
  3. reports the Monte Carlo p-value distribution under the simulation null;
  4. writes simulation_comparison.csv and evidence/mc_pvalue_distribution.csv.

The simulation is a model of the arithmetic, not a model of the live process.
It does not include timestamps, newest-first ordering, or same-user repeats.
"""

import csv
import json
import math
import os
import random
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))   # phase_b/
ROOT = HERE
EVID = os.path.join(ROOT, "evidence")
PHASE_A = os.path.join(os.path.dirname(ROOT), "evidence", "sanitized_observations")


def chi2_sf(x, df):
    """Regularized upper incomplete gamma Q(df/2, x/2), same as Phase A."""
    if x <= 0:
        return 1.0
    a = df / 2.0
    x2 = x / 2.0
    if x2 < a + 1:
        ap = a
        s = 1.0 / a
        d = s
        for _ in range(1000):
            ap += 1
            d *= x2 / ap
            s += d
            if abs(d) < abs(s) * 1e-12:
                break
        return 1.0 - s * math.exp(-x2 + a * math.log(x2) - math.lgamma(a))
    b = x2 + 1 - a
    c = 1e300
    d = 1.0 / b
    h = d
    for i in range(1, 1000):
        an = -i * (i - a)
        b += 2
        d = an * d + b
        if abs(d) < 1e-300:
            d = 1e-300
        c = b + an / c
        if abs(c) < 1e-300:
            c = 1e-300
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1) < 1e-12:
            break
    return math.exp(-x2 + a * math.log(x2) - math.lgamma(a)) * h


def load_numbers():
    pools = {}
    for rid in (229, 230):
        path = os.path.join(PHASE_A, f"round_{rid}_numbers.csv")
        with open(path) as f:
            pools[str(rid)] = [int(r["number"]) for r in csv.DictReader(f)]
    # Phase B 7-round pool from the sanitized event CSV
    all_nums = []
    with open(os.path.join(EVID, "submission_events.csv")) as f:
        for r in csv.DictReader(f):
            all_nums.append(int(r["number"]))
    pools["all7"] = all_nums
    pools["229+230"] = pools["229"] + pools["230"]
    return pools


def reproduce_phase_a_exact(pool):
    """
    Phase A's RNG state at test 6 was advanced by test 2 (20,000 x 53
    randrange(100) calls). Replaying that consumption reproduces the
    published counts exactly. A fresh seed does NOT.
    """
    random.seed(20261107)
    for _ in range(20000):
        _ = [random.randrange(100) for _ in range(53)]  # test 2 consumption
    counts = [0] * 10
    for _ in range(20000):
        draw = [random.choice(pool) for _ in range(168)]
        total = sum(draw) - draw[15]
        counts[(total % 100000) % 10] += 1
    exp = 20000 / 10.0
    chi2 = sum((c - exp) ** 2 / exp for c in counts)
    return chi2, chi2_sf(chi2, 9), counts


def simulate_python_random(pool, n, rule, seed, iterations):
    """Bit-for-bit reproduction path using Python's random module (Phase A)."""
    random.seed(seed)
    counts = [0] * 10
    for _ in range(iterations):
        draw = [random.choice(pool) for _ in range(n)]
        total = sum(draw)
        if rule == "chrono16":
            sub = draw[15]
        elif rule == "last16":
            sub = draw[-16]
        elif rule == "last":
            sub = draw[-1]
        else:
            sub = draw[random.randrange(n)]
        counts[(total - sub) % 100000 % 10] += 1
    exp = iterations / 10.0
    chi2 = sum((c - exp) ** 2 / exp for c in counts)
    return chi2, chi2_sf(chi2, 9), counts


def simulate(pool, n, rule, seed, iterations):
    rng = np.random.default_rng(seed)
    arr = np.asarray(pool, dtype=np.int64)
    draws = rng.choice(arr, size=(iterations, n), replace=True)
    sums = draws.sum(axis=1)
    if rule == "chrono16":
        sub = draws[:, 15]
    elif rule == "last16":
        sub = draws[:, -16]
    elif rule == "last":
        sub = draws[:, -1]
    elif rule == "random_row":
        sub = draws[np.arange(iterations), rng.integers(0, n, size=iterations)]
    else:
        raise ValueError(rule)
    results = (sums - sub) % 100000
    counts = np.bincount(results % 10, minlength=10).astype(float)
    exp = iterations / 10.0
    chi2 = float(((counts - exp) ** 2 / exp).sum())
    return chi2, chi2_sf(chi2, 9), counts.astype(int).tolist()


def main():
    pools = load_numbers()
    rows = []

    # 1. Exact Phase A reproduction (replay the RNG state at test 6)
    chi2, p, counts = reproduce_phase_a_exact(pools["229+230"])
    print("Phase A reproduction (replayed RNG state):")
    print(f"  chi2={chi2:.3f} p={p:.4f} counts={counts}")
    print("  expected: chi2=14.044 p=0.1208")
    assert abs(chi2 - 14.044) < 1e-3, chi2
    assert abs(p - 0.1208) < 1e-4, p

    # 2. Sensitivity grid
    configs = []
    for pool_name in ("229", "230", "229+230", "all7"):
        for n in (151, 164, 168, 173):
            for rule in ("chrono16", "last16", "last", "random_row"):
                configs.append((pool_name, n, rule))

    for i, (pool_name, n, rule) in enumerate(configs):
        chi2, p, counts = simulate(pools[pool_name], n, rule, 20261107, 20000)
        rows.append({
            "config_id": i + 1, "pool": pool_name, "pool_size": len(pools[pool_name]),
            "n_draws": n, "sixteenth_rule": rule, "seed": 20261107,
            "iterations": 20000, "chi2": round(chi2, 4), "p_value": round(p, 6),
            **{f"digit_{d}": counts[d] for d in range(10)},
        })

    with open(os.path.join(ROOT, "simulation_comparison.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print(f"\nwrote simulation_comparison.csv ({len(rows)} configurations)")

    # 3. p-value distribution across seeds (main configuration)
    ps = []
    for seed in range(1, 101):
        _, p, _ = simulate(pools["229+230"], 168, "chrono16", seed, 20000)
        ps.append(p)
    ps = np.array(ps)
    print("\np-value distribution across 100 seeds (main config):")
    print(f"  mean={ps.mean():.4f} median={np.median(ps):.4f} "
          f"5th={np.quantile(ps,0.05):.4f} 95th={np.quantile(ps,0.95):.4f} "
          f"P(p<0.05)={(ps<0.05).mean():.3f}")
    with open(os.path.join(EVID, "mc_pvalue_distribution.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["seed", "p_value"])
        for seed, p in enumerate(ps, 1):
            w.writerow([seed, round(float(p), 6)])

    # 4. Larger iteration stability for the main configuration
    chi2_big, p_big, counts_big = simulate(pools["229+230"], 168, "chrono16", 20261107, 200000)
    print("\n200,000-iteration stability:")
    print(f"  chi2={chi2_big:.3f} p={p_big:.4f} counts={counts_big}")

    # 5. Summary by rule across all pools/n
    print("\nmean p-value by sixteenth rule (all pools/n, seed fixed):")
    for rule in ("chrono16", "last16", "last", "random_row"):
        vals = [r["p_value"] for r in rows if r["sixteenth_rule"] == rule]
        print(f"  {rule}: mean={np.mean(vals):.4f} min={min(vals):.4f} max={max(vals):.4f}")


if __name__ == "__main__":
    main()
