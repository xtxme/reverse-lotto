#!/usr/bin/env python3
"""
Backtest every operational interpretation of the screenshot rules.

Statistical design
------------------
* Unit: one 15-minute round pair (trigger round t -> target round t+1),
  restricted to consecutive rounds inside the same trading day.
* Two baselines:
    - uniform p0 implied by the target set / digit containment;
    - empirical baseline = target rate over all evaluable rows.
* Inference:
    - exact binomial one-sided p against p0;
    - within-day permutation of the trigger labels (hypergeometric per day),
      which preserves the number of triggers per day and each day's target
      distribution;
    - global permutation for reference.
* All interpretations are reported.  No variant is selected after seeing
  the results.  BH q-values are computed over the pre-declared primary
  family and, separately, over every variant.
"""
from __future__ import annotations

import csv
import math
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import binomtest, hypergeom

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
RNG = np.random.default_rng(20261108)
B = 20000

SIBLING_CANON = {"01", "12", "23", "34", "45", "56", "67", "78", "89", "90"}
SIBLING = SIBLING_CANON | {s[::-1] for s in SIBLING_CANON}
DOUBLES = {f"{d}{d}" for d in range(10)}
CONTAINS0 = {f"{a}{b}" for a in range(10) for b in range(10) if "0" in f"{a}{b}"}
SIB_OR_0 = CONTAINS0 | SIBLING
IMG1 = {"85", "97", "94", "95", "74", "96", "75"}
IMG2 = {"56", "58", "59", "68", "69", "76", "78", "79", "89"}


def load_rows():
    import os
    path = os.environ.get("RESULTS_CSV", str(OUT / "results_dedup_independent.csv"))
    raw = list(csv.DictReader(open(path, encoding="utf-8-sig")))
    raw.sort(key=lambda r: (r["trading_day"], int(r["round"])))
    for r in raw:
        r["round"] = int(r["round"])
    idx = {(r["trading_day"], r["round"]): i for i, r in enumerate(raw)}
    for i, r in enumerate(raw):
        r["next"] = raw[i + 1] if i + 1 < len(raw) and raw[i + 1]["trading_day"] == r["trading_day"] and raw[i + 1]["round"] == r["round"] + 1 else None
        r["prev"] = raw[i - 1] if i > 0 and raw[i - 1]["trading_day"] == r["trading_day"] and raw[i - 1]["round"] == r["round"] - 1 else None
        r["prev2"] = raw[i - 2] if i > 1 and raw[i - 2]["trading_day"] == r["trading_day"] and raw[i - 2]["round"] == r["round"] - 2 else None
        r["next2"] = raw[i + 2] if i + 2 < len(raw) and raw[i + 2]["trading_day"] == r["trading_day"] and raw[i + 2]["round"] == r["round"] + 2 else None
    return raw


def wilson(k, n, z=1.96):
    if n == 0:
        return (None, None)
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, centre - half), min(1.0, centre + half))


def perm_test(rows, trig, y, B=B):
    """Within-day permutation of trigger labels."""
    groups = defaultdict(list)
    for i, r in enumerate(rows):
        groups[r["trading_day"]].append(i)
    obs = int(sum(t * yy for t, yy in zip(trig, y)))
    sims = np.zeros(B, dtype=float)
    for idxs in groups.values():
        idxs = np.asarray(idxs)
        n = len(idxs)
        t = int(sum(trig[i] for i in idxs))
        yy = int(sum(y[i] for i in idxs))
        if t == 0 or yy == 0 or t == n:
            sims += t * yy / n if n else 0
            continue
        sims += hypergeom.rvs(n, yy, t, size=B, random_state=RNG)
        p = (1 + int((sims >= obs).sum())) / (B + 1)
    return p, float(sims.mean()), float(sims.std())


def global_perm(rows, trig, y, B=B):
    obs = int(sum(t * yy for t, yy in zip(trig, y)))
    T = int(sum(trig))
    Y = int(sum(y))
    n = len(rows)
    sims = hypergeom.rvs(n, Y, T, size=B, random_state=RNG)
    p = (1 + int((sims >= obs).sum())) / (B + 1)
    return p


def rate(rows, trig, y):
    n = int(sum(trig))
    k = int(sum(t * yy for t, yy in zip(trig, y)))
    return n, k, (k / n if n else None)


def bh(pvals):
    """Benjamini-Hochberg q-values; None passes through."""
    m = len(pvals)
    order = sorted(range(m), key=lambda i: (pvals[i] is None, pvals[i] if pvals[i] is not None else 1))
    q = [None] * m
    prev = 1.0
    for rank in range(m, 0, -1):
        i = order[rank - 1]
        if pvals[i] is None:
            continue
        val = min(prev, pvals[i] * m / rank)
        q[i] = val
        prev = val
    return q


# ---------------------------------------------------------------------------
# trigger / target helpers
# ---------------------------------------------------------------------------
def is_sibling_bottom(r):
    return r["bottom2"] in SIBLING_CANON


def is_sibling_bottom_both(r):
    return r["bottom2"] in SIBLING


def top_has_adjacent(r):
    d = r["top3"]
    return any(d[i : i + 2] in SIBLING for i in (0, 1))


def top_is_double(r):
    d = r["top3"]
    return len(set(d)) == 2


def bottom_double(r):
    return r["bottom2"] in DOUBLES


def contains(bs, digits):
    return any(c in digits for c in bs)


def target_next(field, kind, values=None, digits=None):
    def f(r):
        n = r["next"]
        if n is None:
            return None
        s = n[field]
        if kind == "set":
            return s in values
        if kind == "contains":
            return contains(s, digits)
        if kind == "double":
            return s in DOUBLES
        if kind == "sibling":
            return s in SIBLING
        if kind == "sum10":
            return sum(map(int, s)) == 10
        if kind == "triple":
            return len(set(s)) == 1
        raise ValueError(kind)

    return f


# Each spec: test_id, rule_id, variant, description, trigger, target, p0, primary
SPECS = []


def add(test_id, rule_id, variant, description, trigger, target, p0, primary=1, unresolved=""):
    SPECS.append(
        dict(
            test_id=test_id,
            rule_id=rule_id,
            variant=variant,
            description=description,
            trigger=trigger,
            target=target,
            p0=p0,
            is_primary=primary,
            unresolved=unresolved,
        )
    )


# R01
add(
    "R01-primary",
    "R01",
    "primary: adjacent-digit sibling in 2 consecutive rounds",
    "bottom sibling in t-1 and t -> next bottom double",
    lambda r: bool(r["prev"] and is_sibling_bottom(r["prev"]) and is_sibling_bottom(r)),
    target_next("bottom2", "double"),
    0.10,
)
add(
    "R01-alt-same-sibling",
    "R01",
    "alt: the same sibling number in 2 consecutive rounds",
    "bottom2(t-1)==bottom2(t) and sibling -> next bottom double",
    lambda r: bool(r["prev"] and r["prev"]["bottom2"] == r["bottom2"] and is_sibling_bottom(r)),
    target_next("bottom2", "double"),
    0.10,
    primary=0,
)
# R02
add(
    "R02-primary",
    "R02",
    "primary: bottom digit sum 10",
    "bottom digit sum=10 -> next bottom contains 0",
    lambda r: (r["bottom2"] in SIBLING_CANON) or (sum(map(int, r["bottom2"])) == 10),
    target_next("bottom2", "contains", digits="0"),
    0.19,
)
add(
    "R02-alt-last0",
    "R02",
    "alt: target last digit 0",
    "bottom digit sum=10 -> next bottom last digit 0",
    lambda r: sum(map(int, r["bottom2"])) == 10,
    lambda r: bool(r["next"] and r["next"]["bottom2"][1] == "0"),
    0.10,
    primary=0,
)
# R03
add(
    "R03-primary",
    "R03",
    "primary: bottom sibling + top repeated digit",
    "bottom sibling and top double -> next bottom contains 0",
    lambda r: is_sibling_bottom(r) and top_is_double(r),
    target_next("bottom2", "contains", digits="0"),
    0.19,
)
# R04
add(
    "R04-primary",
    "R04",
    "primary: sibling in both fields",
    "bottom sibling and top adjacent pair -> next bottom contains 1/0/8",
    lambda r: is_sibling_bottom(r) and top_has_adjacent(r),
    target_next("bottom2", "contains", digits="108"),
    0.51,
)
add(
    "R04-alt-lastdigit",
    "R04",
    "alt: target last digit in 1/0/8",
    "bottom sibling and top adjacent pair -> next bottom last digit in 1/0/8",
    lambda r: is_sibling_bottom(r) and top_has_adjacent(r),
    lambda r: bool(r["next"] and r["next"]["bottom2"][1] in "108"),
    0.30,
    primary=0,
)
# R05
add(
    "R05-primary",
    "R05",
    "primary: sibling in both fields",
    "bottom sibling and top adjacent pair -> next bottom sibling",
    lambda r: is_sibling_bottom(r) and top_has_adjacent(r),
    target_next("bottom2", "set", values=SIBLING_CANON),
    0.10,
)
# R06
def is_ham(r):
    """ABA top3: first == last, middle different (Thai 'หาม')."""
    d = r["top3"]
    return d[0] == d[2] and d[1] != d[0]


def r06_trigger(r):
    return is_ham(r)


add(
    "R06-primary",
    "R06",
    "primary: return after one skipped round",
    "bottom2(t)==bottom2(t-2)!=bottom2(t-1) -> next bottom2 equals it",
    r06_trigger,
    lambda r: bool(r.get("next2") and r["top3"][0] in r["next2"]["top3"]),
    0.271,
    unresolved="'หมา' has no verified standard definition",
)
add(
    "R06-alt-noskip",
    "R06",
    "alt: no skip, t+1 top contains the digit",
    "หาม at t -> t+1 top contains the repeated digit",
    r06_trigger,
    lambda r: bool(r["next"] and r["top3"][0] in r["next"]["top3"]),
    0.271,
    primary=0,
    unresolved="'หมา' = 'หาม' (ABA), but the skip semantics are inferred",
)
add(
    "R06-alt-bottom",
    "R06",
    "alt: t+2 bottom contains the digit",
    "หาม at t -> t+2 bottom contains the repeated digit",
    r06_trigger,
    lambda r: bool(r.get("next2") and r["top3"][0] in r["next2"]["bottom2"]),
    0.19,
    primary=0,
    unresolved="'หมา' = 'หาม' (ABA), but the skip semantics are inferred",
)
# R07
add(
    "R07-primary",
    "R07",
    "primary: top triple -> same digit in next top",
    "top3 triple -> next top3 contains that digit",
    lambda r: len(set(r["top3"])) == 1,
    lambda r: bool(r["next"] and r["top3"][0] in r["next"]["top3"]),
    0.271,
)
add(
    "R07-alt-exact",
    "R07",
    "alt: exact triple repeats",
    "top3 triple -> next top3 is the same triple",
    lambda r: len(set(r["top3"])) == 1,
    lambda r: bool(r["next"] and r["next"]["top3"] == r["top3"]),
    0.001,
    primary=0,
)
add(
    "R07-alt-bottom",
    "R07",
    "alt: follow in bottom2",
    "top3 triple -> next bottom2 contains that digit",
    lambda r: len(set(r["top3"])) == 1,
    lambda r: bool(r["next"] and r["top3"][0] in r["next"]["bottom2"]),
    0.19,
    primary=0,
)
# R08
add(
    "R08-primary",
    "R08",
    "primary: target contains 0 or sibling",
    "bottom double -> next bottom contains 0 OR is sibling",
    bottom_double,
    lambda r: bool(r["next"] and (contains(r["next"]["bottom2"], "0") or r["next"]["bottom2"] in SIBLING_CANON)),
    0.27,
)
add(
    "R08-alt-0only",
    "R08",
    "alt: target contains 0 only",
    "bottom double -> next bottom contains 0",
    bottom_double,
    target_next("bottom2", "contains", digits="0"),
    0.19,
    primary=0,
)
add(
    "R08-alt-sibling-only",
    "R08",
    "alt: target sibling only",
    "bottom double -> next bottom sibling",
    bottom_double,
    target_next("bottom2", "set", values=SIBLING_CANON),
    0.10,
    primary=0,
)
# R09
add(
    "R09-primary",
    "R09",
    "primary: both sums 10",
    "top sum=10 and bottom sum=10 -> next bottom double",
    lambda r: sum(map(int, r["top3"])) == 10 and sum(map(int, r["bottom2"])) == 10,
    target_next("bottom2", "double"),
    0.10,
)
add(
    "R09-alt-either",
    "R09",
    "alt: either field sum 10",
    "top or bottom sum=10 -> next bottom double",
    lambda r: sum(map(int, r["top3"])) == 10 or sum(map(int, r["bottom2"])) == 10,
    target_next("bottom2", "double"),
    0.10,
    primary=0,
)
# R10
add(
    "R10-primary",
    "R10",
    "primary: bottom tens=0 -> contains 0",
    "bottom2[0]=0 -> next bottom contains 0",
    lambda r: r["bottom2"][0] == "0",
    target_next("bottom2", "contains", digits="0"),
    0.19,
)
add(
    "R10-alt-tens0",
    "R10",
    "alt: next tens digit 0",
    "bottom2[0]=0 -> next bottom2[0]=0",
    lambda r: r["bottom2"][0] == "0",
    lambda r: bool(r["next"] and r["next"]["bottom2"][0] == "0"),
    0.10,
    primary=0,
)
# R11
add(
    "R10-alt-top-tens0",
    "R10",
    "alt: top3 tens=0 -> next bottom contains 0",
    "top3[1]=0 -> next bottom contains 0",
    lambda r: r["top3"][1] == "0",
    target_next("bottom2", "contains", digits="0"),
    0.19,
    primary=0,
)
add(
    "R11-primary",
    "R11",
    "primary: same trigger as R06 -> contains 0 or 6",
    "return after one skipped round -> next bottom contains 0 or 6",
    r06_trigger,
    lambda r: bool(r.get("next2") and contains(r["next2"]["bottom2"], "06")),
    0.36,
    unresolved="'หมา' has no verified standard definition",
)
add(
    "R11-alt-last06",
    "R11",
    "alt: next last digit 0 or 6",
    "return after one skipped round -> next last digit 0 or 6",
    r06_trigger,
    lambda r: bool(r["next"] and r["next"]["bottom2"][1] in "06"),
    0.20,
    primary=0,
    unresolved="'หมา' has no verified standard definition",
)
# R12
add(
    "R12-primary",
    "R12",
    "primary: target contains 8",
    "bottom double -> next bottom contains 8",
    bottom_double,
    target_next("bottom2", "contains", digits="8"),
    0.19,
)
# R13
add(
    "R12-alt-topdouble",
    "R12",
    "alt: top3 double -> next bottom contains 8",
    "top3 has any repeated pair -> next bottom contains 8",
    top_is_double,
    target_next("bottom2", "contains", digits="8"),
    0.19,
    primary=0,
)
add(
    "R13-primary",
    "R13",
    "primary: last digit 5",
    "bottom last digit 5 -> next bottom contains 0",
    lambda r: r["bottom2"][1] == "5",
    target_next("bottom2", "contains", digits="0"),
    0.19,
)
add(
    "R13-alt-contains5",
    "R13",
    "alt: bottom contains 5",
    "bottom contains 5 -> next bottom contains 0",
    lambda r: "5" in r["bottom2"],
    target_next("bottom2", "contains", digits="0"),
    0.19,
    primary=0,
)
# R14
add(
    "R14-primary",
    "R14",
    "primary: top tens == bottom tens",
    "top3[1]==bottom2[0] -> next bottom contains 3",
    lambda r: r["top3"][1] == r["bottom2"][0],
    target_next("bottom2", "contains", digits="3"),
    0.19,
)
add(
    "R14-alt-next-top",
    "R14",
    "alt: target next top contains 3",
    "top3[1]==bottom2[0] -> next top contains 3",
    lambda r: r["top3"][1] == r["bottom2"][0],
    lambda r: bool(r["next"] and "3" in r["next"]["top3"]),
    0.271,
    primary=0,
)
# R15
add(
    "R15-primary",
    "R15",
    "primary: top first two equal",
    "top3 AAB -> next bottom contains 7 or 9",
    lambda r: r["top3"][0] == r["top3"][1],
    target_next("bottom2", "contains", digits="79"),
    0.36,
)
add(
    "R15-alt-bottom-double",
    "R15",
    "alt: 'เบิ้ลหน้า' means bottom double",
    "bottom double -> next bottom contains 7 or 9",
    bottom_double,
    target_next("bottom2", "contains", digits="79"),
    0.36,
    primary=0,
)
# R16
add(
    "R16-primary",
    "R16",
    "primary: top and bottom share any digit",
    "set(top3)&set(bottom2) non-empty -> next bottom contains 3",
    lambda r: bool(set(r["top3"]) & set(r["bottom2"])),
    target_next("bottom2", "contains", digits="3"),
    0.19,
)
add(
    "R16-alt-same-position",
    "R16",
    "alt: last digit of both fields equal",
    "top3[2]==bottom2[1] -> next bottom contains 3",
    lambda r: r["top3"][2] == r["bottom2"][1],
    target_next("bottom2", "contains", digits="3"),
    0.19,
    primary=0,
)
# R17
add(
    "R17-primary",
    "R17",
    "primary: top hundreds=4 -> next top contains 6",
    "top3[0]=4 -> next top contains 6",
    lambda r: r["top3"][0] == "4",
    lambda r: bool(r["next"] and "6" in r["next"]["top3"]),
    0.271,
)
add(
    "R17-alt-bottom",
    "R17",
    "alt: target next bottom contains 6",
    "top3[0]=4 -> next bottom contains 6",
    lambda r: r["top3"][0] == "4",
    target_next("bottom2", "contains", digits="6"),
    0.19,
    primary=0,
)
# I1
add(
    "I1-primary",
    "I1",
    "primary: bottom double -> next bottom in 7-number set",
    "bottom double -> next bottom in {85,97,94,95,74,96,75}",
    bottom_double,
    target_next("bottom2", "set", values=IMG1),
    0.07,
)
add(
    "I1-alt-toplast2",
    "I1",
    "alt: target next top last two digits in set",
    "bottom double -> next top last2 in set",
    bottom_double,
    lambda r: bool(r["next"] and r["next"]["top3"][-2:] in IMG1),
    0.07,
    primary=0,
)
# I2
add(
    "I2a-primary",
    "I2a",
    "primary: bottom=69 -> next bottom in 9-number set",
    "bottom=69 -> next bottom in set",
    lambda r: r["bottom2"] == "69",
    target_next("bottom2", "set", values=IMG2),
    0.09,
)
add(
    "I2b-primary",
    "I2b",
    "primary: bottom=65 -> next bottom in 9-number set",
    "bottom=65 -> next bottom in set",
    lambda r: r["bottom2"] == "65",
    target_next("bottom2", "set", values=IMG2),
    0.09,
    primary=0,
)
add(
    "I2c-primary",
    "I2c",
    "primary: 69 then 65 -> next bottom in set",
    "bottom(t-1)=69 and bottom(t)=65 -> next bottom in set",
    lambda r: bool(r["prev"] and r["prev"]["bottom2"] == "69" and r["bottom2"] == "65"),
    target_next("bottom2", "set", values=IMG2),
    0.09,
)
add(
    "I2d-secondary",
    "I2d",
    "secondary: 69 or 65 -> next bottom in set",
    "bottom in {69,65} -> next bottom in set",
    lambda r: r["bottom2"] in {"69", "65"},
    target_next("bottom2", "set", values=IMG2),
    0.09,
    primary=0,
)


def main():
    rows = load_rows()
    out = []
    for spec in SPECS:
        trig = []
        y = []
        valid = []
        for r in rows:
            t = spec["trigger"](r)
            if t is None:
                continue
            yy = spec["target"](r)
            if yy is None:
                continue
            valid.append(r)
            trig.append(bool(t))
            y.append(bool(yy))
        n = len(valid)
        nt, k, hit_rate = rate(valid, trig, y)
        lo, hi = wilson(k, nt)
        emp = sum(y) / n if n else None
        p_binom = binomtest(k, nt, spec["p0"], alternative="greater").pvalue if nt else None
        if nt:
            p_perm, sim_mean, sim_sd = perm_test(valid, trig, y)
            p_glob = global_perm(valid, trig, y)
        else:
            p_perm = p_glob = None
            sim_mean = sim_sd = None
        # chronological 60/40 split of evaluable rows
        cut = int(0.6 * n)
        first = [i for i in range(n) if i < cut]
        last = [i for i in range(n) if i >= cut]

        def sub_rate(idxs):
            nn = sum(trig[i] for i in idxs)
            kk = sum(trig[i] and y[i] for i in idxs)
            return (kk, nn, round(kk / nn, 4) if nn else None)

        fk, fn, fr = sub_rate(first)
        lk, ln, lr = sub_rate(last)
        out.append(
            {
                "test_id": spec["test_id"],
                "rule_id": spec["rule_id"],
                "variant": spec["variant"],
                "description": spec["description"],
                "is_primary": spec["is_primary"],
                "n_evaluable": n,
                "triggers": nt,
                "hits": k,
                "hit_rate": round(hit_rate, 4) if hit_rate is not None else None,
                "ci95_low": round(lo, 4) if lo is not None else None,
                "ci95_high": round(hi, 4) if hi is not None else None,
                "p0_uniform": spec["p0"],
                "empirical_baseline": round(emp, 4) if emp is not None else None,
                "lift_vs_uniform_pp": round(100 * (hit_rate - spec["p0"]), 2) if hit_rate is not None else None,
                "lift_vs_empirical_pp": round(100 * (hit_rate - emp), 2) if hit_rate is not None and emp is not None else None,
                "binom_p_one_sided": p_binom,
                "perm_p_within_day": p_perm,
                "perm_p_global": p_glob,
                "perm_null_mean": round(sim_mean, 2) if sim_mean is not None else None,
                "perm_null_sd": round(sim_sd, 2) if sim_sd is not None else None,
                "split_first_60_hits": fk,
                "split_first_60_n": fn,
                "split_first_60_rate": fr,
                "split_last_40_hits": lk,
                "split_last_40_n": ln,
                "split_last_40_rate": lr,
                "unresolved_terms": spec["unresolved"],
            }
        )

    # multiple testing
    prim = [i for i, r in enumerate(out) if r["is_primary"] == 1]
    q_prim = bh([out[i]["perm_p_within_day"] for i in prim])
    for i, q in zip(prim, q_prim):
        out[i]["q_BH_primary_family"] = q
    q_all = bh([r["perm_p_within_day"] for r in out])
    for r, q in zip(out, q_all):
        r["q_BH_all_variants"] = q
        r.setdefault("q_BH_primary_family", None)

    fields = list(out[0].keys())
    with open(OUT / "IMAGE_RULE_BACKTEST.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(out)

    # compact console summary
    print(f"evaluable rows: {out[0]['n_evaluable']}")
    for r in out:
        print(
            f"{r['test_id']:<24} trig={r['triggers']:>4} hit={r['hits']:>4} "
            f"rate={r['hit_rate']} p0={r['p0_uniform']} perm_p={r['perm_p_within_day']} "
            f"q={r['q_BH_primary_family'] or r['q_BH_all_variants']}"
        )


if __name__ == "__main__":
    main()
