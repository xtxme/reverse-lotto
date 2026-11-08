#!/usr/bin/env python3
"""
Independent audit of the hourly "เลขนิ่ง" digit table.

Key points
----------
* 886 posts collapse to 86 daily tables.  FORECASTER_A and FORECASTER_03 repost
  the same table, so authors are NOT independent forecasters.
* A digit is evaluated only if its first appearance was strictly before the
  first draw of the target hour.
* A digit counts as a hit if it appears in any of the four draws of that hour
  (top3: any of 3 positions; bottom2: any of 2 positions).
* Inference is at the day level: within-day permutation of the 22 digits and
  a day bootstrap, because hours within a day are not independent.
"""
from __future__ import annotations

import csv
import json
import math
import random
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
RNG = np.random.default_rng(20261108)


def load_results():
    rows = list(csv.DictReader(open(OUT / "results_dedup_independent.csv", encoding="utf-8-sig")))
    lookup = {}
    for r in rows:
        dt = datetime.fromisoformat(r["scheduled_close"])
        lookup[dt] = (r["top3"], r["bottom2"])
    return rows, lookup


def load_posts():
    return json.load(open(OUT / "hourly_forecast_posts.json", encoding="utf-8"))


def trading_day(ts: datetime) -> str:
    d = ts.date() if ts.hour >= 5 else ts.date() - timedelta(days=1)
    return d.isoformat()


def build_daily_tables(posts):
    """Return day -> hour_label -> {digit, first_posted, sources}."""
    byday = defaultdict(lambda: defaultdict(list))
    for p in posts:
        ts = datetime.fromisoformat(p["posted"])
        day = trading_day(ts)
        for e in p["entries"]:
            byday[day][e["hour_label"]].append(
                {"digit": e["digit"], "posted": ts, "author": p["author"], "line": p["line"]}
            )
    tables = {}
    conflicts = []
    for day, hours in byday.items():
        tables[day] = {}
        for h, entries in hours.items():
            entries.sort(key=lambda x: (x["posted"], x["line"]))
            digits = sorted({e["digit"] for e in entries})
            if len(digits) > 1:
                conflicts.append({"day": day, "hour": h, "digits": digits, "n": len(entries)})
            first = entries[0]
            tables[day][h] = {
                "digit": first["digit"],
                "first_posted": first["posted"],
                "first_author": first["author"],
                "first_line": first["line"],
                "n_posts": len(entries),
                "n_distinct": len(digits),
            }
    return tables, conflicts


def target_dt(day: str, hour_label: int) -> datetime:
    d = datetime.fromisoformat(day)
    if hour_label == 24:
        return datetime.combine(d + timedelta(days=1), datetime.min.time())
    if 1 <= hour_label <= 3:
        return datetime.combine(d + timedelta(days=1), datetime.min.time()) + timedelta(hours=hour_label)
    return datetime.combine(d, datetime.min.time()) + timedelta(hours=hour_label)


def main():
    rows, lookup = load_results()
    posts = load_posts()
    tables, conflicts = build_daily_tables(posts)

    # ---- build evaluable hour records --------------------------------------
    recs = []
    excluded_post_after = 0
    excluded_missing_draws = 0
    for day in sorted(tables):
        for h, info in sorted(tables[day].items()):
            target = target_dt(day, h)
            if info["first_posted"] >= target:
                excluded_post_after += 1
                continue
            draws = [lookup.get(target + timedelta(minutes=15 * i)) for i in range(4)]
            if any(d is None for d in draws):
                excluded_missing_draws += 1
                continue
            top_union = set("".join(d[0] for d in draws))
            bot_union = set("".join(d[1] for d in draws))
            either_union = top_union | bot_union
            d = info["digit"]
            ds = str(d)
            recs.append(
                {
                    "trading_day": day,
                    "hour_label": h,
                    "target_hour": target.isoformat(sep=" "),
                    "digit": d,
                    "first_posted": info["first_posted"].isoformat(sep=" "),
                    "lead_minutes": round((target - info["first_posted"]).total_seconds() / 60),
                    "first_author": info["first_author"],
                    "n_posts": info["n_posts"],
                    "top_union_size": len(top_union),
                    "bottom_union_size": len(bot_union),
                    "either_union_size": len(either_union),
                    "top_hit": int(ds in top_union),
                    "bottom_hit": int(ds in bot_union),
                    "either_hit": int(ds in either_union),
                    # baseline conditional on the realised draws: |union|/10
                    "top_base": len(top_union) / 10,
                    "bottom_base": len(bot_union) / 10,
                    "either_base": len(either_union) / 10,
                    "top_digits": "".join(sorted(top_union)),
                    "bottom_digits": "".join(sorted(bot_union)),
                    "either_digits": "".join(sorted(either_union)),
                }
            )

    # ---- headline metrics ---------------------------------------------------
    def metrics(sub, key, base):
        n = len(sub)
        k = sum(x[key] for x in sub)
        p = sum(x[base] for x in sub) / n if n else None
        return {"n": n, "hits": k, "rate": k / n if n else None, "expected_rate": p, "lift_pp": 100 * (k / n - p) if n else None}

    overall = {
        "top": metrics(recs, "top_hit", "top_base"),
        "bottom": metrics(recs, "bottom_hit", "bottom_base"),
        "either": metrics(recs, "either_hit", "either_base"),
    }

    # ---- within-day permutation: shuffle digits among hours -----------------
    byday = defaultdict(list)
    for i, r in enumerate(recs):
        byday[r["trading_day"]].append(i)
    digits = np.array([r["digit"] for r in recs])
    top = np.array([r["top_hit"] for r in recs])
    bot = np.array([r["bottom_hit"] for r in recs])
    either = np.array([r["either_hit"] for r in recs])
    obs = np.array([top.sum(), bot.sum(), either.sum()])

    def membership(field):
        m = np.zeros((len(recs), 10), dtype=np.int8)
        for i, r in enumerate(recs):
            for d in range(10):
                m[i, d] = int(str(d) in r[f"{field}_digits"])
        return m

    top_membership = membership("top")
    bot_membership = membership("bottom")
    either_membership = membership("either")

    B = 20000
    sims = np.zeros((B, 3), dtype=np.int32)
    rng = np.random.default_rng(20261108)
    order = np.arange(len(recs))
    for b in range(B):
        shuffled = np.empty_like(digits)
        for idxs in byday.values():
            idxs = np.asarray(idxs)
            shuffled[idxs] = rng.permutation(digits[idxs])
        sims[b, 0] = top_membership[order, shuffled].sum()
        sims[b, 1] = bot_membership[order, shuffled].sum()
        sims[b, 2] = either_membership[order, shuffled].sum()

    p_perm = [(1 + int((sims[:, j] >= obs[j]).sum())) / (B + 1) for j in range(3)]

    # ---- day bootstrap ------------------------------------------------------
    days = sorted(byday)
    day_hits = {k: [] for k in ("top", "bottom", "either")}
    day_base = {k: [] for k in ("top", "bottom", "either")}
    for day in days:
        idxs = byday[day]
        for key, base in (("top", "top_base"), ("bottom", "bottom_base"), ("either", "either_base")):
            day_hits[key].append(sum(recs[i][f"{key}_hit"] for i in idxs))
            day_base[key].append(sum(recs[i][base] for i in idxs))
    boot = {}
    for key in ("top", "bottom", "either"):
        h = np.array(day_hits[key], dtype=float)
        e = np.array(day_base[key], dtype=float)
        n = np.array([len(byday[d]) for d in days], dtype=float)
        rates = []
        for _ in range(10000):
            pick = RNG.integers(0, len(days), len(days))
            rates.append((h[pick].sum() - e[pick].sum()) / n[pick].sum())
        boot[key] = {
            "observed_lift_pp": 100 * (h.sum() - e.sum()) / n.sum(),
            "boot_mean_pp": 100 * float(np.mean(rates)),
            "boot_ci_low_pp": 100 * float(np.percentile(rates, 2.5)),
            "boot_ci_high_pp": 100 * float(np.percentile(rates, 97.5)),
            "boot_p_gt_0": float((np.array(rates) > 0).mean()),
        }

    # ---- chronological split ------------------------------------------------
    cut = int(0.7 * len(days))
    early_days = set(days[:cut])
    late_days = set(days[cut:])
    split = {}
    for name, ds in (("first_70pct", early_days), ("last_30pct", late_days)):
        sub = [r for r in recs if r["trading_day"] in ds]
        split[name] = {k: metrics(sub, f"{k}_hit", f"{k}_base") for k in ("top", "bottom", "either")}

    # ---- per day, per hour, per month --------------------------------------
    per_day = []
    for day in days:
        sub = [r for r in recs if r["trading_day"] == day]
        per_day.append(
            {
                "trading_day": day,
                "n_hours": len(sub),
                "top_hits": sum(r["top_hit"] for r in sub),
                "top_expected": round(sum(r["top_base"] for r in sub), 2),
                "bottom_hits": sum(r["bottom_hit"] for r in sub),
                "bottom_expected": round(sum(r["bottom_base"] for r in sub), 2),
                "either_hits": sum(r["either_hit"] for r in sub),
                "either_expected": round(sum(r["either_base"] for r in sub), 2),
            }
        )
    per_hour = []
    for h in sorted({r["hour_label"] for r in recs}):
        sub = [r for r in recs if r["hour_label"] == h]
        per_hour.append(
            {
                "hour_label": h,
                "n": len(sub),
                "top_hits": sum(r["top_hit"] for r in sub),
                "top_expected": round(sum(r["top_base"] for r in sub), 2),
                "bottom_hits": sum(r["bottom_hit"] for r in sub),
                "bottom_expected": round(sum(r["bottom_base"] for r in sub), 2),
                "either_hits": sum(r["either_hit"] for r in sub),
                "either_expected": round(sum(r["either_base"] for r in sub), 2),
            }
        )
    per_month = []
    for month in sorted({r["trading_day"][:7] for r in recs}):
        sub = [r for r in recs if r["trading_day"].startswith(month)]
        per_month.append(
            {
                "month": month,
                "n": len(sub),
                "top_rate": sum(r["top_hit"] for r in sub) / len(sub),
                "top_expected": sum(r["top_base"] for r in sub) / len(sub),
                "bottom_rate": sum(r["bottom_hit"] for r in sub) / len(sub),
                "bottom_expected": sum(r["bottom_base"] for r in sub) / len(sub),
                "either_rate": sum(r["either_hit"] for r in sub) / len(sub),
                "either_expected": sum(r["either_base"] for r in sub) / len(sub),
            }
        )

    # ---- is the table derived from past results? ---------------------------
    # candidate deterministic mappings from the previous day's result at the
    # same hour to the next day's posted digit
    rows_by_day_hour = defaultdict(dict)
    for r in rows:
        rows_by_day_hour[r["trading_day"]][int(r["round"])] = r
    # map hour label to round numbers: 06:00 -> 1, ..., 23:00 -> 69,
    # 24:00 -> 73, 01:00 -> 77, 02:00 -> 81, 03:00 -> 85
    hour_to_round = {6 + i: 1 + 4 * i for i in range(18)}
    hour_to_round.update({24: 73, 1: 77, 2: 81, 3: 85})
    day_list = sorted(tables)
    mapping_tests = {}
    for name, fn in {
        "prev_top_last": lambda t, b: int(t[-1]),
        "prev_top_first": lambda t, b: int(t[0]),
        "prev_bottom_last": lambda t, b: int(b[-1]),
        "prev_bottom_first": lambda t, b: int(b[0]),
        "prev_top_sum_mod10": lambda t, b: sum(map(int, t)) % 10,
        "prev_bottom_sum_mod10": lambda t, b: sum(map(int, b)) % 10,
        "prev_result_sum_mod10": lambda t, b: (sum(map(int, t)) + sum(map(int, b))) % 10,
    }.items():
        hits = 0
        n = 0
        for i, day in enumerate(day_list[1:], start=1):
            prev_day = day_list[i - 1]
            for h, info in tables[day].items():
                rnd = hour_to_round.get(h)
                if rnd is None:
                    continue
                prev = rows_by_day_hour.get(prev_day, {}).get(rnd)
                if not prev:
                    continue
                pred = fn(prev["top3"], prev["bottom2"])
                hits += int(pred == info["digit"])
                n += 1
        mapping_tests[name] = {"n": n, "hits": hits, "rate": hits / n if n else None}

    # same-day earlier-hour mapping
    sameday = {}
    for name, fn in {
        "prev_hour_bottom_last": lambda r: int(r["bottom2"][-1]),
        "prev_hour_top_last": lambda r: int(r["top3"][-1]),
        "prev_hour_bottom_sum_mod10": lambda r: sum(map(int, r["bottom2"])) % 10,
    }.items():
        hits = 0
        n = 0
        for day in day_list:
            for h in sorted(tables[day]):
                rnd = hour_to_round.get(h)
                if rnd is None or rnd - 4 < 1:
                    continue
                prev = rows_by_day_hour.get(day, {}).get(rnd - 4)
                if not prev:
                    continue
                hits += int(fn(prev) == tables[day][h]["digit"])
                n += 1
        sameday[name] = {"n": n, "hits": hits, "rate": hits / n if n else None}

    # day-to-day correlation of the full vector (same hour)
    vectors = {d: {h: v["digit"] for h, v in tables[d].items()} for d in day_list}
    same_hour_matches = []
    for i in range(1, len(day_list)):
        a, b = day_list[i - 1], day_list[i]
        common = set(vectors[a]) & set(vectors[b])
        if common:
            same_hour_matches.append(sum(vectors[a][h] == vectors[b][h] for h in common) / len(common))
    same_hour_rate = float(np.mean(same_hour_matches)) if same_hour_matches else None

    # digit frequency
    digit_freq = Counter(v["digit"] for d in tables.values() for v in d.values())

    # author copying
    author_days = defaultdict(set)
    for p in posts:
        author_days[p["author"]].add(trading_day(datetime.fromisoformat(p["posted"])))

    # ---- write outputs ------------------------------------------------------
    with open(OUT / "hourly_evaluated_hours.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(recs[0].keys()))
        w.writeheader()
        w.writerows(recs)
    with open(OUT / "hourly_per_day.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(per_day[0].keys()))
        w.writeheader()
        w.writerows(per_day)
    with open(OUT / "hourly_per_hour.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(per_hour[0].keys()))
        w.writeheader()
        w.writerows(per_hour)
    with open(OUT / "hourly_per_month.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(per_month[0].keys()))
        w.writeheader()
        w.writerows(per_month)

    summary = {
        "daily_tables": len(tables),
        "table_conflicts": conflicts,
        "forecast_posts": len(posts),
        "authors": dict(Counter(p["author"] for p in posts)),
        "author_trading_days": {k: len(v) for k, v in author_days.items()},
        "evaluated_hours": len(recs),
        "excluded_post_after_target": excluded_post_after,
        "excluded_missing_draws": excluded_missing_draws,
        "date_range": [recs[0]["target_hour"], recs[-1]["target_hour"]],
        "overall": overall,
        "within_day_permutation_p": {"top": p_perm[0], "bottom": p_perm[1], "either": p_perm[2]},
        "permutation_observed": {"top": int(obs[0]), "bottom": int(obs[1]), "either": int(obs[2])},
        "permutation_mean": sims.mean(axis=0).round(2).tolist(),
        "permutation_sd": sims.std(axis=0).round(2).tolist(),
        "day_bootstrap": boot,
        "chronological_split": split,
        "digit_frequency_in_table": dict(sorted(digit_freq.items())),
        "same_hour_next_day_match_rate": same_hour_rate,
        "mapping_from_previous_day": mapping_tests,
        "mapping_from_previous_hour_same_day": sameday,
        "note": "Authors repost the same daily table; they are not independent forecasters. Inference treats the day as the unit.",
    }
    (OUT / "hourly_audit_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    # precompute membership matrices after recs exist; done inside main below
    main()
