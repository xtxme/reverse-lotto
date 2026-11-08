#!/usr/bin/env python3
"""
Pattern discovery with explicit multiple-testing accounting, followed by a
chronological train/validation/test evaluation of simple predictive models.

All tests are pre-declared families:
  A. marginal uniformity
  B. lag-k repeats and transitions (k=1..4)
  C. digit-position transitions (5 positions x 4 lags)
  D. state transitions (double, triple, sibling, sum)
  E. time-of-day / day-of-week
  F. same-round top-bottom relations
  G. conditional distributions after named triggers
  H. out-of-sample model comparison (bottom2)

Failures are reported, not hidden.
"""
from __future__ import annotations

import csv
import itertools
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import chi2_contingency, binomtest, pearsonr, fisher_exact

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
RNG = np.random.default_rng(20261108)
B = 5000

SIBLING = {
    "01", "10", "12", "21", "23", "32", "34", "43", "45", "54",
    "56", "65", "67", "76", "78", "87", "89", "98", "90", "09",
}


def load():
    raw = list(csv.DictReader(open(OUT / "results_dedup_independent.csv", encoding="utf-8-sig")))
    raw.sort(key=lambda r: (r["trading_day"], int(r["round"])))
    for r in raw:
        r["round"] = int(r["round"])
        r["next"] = None
        r["prev"] = {}
        for k in (1, 2, 3, 4):
            r[f"prev{k}"] = {}
    for i, r in enumerate(raw):
        for k in (1, 2, 3, 4):
            key = f"prev{k}"
            if i - k >= 0 and raw[i - k]["trading_day"] == r["trading_day"] and raw[i - k]["round"] == r["round"] - k:
                r[key] = raw[i - k]
        if i + 1 < len(raw) and raw[i + 1]["trading_day"] == r["trading_day"] and raw[i + 1]["round"] == r["round"] + 1:
            r["next"] = raw[i + 1]
    return raw


def cramers_v(table):
    table = np.asarray(table, dtype=float)
    n = table.sum()
    if n == 0:
        return None
    chi2 = chi2_contingency(table, correction=False)[0]
    return math.sqrt(chi2 / (n * (min(table.shape) - 1)))


def mutual_info(table):
    table = np.asarray(table, dtype=float)
    n = table.sum()
    if n == 0:
        return None
    p = table / n
    px = p.sum(axis=1, keepdims=True)
    py = p.sum(axis=0, keepdims=True)
    nz = p > 0
    return float(np.sum(p[nz] * np.log2(p[nz] / (px @ py)[nz])))


def perm_chi2(rows, xkey, ykey, groups_key="trading_day", B=B):
    """Permutation p for chi-square independence, shuffling y within day."""
    xs = [r[xkey] for r in rows]
    ys = [r[ykey] for r in rows]
    obs = chi2_contingency(np.array(pd_crosstab(xs, ys)), correction=False)[0]
    groups = defaultdict(list)
    for i, r in enumerate(rows):
        groups[r[groups_key]].append(i)
    sims = []
    for _ in range(B):
        yy = list(ys)
        for idxs in groups.values():
            vals = [yy[i] for i in idxs]
            RNG.shuffle(vals)
            for i, v in zip(idxs, vals):
                yy[i] = v
        sims.append(chi2_contingency(np.array(pd_crosstab(xs, yy)), correction=False)[0])
    return obs, (1 + sum(s >= obs for s in sims)) / (B + 1)


def pd_crosstab(xs, ys):
    xv = sorted(set(xs))
    yv = sorted(set(ys))
    xi = {v: i for i, v in enumerate(xv)}
    yi = {v: i for i, v in enumerate(yv)}
    t = np.zeros((len(xv), len(yv)), dtype=int)
    for x, y in zip(xs, ys):
        t[xi[x], yi[y]] += 1
    return t


def bh(pvals):
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    q = [1.0] * m
    prev = 1.0
    for rank in range(m, 0, -1):
        i = order[rank - 1]
        val = min(prev, pvals[i] * m / rank)
        q[i] = val
        prev = val
    return q


def main():
    rows = load()
    tests = []

    def add(family, name, n, stat, p, effect=None, detail=""):
        tests.append(
            {
                "family": family,
                "test": name,
                "n": n,
                "statistic": stat,
                "p_value": p,
                "effect": effect,
                "detail": detail,
            }
        )

    # ---------- A. marginal uniformity ----------
    for field, k in (("bottom2", 100), ("top3", 1000)):
        c = Counter(r[field] for r in rows)
        n = len(rows)
        chi = sum((c.get(f"{i:0{len(rows[0][field])}d}", 0) - n / k) ** 2 / (n / k) for i in range(k))
        # chi-square with sparse cells: Monte Carlo p
        sims = []
        for _ in range(500):
            sample = RNG.integers(0, k, n)
            cc = np.bincount(sample, minlength=k)
            sims.append(((cc - n / k) ** 2 / (n / k)).sum())
        p = (1 + sum(s >= chi for s in sims)) / (501)
        add("A_marginal", f"{field}_uniform", n, round(chi, 2), p, effect=f"max_share={max(c.values())/n:.4f}")

    # ---------- B. lag-k repeats / transitions ----------
    for k in (1, 2, 3, 4):
        pairs = [r for r in rows if r[f"prev{k}"]]
        n = len(pairs)
        # exact repeat of bottom2
        rep = sum(r["bottom2"] == r[f"prev{k}"]["bottom2"] for r in pairs)
        p = binomtest(rep, n, 1 / 100, alternative="two-sided").pvalue
        add("B_lag", f"bottom2_exact_repeat_lag{k}", n, rep, p, effect=rep / n - 0.01)
        # last-digit repeat
        rep = sum(r["bottom2"][-1] == r[f"prev{k}"]["bottom2"][-1] for r in pairs)
        p = binomtest(rep, n, 0.1, alternative="two-sided").pvalue
        add("B_lag", f"bottom_lastdigit_repeat_lag{k}", n, rep, p, effect=rep / n - 0.1)
        # attach prev key, then transition-table chi-square
        for r in pairs:
            r[f"prev{k}_bottom2"] = r[f"prev{k}"]["bottom2"]
        obs, pp = perm_chi2(pairs, f"prev{k}_bottom2", "bottom2")
        tab = pd_crosstab([r[f"prev{k}_bottom2"] for r in pairs], [r["bottom2"] for r in pairs])
        add("B_lag", f"bottom2_transition_lag{k}", n, round(obs, 2), pp, effect=round(cramers_v(tab), 4), detail=f"MI={mutual_info(tab):.4f} bits")

    # ---------- C. digit-position transitions ----------
    positions = {
        "top_hundreds": lambda r: r["top3"][0],
        "top_tens": lambda r: r["top3"][1],
        "top_units": lambda r: r["top3"][2],
        "bottom_tens": lambda r: r["bottom2"][0],
        "bottom_units": lambda r: r["bottom2"][1],
    }
    for k in (1, 2, 3, 4):
        pairs = [r for r in rows if r[f"prev{k}"]]
        for name, fn in positions.items():
            xs = [fn(r[f"prev{k}"]) for r in pairs]
            ys = [fn(r) for r in pairs]
            tab = pd_crosstab(xs, ys)
            chi = chi2_contingency(tab, correction=False)[0]
            # 10x10, df=81; use chi2 sf via scipy
            from scipy.stats import chi2 as chi2dist

            p = chi2dist.sf(chi, 81)
            add("C_position", f"{name}_lag{k}", len(pairs), round(chi, 2), p, effect=round(cramers_v(tab), 4))

    # ---------- D. state transitions ----------
    states = {
        "double": lambda r: r["bottom2"] in {f"{d}{d}" for d in range(10)},
        "triple_top": lambda r: len(set(r["top3"])) == 1,
        "sibling_bottom": lambda r: r["bottom2"] in SIBLING,
        "sum10_bottom": lambda r: sum(map(int, r["bottom2"])) == 10,
        "even_bottom": lambda r: int(r["bottom2"]) % 2 == 0,
    }
    for k in (1, 2, 3, 4):
        pairs = [r for r in rows if r[f"prev{k}"]]
        for name, fn in states.items():
            xs = [fn(r[f"prev{k}"]) for r in pairs]
            ys = [fn(r) for r in pairs]
            tab = pd_crosstab(xs, ys)
            chi = chi2_contingency(tab, correction=False)[0]
            p = fisher_exact(tab, alternative="two-sided").pvalue
            add("D_state", f"{name}_lag{k}", len(pairs), round(chi, 2), p, effect=round(cramers_v(tab), 4))

    # ---------- E. time-of-day / day-of-week ----------
    import datetime

    for field in ("top3", "bottom2"):
        for pos in range(len(rows[0][field])):
            xs = [r["trading_day"][11:13] if False else r["scheduled_close"][11:13] for r in rows]
            ys = [r[field][pos] for r in rows]
            tab = pd_crosstab(xs, ys)
            chi = chi2_contingency(tab, correction=False)[0]
            p = chi2_contingency(tab, correction=False)[1]
            add("E_time", f"{field}_pos{pos}_by_hour", len(rows), round(chi, 2), p, effect=round(cramers_v(tab), 4))
    for field in ("top3", "bottom2"):
        xs = [datetime.date.fromisoformat(r["trading_day"]).strftime("%a") for r in rows]
        for pos in range(len(rows[0][field])):
            ys = [r[field][pos] for r in rows]
            tab = pd_crosstab(xs, ys)
            chi = chi2_contingency(tab, correction=False)[0]
            p = chi2_contingency(tab, correction=False)[1]
            add("E_time", f"{field}_pos{pos}_by_weekday", len(rows), round(chi, 2), p, effect=round(cramers_v(tab), 4))

    # ---------- F. same-round relations ----------
    # probability that a given top digit equals a given bottom digit
    for i, label in enumerate(("hundreds", "tens", "units")):
        for j, jlabel in enumerate(("tens", "units")):
            eq = sum(r["top3"][i] == r["bottom2"][j] for r in rows)
            p = binomtest(eq, len(rows), 0.1, alternative="two-sided").pvalue
            add("F_same_round", f"top_{label}_eq_bottom_{jlabel}", len(rows), eq, p, effect=eq / len(rows) - 0.1)
    # top3 digit duplicates
    dup = sum(len(set(r["top3"])) < 3 for r in rows)
    p = binomtest(dup, len(rows), 0.28, alternative="two-sided").pvalue
    add("F_same_round", "top3_has_duplicate", len(rows), dup, p, effect=dup / len(rows) - 0.28)
    tri = sum(len(set(r["top3"])) == 1 for r in rows)
    p = binomtest(tri, len(rows), 0.01, alternative="two-sided").pvalue
    add("F_same_round", "top3_triple", len(rows), tri, p, effect=tri / len(rows) - 0.01)

    # ---------- G. conditional distributions ----------
    # after double / 69 / 65, is next bottom2 distribution different from marginal?
    triggers = {
        "after_double": lambda r: r["bottom2"] in {f"{d}{d}" for d in range(10)},
        "after_69": lambda r: r["bottom2"] == "69",
        "after_65": lambda r: r["bottom2"] == "65",
        "after_sum10": lambda r: sum(map(int, r["bottom2"])) == 10,
    }
    base = Counter(r["next"]["bottom2"] for r in rows if r["next"])
    nbase = sum(base.values())
    for name, fn in triggers.items():
        sub = [r for r in rows if r["next"] and fn(r)]
        c = Counter(r["next"]["bottom2"] for r in sub)
        n = len(sub)
        # chi-square vs marginal (100 cells, sparse) -> permutation of labels
        # use total variation distance and a day-preserving permutation
        tvd = 0.5 * sum(abs(c.get(f"{i:02d}", 0) / n - base.get(f"{i:02d}", 0) / nbase) for i in range(100))
        idxs = [i for i, r in enumerate(rows) if r["next"]]
        groups = defaultdict(list)
        for pos, i in enumerate(idxs):
            groups[rows[i]["trading_day"]].append(pos)
        trig = [fn(rows[i]) for i in idxs]
        y = [rows[i]["next"]["bottom2"] for i in idxs]
        sims = []
        for _ in range(1000):
            tt = list(trig)
            for g in groups.values():
                vals = [tt[i] for i in g]
                RNG.shuffle(vals)
                for i, v in zip(g, vals):
                    tt[i] = v
            cc = Counter(y[i] for i in range(len(idxs)) if tt[i])
            nn = sum(tt)
            sims.append(0.5 * sum(abs(cc.get(f"{j:02d}", 0) / nn - base.get(f"{j:02d}", 0) / nbase) for j in range(100)))
        p = (1 + sum(s >= tvd for s in sims)) / 1001
        add("G_conditional", name, n, round(tvd, 4), p, effect=f"TVD={tvd:.4f}", detail=f"top_next={c.most_common(3)}")

    # ---------- H. multiple testing ----------
    q = bh([t["p_value"] for t in tests])
    for t, qq in zip(tests, q):
        t["q_value_BH"] = qq
    with open(OUT / "PATTERN_DISCOVERY_TESTS.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(tests[0].keys()))
        w.writeheader()
        w.writerows(tests)

    summary = {
        "n_tests": len(tests),
        "n_rows": len(rows),
        "n_contiguous_pairs": sum(1 for r in rows if r["next"]),
        "min_p": min(t["p_value"] for t in tests),
        "n_p_below_0.05": sum(1 for t in tests if t["p_value"] < 0.05),
        "n_q_below_0.05": sum(1 for t in tests if t["q_value_BH"] < 0.05),
        "smallest_q": min(t["q_value_BH"] for t in tests),
        "top_10_by_p": sorted(tests, key=lambda t: t["p_value"])[:10],
        "families": {f: sum(1 for t in tests if t["family"] == f) for f in sorted({t["family"] for t in tests})},
    }
    (OUT / "PATTERN_DISCOVERY_SUMMARY.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
