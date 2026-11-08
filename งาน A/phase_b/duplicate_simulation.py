#!/usr/bin/env python3
"""
Investigation 3 — duplicate 5-digit numbers (v2).

Definitions
-----------
duplicate entry : a row whose number is not the first occurrence in its round.
                  duplicate_entries = n - unique_within_round.
colliding pair  : an unordered pair of rows with the same number.
                  colliding_pairs = sum_v C(freq_v, 2).

Null models
-----------
A. Uniform iid over 00000..99999.
B. Finite-pool resampling from the other six rounds (can only generate numbers
   already seen; this over-predicts duplicates and is a bounding sensitivity,
   not a credible generative model).
C. Smoothed empirical: mixture of B and a uniform draw, so unseen numbers are
   possible. epsilon is the uniform mixing weight.
D. Positional digit model: estimate the distribution of each of the five digit
   positions from the other six rounds, then draw each position independently.
   This can generate any number and preserves marginal digit preferences.
E. Same-user repeat model: supported by the aggregate evidence (44 duplicate
   groups, 0 all-same-second, mostly one user per group) but not simulated
   row-by-row because the sanitized dataset intentionally omits per-row user
   links. Retaining user hashes would be required for a faithful model.

Outputs
-------
duplicate_model_comparison.csv
evidence/duplicate_aggregate_models.json
evidence/cross_round_overlap.csv
evidence/pattern_frequencies.csv
evidence/recurring_tail.csv
"""

import csv
import json
import math
import os
from collections import Counter, defaultdict

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = HERE
EVID = os.path.join(ROOT, "evidence")
ROUNDS = list(range(53, 60))
B = 20000
RNG = np.random.default_rng(20261107)


def load_rounds():
    by = defaultdict(list)
    with open(os.path.join(EVID, "submission_events.csv")) as f:
        for r in csv.DictReader(f):
            by[int(r["round"])].append(int(r["number"]))
    return {r: by[r] for r in ROUNDS}


def n_unique_and_pairs(draws):
    Bn, n = draws.shape
    s = np.sort(draws, axis=1)
    unique = 1 + (np.diff(s, axis=1) != 0).sum(axis=1)
    pairs = np.empty(Bn, dtype=np.int64)
    for i in range(Bn):
        _, c = np.unique(s[i], return_counts=True)
        pairs[i] = int((c * (c - 1) // 2).sum())
    return unique, pairs


def sim_uniform(n):
    return n_unique_and_pairs(RNG.integers(0, 100000, size=(B, n), dtype=np.int64))


def sim_empirical(pool, n):
    arr = np.asarray(pool, dtype=np.int64)
    return n_unique_and_pairs(RNG.choice(arr, size=(B, n), replace=True))


def sim_smoothed(pool, n, eps):
    arr = np.asarray(pool, dtype=np.int64)
    emp = RNG.choice(arr, size=(B, n), replace=True)
    uni = RNG.integers(0, 100000, size=(B, n), dtype=np.int64)
    mask = RNG.random((B, n)) < eps
    draws = np.where(mask, uni, emp)
    return n_unique_and_pairs(draws)


def positional_probs(pool):
    digits = np.array([[int(f"{x:05d}"[p]) for p in range(5)] for x in pool])  # (m,5)
    probs = []
    for p in range(5):
        c = np.bincount(digits[:, p], minlength=10).astype(float)
        probs.append(c / c.sum())
    return probs


def sim_positional(probs, n):
    digits = np.stack([RNG.choice(10, size=(B, n), p=probs[p]) for p in range(5)], axis=2)
    nums = (digits[:, :, 0] * 10000 + digits[:, :, 1] * 1000 +
            digits[:, :, 2] * 100 + digits[:, :, 3] * 10 + digits[:, :, 4])
    return n_unique_and_pairs(nums)


def p_upper(sim, obs):
    return float((np.sum(sim >= obs) + 1) / (len(sim) + 1))


def p_lower(sim, obs):
    return float((np.sum(sim <= obs) + 1) / (len(sim) + 1))


def main():
    rounds = load_rounds()
    comparison = []

    for r in ROUNDS:
        nums = rounds[r]
        n = len(nums)
        c = Counter(nums)
        obs_unique = len(c)
        obs_pairs = sum(v * (v - 1) // 2 for v in c.values())
        pool_other = [x for rr in ROUNDS if rr != r for x in rounds[rr]]
        pool_all = [x for rr in ROUNDS for x in rounds[rr]]
        probs = positional_probs(pool_other)

        models = {
            "A_uniform": sim_uniform(n),
            "B_finite_pool_other": sim_empirical(pool_other, n),
            "C_smoothed_eps0.5": sim_smoothed(pool_other, n, 0.5),
            "C_smoothed_eps0.9": sim_smoothed(pool_other, n, 0.9),
            "D_positional_digits": sim_positional(probs, n),
            "E_pooled_in_sample": sim_empirical(pool_all, n),
        }
        for label, (u, p) in models.items():
            comparison.append({
                "round": r, "period_id": 176 + r, "n": n, "model": label,
                "sim_mean_unique": round(float(u.mean()), 2),
                "sim_unique_p2.5": int(np.quantile(u, 0.025)),
                "sim_unique_p97.5": int(np.quantile(u, 0.975)),
                "observed_unique": obs_unique,
                "p_unique_le_obs": round(p_lower(u, obs_unique), 5),
                "sim_mean_pairs": round(float(p.mean()), 2),
                "sim_pairs_p97.5": int(np.quantile(p, 0.975)),
                "observed_pairs": obs_pairs,
                "p_pairs_ge_obs": round(p_upper(p, obs_pairs), 5),
            })

    with open(os.path.join(ROOT, "duplicate_model_comparison.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(comparison[0].keys()))
        w.writeheader(); w.writerows(comparison)

    # Aggregate joint simulations
    def joint(models):
        total_dup = np.zeros(B, dtype=np.int64)
        total_pairs = np.zeros(B, dtype=np.int64)
        for r in ROUNDS:
            n = len(rounds[r])
            pool_other = [x for rr in ROUNDS if rr != r for x in rounds[rr]]
            if models == "A":
                u, p = sim_uniform(n)
            elif models == "B":
                u, p = sim_empirical(pool_other, n)
            elif models == "C0.5":
                u, p = sim_smoothed(pool_other, n, 0.5)
            elif models == "C0.9":
                u, p = sim_smoothed(pool_other, n, 0.9)
            else:
                u, p = sim_positional(positional_probs(pool_other), n)
            total_dup += (n - u)
            total_pairs += p
        return total_dup, total_pairs

    obs_total_dup = sum(len(rounds[r]) - len(set(rounds[r])) for r in ROUNDS)
    obs_total_pairs = sum(sum(v * (v - 1) // 2 for v in Counter(rounds[r]).values()) for r in ROUNDS)
    agg = {}
    for label in ("A", "B", "C0.5", "C0.9", "D"):
        d, p = joint(label)
        agg[label] = {
            "obs_total_duplicate_entries": obs_total_dup,
            "sim_mean_duplicate_entries": round(float(d.mean()), 2),
            "sim_p2.5_duplicate_entries": int(np.quantile(d, 0.025)),
            "sim_p97.5_duplicate_entries": int(np.quantile(d, 0.975)),
            "p_dup_ge_obs": round(p_upper(d, obs_total_dup), 5),
            "obs_total_colliding_pairs": obs_total_pairs,
            "sim_mean_colliding_pairs": round(float(p.mean()), 2),
            "sim_p97.5_colliding_pairs": int(np.quantile(p, 0.975)),
            "p_pairs_ge_obs": round(p_upper(p, obs_total_pairs), 5),
        }
    with open(os.path.join(EVID, "duplicate_aggregate_models.json"), "w") as f:
        json.dump(agg, f, indent=2)

    # Cross-round overlap
    overlap = []
    sets = {r: set(rounds[r]) for r in ROUNDS}
    for i, a in enumerate(ROUNDS):
        for b in ROUNDS[i + 1:]:
            inter = len(sets[a] & sets[b])
            exp = len(rounds[a]) * len(rounds[b]) / 100000.0
            p = 1.0 - sum(math.exp(-exp) * exp ** k / math.factorial(k) for k in range(inter))
            overlap.append({"round_a": a, "round_b": b, "n_a": len(rounds[a]), "n_b": len(rounds[b]),
                            "observed_intersection": inter, "uniform_expected": round(exp, 4),
                            "ratio": round(inter / exp, 2) if exp else None,
                            "poisson_p_upper": round(min(1.0, max(0.0, p)), 6)})
    with open(os.path.join(EVID, "cross_round_overlap.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(overlap[0].keys()))
        w.writeheader(); w.writerows(overlap)
    obs_inter = sum(x["observed_intersection"] for x in overlap)
    exp_inter = sum(x["uniform_expected"] for x in overlap)
    print(f"pairwise overlap: observed {obs_inter}, uniform expected {exp_inter:.2f}, ratio {obs_inter/exp_inter:.1f}x")

    # Pattern frequencies vs uniform
    all_nums = [x for r in ROUNDS for x in rounds[r]]
    n = len(all_nums)
    padded = [f"{x:05d}" for x in all_nums]
    all_same = sum(1 for s in padded if len(set(s)) == 1)
    four_same = sum(1 for s in padded if max(Counter(s).values()) == 4)
    palindrome = sum(1 for s in padded if s == s[::-1])
    at_least_pair = sum(1 for s in padded if max(Counter(s).values()) >= 2)
    exp_all_same = n * 10 / 100000
    exp_four_same = n * (10 * 9 * 5) / 100000
    exp_palindrome = n * 100 / 100000
    p_distinct = 1.0
    for i in range(5):
        p_distinct *= (10 - i) / 10
    exp_pair = n * (1 - p_distinct)
    patterns = [
        {"pattern": "all_five_same", "observed": all_same, "uniform_expected": round(exp_all_same, 3),
         "ratio": round(all_same / exp_all_same, 1) if exp_all_same else None},
        {"pattern": "exactly_four_same", "observed": four_same, "uniform_expected": round(exp_four_same, 3),
         "ratio": round(four_same / exp_four_same, 1) if exp_four_same else None},
        {"pattern": "palindrome", "observed": palindrome, "uniform_expected": round(exp_palindrome, 3),
         "ratio": round(palindrome / exp_palindrome, 1) if exp_palindrome else None},
        {"pattern": "at_least_one_repeated_digit", "observed": at_least_pair, "uniform_expected": round(exp_pair, 3),
         "ratio": round(at_least_pair / exp_pair, 2) if exp_pair else None},
    ]
    with open(os.path.join(EVID, "pattern_frequencies.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(patterns[0].keys()))
        w.writeheader(); w.writerows(patterns)

    # Recurring-number tail (zero-padded display)
    total = Counter(all_nums)
    mu = n / 100000.0
    top = total.most_common(10)
    tail = []
    for num, k in top:
        p = 1.0 - sum(math.exp(-mu) * mu ** j / math.factorial(j) for j in range(k))
        tail.append({"number": f"{num:05d}", "count": k, "uniform_expected": round(mu, 5),
                     "poisson_p_upper": float(p), "family_wise_p_upper": float(min(1.0, p * 100000))})
    with open(os.path.join(EVID, "recurring_tail.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(tail[0].keys()))
        w.writeheader(); w.writerows(tail)

    # Console
    print("\nper-round model comparison")
    for x in comparison:
        print(f"  r{x['round']:>2} {x['model']:<24} obs_uniq={x['observed_unique']:>3} "
              f"sim_uniq={x['sim_mean_unique']:>6} p(uniq<=obs)={x['p_unique_le_obs']:.3f} "
              f"obs_pairs={x['observed_pairs']:>3} sim_pairs={x['sim_mean_pairs']:>6} p(pairs>=obs)={x['p_pairs_ge_obs']:.3f}")
    print("\naggregate")
    for k, v in agg.items():
        print(" ", k, v)
    print("\npatterns")
    for x in patterns:
        print(" ", x)
    print("\nrecurring tail")
    for x in tail:
        print(" ", x)


if __name__ == "__main__":
    main()
