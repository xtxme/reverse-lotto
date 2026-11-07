#!/usr/bin/env python3
"""
Preliminary randomness / predictive-feasibility tests for observed Yeekee results.

Input: evidence/sanitized_observations/results_2026-11-07.json (53 published rounds).
This is a small sample. The script reports effect sizes and p-values, and
explicitly labels results as underpowered where applicable.

Tests
  1. Last-digit uniformity (chi-square, 10 bins).
  2. Bottom-2 uniformity via exact multinomial Monte Carlo (100 bins).
  3. Runs test on top-3 values above/below the median (Wald-Wolfowitz).
  4. Lag-1 Pearson autocorrelation of the 5-digit outcome.
  5. Simple "hot digit" heuristic evaluated out-of-sample against a uniform
     baseline (1/10 for a single digit).
  6. Monte Carlo of the published arithmetic using the empirical submission
     distribution from rounds 229/230, to see whether non-uniform human
     submissions survive the sum/subtract/mod-100000 transform.
"""

import json
import math
import os
import random
import statistics
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "sanitized_observations", "results_2026-11-07.json")

random.seed(20261107)


def chi_square_uniform(counts, expected):
    return sum((c - expected) ** 2 / expected for c in counts)


def chi2_sf(x, df):
    """Survival function for chi-square via regularized upper incomplete gamma."""
    # Numerical Recipes gammq
    if x <= 0:
        return 1.0
    a = df / 2.0
    x2 = x / 2.0
    if x2 < a + 1:
        # series
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
    # continued fraction
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


def runs_test(binary):
    n1 = sum(binary)
    n2 = len(binary) - n1
    runs = 1 + sum(1 for i in range(1, len(binary)) if binary[i] != binary[i - 1])
    mu = 2 * n1 * n2 / (n1 + n2) + 1
    var = 2 * n1 * n2 * (2 * n1 * n2 - n1 - n2) / ((n1 + n2) ** 2 * (n1 + n2 - 1))
    z = (runs - mu) / math.sqrt(var)
    p = 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))
    return runs, mu, z, p


def main():
    d = json.load(open(DATA, encoding="utf-8"))
    rows = d["results"]
    n = len(rows)
    tops = [r["top"] for r in rows]
    bottoms = [r["bottom"] for r in rows]
    full = [int(t + b) for t, b in zip(tops, bottoms)]  # 5-digit outcome

    print(f"n = {n} rounds (2026-11-07, rounds 1-{n})")

    # 1. last digit
    last = [int(t) % 10 for t in tops]
    c = Counter(last)
    counts = [c.get(i, 0) for i in range(10)]
    exp = n / 10
    x2 = chi_square_uniform(counts, exp)
    p = chi2_sf(x2, 9)
    print("\n[1] Last-digit uniformity (10 bins)")
    print("    counts:", counts)
    print(f"    chi2 = {x2:.3f}, df=9, p = {p:.4f}  (underpowered: expected {exp:.1f}/bin)")

    # 2. bottom-2 Monte Carlo
    c2 = Counter(bottoms)
    obs_max = max(c2.values())
    obs_distinct = len(c2)
    trials = 20000
    max_ge = 0
    distinct_le = 0
    for _ in range(trials):
        sim = Counter(str(random.randrange(100)).zfill(2) for _ in range(n))
        if max(sim.values()) >= obs_max:
            max_ge += 1
        if len(sim) <= obs_distinct:
            distinct_le += 1
    print("\n[2] Bottom-2 (100 bins) exact-style Monte Carlo, 20k draws")
    print(f"    observed distinct = {obs_distinct}/100, max bin = {obs_max}")
    print(f"    P(max bin >= observed | uniform) = {max_ge/trials:.3f}")
    print(f"    P(distinct <= observed | uniform) = {distinct_le/trials:.3f}")

    # 3. runs test on top-3 above/below median
    med = statistics.median(int(t) for t in tops)
    binary = [1 if int(t) > med else 0 for t in tops]
    runs, mu, z, p_runs = runs_test(binary)
    print("\n[3] Runs test, top-3 above/below median")
    print(f"    median = {med}, runs = {runs}, expected = {mu:.2f}, z = {z:.3f}, p = {p_runs:.4f}")

    # 4. lag-1 autocorrelation
    m = statistics.mean(full)
    var = sum((x - m) ** 2 for x in full)
    ac = sum((full[i] - m) * (full[i + 1] - m) for i in range(n - 1)) / var
    se = 1 / math.sqrt(n)
    print("\n[4] Lag-1 autocorrelation of 5-digit outcome")
    print(f"    r = {ac:.4f}, SE ~ {se:.4f}, approx 95% band = +/-{1.96*se:.4f}")

    # 5. out-of-sample hot-digit heuristic
    train, test = last[:30], last[30:]
    hot = Counter(train).most_common(1)[0][0]
    hits = sum(1 for x in test if x == hot)
    expected = len(test) / 10
    print("\n[5] 'Hot last digit' heuristic (train rounds 1-30, test 31-53)")
    print(f"    hot digit = {hot}, hits = {hits}/{len(test)}, expected = {expected:.1f}")
    # exact binomial two-sided-ish upper tail
    p_ge = sum(math.comb(len(test), k) * 0.1 ** k * 0.9 ** (len(test) - k)
               for k in range(hits, len(test) + 1))
    print(f"    P(X >= hits | p=0.1) = {p_ge:.3f}")

    # 6. Monte Carlo of published arithmetic with empirical pool
    pool = []
    for f in ("round_229_numbers.csv", "round_230_numbers.csv"):
        path = os.path.join(HERE, "..", "sanitized_observations", f)
        if os.path.exists(path):
            with open(path) as fh:
                for line in fh:
                    line = line.strip()
                    if line and not line.startswith("seq"):
                        parts = line.split(",")
                        if len(parts) == 2 and parts[1].isdigit():
                            pool.append(int(parts[1]))
    if len(pool) >= 50:
        sims = []
        k = 168
        for _ in range(20000):
            draw = [random.choice(pool) for _ in range(k)]
            s = sum(draw) - draw[15]
            sims.append(s % 100000)
        last_digits = Counter(x % 10 for x in sims)
        exp = len(sims) / 10
        x2s = chi_square_uniform([last_digits.get(i, 0) for i in range(10)], exp)
        print("\n[6] Monte Carlo of published formula with empirical submission pool")
        print(f"    pool size = {len(pool)}, draws/round = {k}, simulations = {len(sims)}")
        print(f"    last-digit counts = {[last_digits.get(i,0) for i in range(10)]}")
        print(f"    chi2 = {x2s:.3f}, df=9, p = {chi2_sf(x2s,9):.4f} (expect ~uniform)")

    print("\nInterpretation: with n=53, none of these tests can establish or refute")
    print("predictability at the 3-digit level. Any p-value near 0.05 here is")
    print("exploratory and must be replicated on unseen future rounds.")


if __name__ == "__main__":
    main()
