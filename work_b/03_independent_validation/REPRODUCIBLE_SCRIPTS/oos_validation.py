#!/usr/bin/env python3
"""
Chronological train / validation / test evaluation of simple next-bottom2
models.  Nothing from validation or test is used to fit a model; validation
is used only to choose the smoothing strength.  Test is evaluated once.

Metrics: multi-class log loss (lower is better), Brier score, top-1 accuracy.
Baselines: uniform 1/100 and the training marginal.
"""
from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
RNG = np.random.default_rng(20261108)


def load_pairs():
    rows = list(csv.DictReader(open(OUT / "results_dedup_independent.csv", encoding="utf-8-sig")))
    rows.sort(key=lambda r: (r["trading_day"], int(r["round"])))
    pairs = []
    for a, b in zip(rows, rows[1:]):
        if a["trading_day"] == b["trading_day"] and int(b["round"]) == int(a["round"]) + 1:
            pairs.append({"day": a["trading_day"], "a": a, "b": b})
    return pairs


def days_split(pairs):
    days = sorted({p["day"] for p in pairs})
    n = len(days)
    train_days = set(days[: int(0.6 * n)])
    val_days = set(days[int(0.6 * n) : int(0.8 * n)])
    test_days = set(days[int(0.8 * n) :])
    return train_days, val_days, test_days, days


def state_key(pair, kind):
    a = pair["a"]
    if kind == "prev_bottom2":
        return a["bottom2"]
    if kind == "prev_lastdigit":
        return a["bottom2"][-1]
    if kind == "prev_tensdigit":
        return a["bottom2"][0]
    if kind == "prev_double":
        return "double" if a["bottom2"][0] == a["bottom2"][1] else "not"
    if kind == "prev_sum_bucket":
        s = sum(map(int, a["bottom2"]))
        return "0-4" if s <= 4 else "5-9" if s <= 9 else "10-13" if s <= 13 else "14-18"
    if kind == "prev_top_last":
        return a["top3"][-1]
    if kind == "prev_pair_last":
        return a["top3"][-1] + a["bottom2"][-1]
    raise ValueError(kind)


def fit(train, kind, alpha):
    marginal = Counter(p["b"]["bottom2"] for p in train)
    n = sum(marginal.values())
    p0 = {f"{i:02d}": (marginal.get(f"{i:02d}", 0) + 1.0) / (n + 100.0) for i in range(100)}
    if kind is None:
        return p0, None
    cond = defaultdict(Counter)
    for p in train:
        cond[state_key(p, kind)][p["b"]["bottom2"]] += 1
    return p0, cond


def predict(pair, p0, cond, kind, alpha):
    if kind is None:
        return p0
    c = cond.get(state_key(pair, kind), Counter())
    z = sum(c.values()) + alpha
    return {k: (c.get(k, 0) + alpha * p0[k]) / z for k in p0}


def evaluate(pairs, p0, cond, kind, alpha):
    ll = 0.0
    brier = 0.0
    hits = 0
    per_row = []
    for p in pairs:
        prob = predict(p, p0, cond, kind, alpha)
        y = p["b"]["bottom2"]
        py = max(prob[y], 1e-15)
        ll += -math.log(py)
        brier += sum((prob[k] - (1.0 if k == y else 0.0)) ** 2 for k in prob)
        if max(prob, key=prob.get) == y:
            hits += 1
        per_row.append((-math.log(py), -math.log(1 / 100)))
    n = len(pairs)
    return {
        "n": n,
        "log_loss": ll / n,
        "brier": brier / n,
        "top1_accuracy": hits / n,
        "per_row_logloss": [x[0] for x in per_row],
        "per_row_uniform": [x[1] for x in per_row],
    }


def uniform_brier(k):
    return (1-1/k)**2 + (k-1)/k**2


def main():
    pairs = load_pairs()
    train_days, val_days, test_days, days = days_split(pairs)
    train = [p for p in pairs if p["day"] in train_days]
    val = [p for p in pairs if p["day"] in val_days]
    test = [p for p in pairs if p["day"] in test_days]

    alphas = [1.0, 3.0, 10.0, 30.0, 100.0, 300.0, 1000.0]
    kinds = [None, "prev_lastdigit", "prev_tensdigit", "prev_bottom2", "prev_double", "prev_sum_bucket", "prev_top_last", "prev_pair_last"]
    results = []

    # uniform
    uniform_ll = math.log(100)
    results.append(
        {
            "model": "uniform",
            "selected_alpha": None,
            "validation_log_loss": uniform_ll,
            "test_log_loss": uniform_ll,
            "test_brier": uniform_brier(100),
            "test_top1_accuracy": 0.01,
            "test_n": len(test),
            "beats_uniform": 0,
            "note": "1/100 for every number",
        }
    )

    for kind in kinds:
        best = None
        for alpha in alphas:
            p0, cond = fit(train, kind, alpha)
            v = evaluate(val, p0, cond, kind, alpha)
            if best is None or v["log_loss"] < best[0]:
                best = (v["log_loss"], alpha)
        alpha = best[1]
        p0, cond = fit(train, kind, alpha)
        t = evaluate(test, p0, cond, kind, alpha)
        # paired day bootstrap for difference vs uniform
        test_by_day = defaultdict(list)
        for p, a, b in zip(test, t["per_row_logloss"], t["per_row_uniform"]):
            test_by_day[p["day"]].append(a - b)
        day_sums = np.array([sum(v) for v in test_by_day.values()])
        day_counts = np.array([len(v) for v in test_by_day.values()])
        boot = []
        for _ in range(10000):
            pick = RNG.integers(0, len(day_sums), len(day_sums))
            boot.append(float(day_sums[pick].sum()/day_counts[pick].sum()))
        results.append(
            {
                "model": kind or "train_marginal",
                "selected_alpha": alpha if kind else None,
                "validation_log_loss": best[0],
                "test_log_loss": t["log_loss"],
                "test_brier": t["brier"],
                "test_top1_accuracy": t["top1_accuracy"],
                "test_n": t["n"],
                "beats_uniform": int(t["log_loss"] < uniform_ll),
                "delta_vs_uniform": t["log_loss"] - uniform_ll,
                "delta_boot_ci_low": float(np.percentile(boot, 2.5)),
                "delta_boot_ci_high": float(np.percentile(boot, 97.5)),
                "note": "alpha selected on validation; test evaluated once",
            }
        )

    out = {
        "days": len(days),
        "train_days": [min(train_days), max(train_days)],
        "validation_days": [min(val_days), max(val_days)],
        "test_days": [min(test_days), max(test_days)],
        "train_pairs": len(train),
        "validation_pairs": len(val),
        "test_pairs": len(test),
        "models": results,
        "note": "No model uses data after its own row; split is chronological by trading day.",
    }
    (OUT / "OUT_OF_SAMPLE_RESULTS.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    with open(OUT / "OUT_OF_SAMPLE_MODELS.csv", "w", encoding="utf-8-sig", newline="") as f:
        fields = ["model", "selected_alpha", "validation_log_loss", "test_log_loss", "test_brier", "test_top1_accuracy", "test_n", "beats_uniform"]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in results:
            w.writerow({k: r.get(k) for k in fields})

    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
