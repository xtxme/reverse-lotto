#!/usr/bin/env python3
"""
Phase B core analysis over the reconstructed 7-round dataset.

Produces:
  number_frequency.csv
  evidence/partial_vs_final.csv
  evidence/cross_round_stats.json
  evidence/duplicate_stats.csv

All inputs are sanitized: round, seq, 5-digit number, timestamp only.
"""

import csv
import json
import math
import os
from collections import Counter, defaultdict

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
EVID = os.path.join(ROOT, "evidence")

ROUNDS = list(range(53, 60))
PERIOD = {r: 176 + r for r in ROUNDS}  # 53->229 ... 59->235


def load_events():
    rows = []
    with open(os.path.join(EVID, "submission_events.csv")) as f:
        for r in csv.DictReader(f):
            r["round"] = int(r["round"])
            r["period_id"] = int(r["period_id"])
            r["seq"] = int(r["seq"])
            r["minutes_from_close"] = float(r["minutes_from_close"])
            rows.append(r)
    return rows


def load_summaries():
    out = {}
    with open(os.path.join(EVID, "round_summary.csv")) as f:
        for r in csv.DictReader(f):
            out[int(r["round"])] = r
    return out


def main():
    events = load_events()
    summaries = load_summaries()
    by_round = defaultdict(list)
    for e in events:
        by_round[e["round"]].append(e)
    for r in by_round:
        by_round[r].sort(key=lambda x: x["seq"])

    # ---------- per-round duplicate stats ----------
    dup_rows = []
    for r in ROUNDS:
        nums = [e["number"] for e in by_round[r]]
        c = Counter(nums)
        n = len(nums)
        uniq = len(c)
        dup_entries = n - uniq
        collision_pairs = sum(v * (v - 1) // 2 for v in c.values())
        max_freq = max(c.values())
        top = c.most_common(5)
        dup_rows.append({
            "round": r, "period_id": PERIOD[r], "n": n, "unique": uniq,
            "duplicate_entries": dup_entries, "duplicate_rate_pct": round(100 * dup_entries / n, 2),
            "colliding_pairs": collision_pairs, "max_frequency": max_freq,
            "top_numbers": "|".join(f"{k}:{v}" for k, v in top),
        })
    with open(os.path.join(EVID, "duplicate_stats.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(dup_rows[0].keys()))
        w.writeheader(); w.writerows(dup_rows)

    # ---------- pooled number frequency ----------
    total = Counter()
    per_round = defaultdict(Counter)
    for e in events:
        total[e["number"]] += 1
        per_round[e["round"]][e["number"]] += 1
    with open(os.path.join(ROOT, "number_frequency.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["number", "total_count", "rounds_present"] + [f"round_{r}" for r in ROUNDS])
        for num, cnt in sorted(total.items(), key=lambda kv: (-kv[1], kv[0])):
            rounds_present = sum(1 for r in ROUNDS if per_round[r][num])
            w.writerow([num, cnt, rounds_present] + [per_round[r][num] for r in ROUNDS])

    # ---------- cross-round overlap ----------
    sets = {r: set(per_round[r]) for r in ROUNDS}
    jaccard = {}
    for i, a in enumerate(ROUNDS):
        for b in ROUNDS[i + 1:]:
            inter = len(sets[a] & sets[b])
            uni = len(sets[a] | sets[b])
            jaccard[f"{a}-{b}"] = round(inter / uni, 4) if uni else 0.0
    multi_round = [n for n, c in total.items() if sum(1 for r in ROUNDS if per_round[r][n]) >= 2]
    three_plus = [n for n, c in total.items() if sum(1 for r in ROUNDS if per_round[r][n]) >= 3]

    # split-half persistence (first 3 rounds vs last 4)
    first = Counter()
    second = Counter()
    for r in ROUNDS[:3]:
        first.update(per_round[r])
    for r in ROUNDS[3:]:
        second.update(per_round[r])
    keys = sorted(set(first) | set(second))
    x = np.array([first.get(k, 0) for k in keys], dtype=float)
    y = np.array([second.get(k, 0) for k in keys], dtype=float)
    if x.std() > 0 and y.std() > 0:
        split_r = float(np.corrcoef(x, y)[0, 1])
    else:
        split_r = 0.0
    # top-20 overlap between halves
    top_first = [k for k, _ in first.most_common(20)]
    top_second = [k for k, _ in second.most_common(20)]
    top_overlap = len(set(top_first) & set(top_second))

    # digit patterns
    first_digit = Counter(n[0] for n in total.elements())
    last_digit = Counter(n[-1] for n in total.elements())
    all_same = sum(1 for n in total.elements() if len(set(n)) == 1)
    four_same = sum(1 for n in total.elements() if max(Counter(n).values()) == 4)
    palindromes = sum(1 for n in total.elements() if n == n[::-1])

    # concentration
    counts = np.array(sorted(total.values(), reverse=True), dtype=float)
    top10_share = counts[:10].sum() / counts.sum()
    hhi = float(((counts / counts.sum()) ** 2).sum())

    cross = {
        "rounds": ROUNDS,
        "total_submissions": len(events),
        "global_unique_numbers": len(total),
        "numbers_in_2plus_rounds": len(multi_round),
        "numbers_in_3plus_rounds": len(three_plus),
        "pct_numbers_in_2plus_rounds_of_all_submissions": round(100 * sum(total[n] for n in multi_round) / len(events), 2),
        "jaccard_pairwise": jaccard,
        "split_half_pearson_r_all_seen_numbers": round(split_r, 4),
        "split_half_pearson_note": "Not used as evidence: sparse 100k-category space and unequal half totals; dominated by zeros. Use pairwise overlap and recurring-number tail instead.",
        "split_half_top20_overlap": top_overlap,
        "leading_digit": {str(i): first_digit.get(str(i), 0) for i in range(10)},
        "trailing_digit": {str(i): last_digit.get(str(i), 0) for i in range(10)},
        "all_same_digits": all_same,
        "four_same_digits": four_same,
        "palindromes": palindromes,
        "top10_share": round(float(top10_share), 4),
        "hhi": round(hhi, 6),
        "top_recurring": [{"number": n, "count": int(total[n]),
                           "rounds": [r for r in ROUNDS if per_round[r][n]]}
                          for n, _ in total.most_common(25)],
    }
    with open(os.path.join(EVID, "cross_round_stats.json"), "w") as f:
        json.dump(cross, f, indent=2, ensure_ascii=False)

    # ---------- pre-cutoff vs final ----------
    pc_rows = []
    for r in ROUNDS:
        s = summaries[r]
        close_min = 0.0
        partial = [e for e in by_round[r] if e["minutes_from_close"] < close_min]
        # display order is seq ascending; newest-first among partial is seq ascending too
        partial_nums = [e["number"] for e in partial]
        pn = len(partial_nums)
        psum = sum(int(n) for n in partial_nums)
        p16 = partial_nums[15] if pn >= 16 else None
        pres = (psum - int(p16)) if p16 is not None else None
        final_result = int(s["raw_result"])
        final_nums = [e["number"] for e in by_round[r]]
        future_nums = final_nums[pn:]  # not used; count/sum below
        future_sum = int(s["sum"]) - psum
        pc_rows.append({
            "round": r, "period_id": PERIOD[r], "final_n": int(s["n"]),
            "partial_n_at_close": pn, "partial_sum": psum,
            "partial_row16": p16, "partial_result_if_ended": pres,
            "final_sum": int(s["sum"]), "final_row16": s["row16"],
            "final_result": final_result,
            "partial_top3_if_ended": (f"{pres:05d}"[-3:] if pres is not None else None),
            "partial_bottom2_if_ended": (f"{pres:05d}"[:2] if pres is not None else None),
            "final_top3": s["top3"], "final_bottom2": s["bottom2"],
            "future_count": int(s["n"]) - pn, "future_sum": future_sum,
            "future_sum_mod100k": future_sum % 100000,
            "partial_sum_mod100k": psum % 100000,
            "final_sum_mod100k": int(s["sum"]) % 100000,
            "row16_same": (str(p16) == str(s["row16"])),
            "partial_top3_match": (f"{pres:05d}"[-3:] == s["top3"] if pres is not None else False),
            "partial_bottom2_match": (f"{pres:05d}"[:2] == s["bottom2"] if pres is not None else False),
        })
    with open(os.path.join(EVID, "partial_vs_final.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(pc_rows[0].keys()))
        w.writeheader(); w.writerows(pc_rows)

    # Correlations (exploratory, n=7)
    p = np.array([x["partial_sum_mod100k"] for x in pc_rows], dtype=float)
    fr = np.array([x["final_result"] % 100000 for x in pc_rows], dtype=float)
    fu = np.array([x["future_sum_mod100k"] for x in pc_rows], dtype=float)
    def corr(a, b):
        if a.std() == 0 or b.std() == 0:
            return None
        return float(np.corrcoef(a, b)[0, 1])
    corr_stats = {
        "n_rounds": len(pc_rows),
        "corr_partial_sum_mod_vs_final_result_mod": corr(p, fr),
        "corr_partial_sum_mod_vs_future_sum_mod": corr(p, fu),
        "partial_row16_matches_final": sum(1 for x in pc_rows if x["row16_same"]),
        "partial_top3_matches_final": sum(1 for x in pc_rows if x["partial_top3_match"]),
        "partial_bottom2_matches_final": sum(1 for x in pc_rows if x["partial_bottom2_match"]),
        "mean_future_count": float(np.mean([x["future_count"] for x in pc_rows])),
        "mean_future_sum": float(np.mean([x["future_sum"] for x in pc_rows])),
        "rows": pc_rows,
    }
    with open(os.path.join(EVID, "precutoff_predictive_stats.json"), "w") as f:
        json.dump(corr_stats, f, indent=2, ensure_ascii=False)

    # ---------- console report ----------
    print("duplicate stats")
    for d in dup_rows:
        print(" ", d)
    print("\ncross-round")
    for k in ("total_submissions", "global_unique_numbers", "numbers_in_2plus_rounds",
              "numbers_in_3plus_rounds", "split_half_pearson_r_all_seen_numbers",
              "split_half_top20_overlap", "top10_share", "hhi",
              "all_same_digits", "four_same_digits", "palindromes"):
        print(f"  {k}: {cross[k]}")
    print("\npre-cutoff vs final")
    for x in pc_rows:
        print(" ", {k: x[k] for k in ("round", "partial_n_at_close", "partial_row16",
                                     "final_row16", "partial_top3_if_ended", "final_top3",
                                     "partial_bottom2_if_ended", "final_bottom2",
                                     "future_count", "future_sum_mod100k")})
    print("\ncorrelations", {k: corr_stats[k] for k in corr_stats if k.startswith("corr_") or k.endswith("matches_final")})


if __name__ == "__main__":
    main()
