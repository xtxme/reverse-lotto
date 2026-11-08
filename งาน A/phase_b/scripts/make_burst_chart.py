#!/usr/bin/env python3
"""Final timestamp-burst chart: per-round concentration, offset spikes,
largest-burst user diversity, and duplicate-group ownership."""

import csv
import json
import os
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
EVID = os.path.join(ROOT, "evidence")
CHARTS = os.path.join(ROOT, "charts")
ROUNDS = list(range(53, 60))


def main():
    summ = {}
    with open(os.path.join(EVID, "round_summary.csv")) as f:
        for r in csv.DictReader(f):
            summ[int(r["round"])] = r

    uc = json.load(open(os.path.join(EVID, "user_concentration.json")))
    uc = {int(k) - 176: v for k, v in uc.items()}

    # per-second offset
    offsets = defaultdict(lambda: defaultdict(int))
    with open(os.path.join(EVID, "per_second.csv")) as f:
        for r in csv.DictReader(f):
            rnd = int(r["round"])
            hh, mm, ss = map(int, r["ts"][11:].split(":"))
            close_min = 19 * 60 + 15 * (rnd - 53)
            rel = int(round((hh * 60 + mm + ss / 60 - close_min) * 60))
            offsets[rnd][rel] += int(r["count"])

    dup = {}
    with open(os.path.join(EVID, "duplicate_stats.csv")) as f:
        for r in csv.DictReader(f):
            dup[int(r["round"])] = r

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    ax = axes[0, 0]
    maxps = [int(summ[r]["max_per_second"]) for r in ROUNDS]
    distinct = [int(summ[r]["distinct_seconds"]) for r in ROUNDS]
    meanps = [int(summ[r]["n"]) / max(1, int(summ[r]["distinct_seconds"])) for r in ROUNDS]
    x = np.arange(len(ROUNDS))
    ax.bar(x - 0.22, maxps, width=0.22, label="max per second", color="#c0392b")
    ax.bar(x, meanps, width=0.22, label="mean per active second", color="#7f8c8d")
    ax.bar(x + 0.22, distinct, width=0.22, label="distinct seconds", color="#2980b9")
    ax.set_xticks(x); ax.set_xticklabels([str(r) for r in ROUNDS])
    ax.set_xlabel("Round"); ax.set_ylabel("Count")
    ax.set_title("A. Burst concentration by round")
    ax.legend(frameon=False, fontsize=8)
    ax.grid(axis="y", alpha=0.25)

    ax = axes[0, 1]
    for r in ROUNDS:
        xs = sorted(offsets[r])
        ys = [offsets[r][k] for k in xs]
        ax.plot(xs, ys, linewidth=1.1, alpha=0.75, label=f"round {r}")
    ax.axvline(103, color="#c0392b", linestyle="--", linewidth=1.2, label="+103 s")
    ax.axvline(119, color="#8e44ad", linestyle="--", linewidth=1.2, label="+119 s")
    ax.set_xlim(0, 125)
    ax.set_xlabel("Seconds relative to betting close")
    ax.set_ylabel("Submissions in that second")
    ax.set_title("B. Two fixed offset spikes in every round")
    ax.legend(frameon=False, fontsize=6, ncol=2)
    ax.grid(alpha=0.25)

    ax = axes[1, 0]
    for r in ROUNDS:
        tb = uc[r]["top_burst"]
        if tb:
            ax.scatter(tb["count"], tb["distinct_users"], s=80, label=f"round {r}")
            ax.annotate(str(r), (tb["count"], tb["distinct_users"]),
                        textcoords="offset points", xytext=(4, 4), fontsize=8)
    ax.plot([0, 70], [0, 70], color="black", linestyle="--", linewidth=1, label="1 user per row")
    ax.set_xlabel("Rows in largest same-second burst")
    ax.set_ylabel("Distinct masked users in that burst")
    ax.set_title("C. Largest burst: rows vs distinct users")
    ax.set_xlim(0, 70); ax.set_ylim(0, 70)
    ax.legend(frameon=False, fontsize=7)
    ax.grid(alpha=0.25)

    ax = axes[1, 1]
    same = [uc[r]["duplicate_class"]["allSame"] for r in ROUNDS]
    mixed = [uc[r]["duplicate_class"]["mixed"] for r in ROUNDS]
    diff = [uc[r]["duplicate_class"]["allDiff"] for r in ROUNDS]
    x = np.arange(len(ROUNDS))
    ax.bar(x, same, label="same user", color="#c0392b")
    ax.bar(x, mixed, bottom=same, label="mixed users", color="#f39c12")
    ax.bar(x, diff, bottom=np.array(same) + np.array(mixed), label="all different users", color="#7f8c8d")
    ax.set_xticks(x); ax.set_xticklabels([str(r) for r in ROUNDS])
    ax.set_xlabel("Round"); ax.set_ylabel("Duplicate groups")
    ax.set_title("D. Duplicate values are mostly one user repeating")
    ax.legend(frameon=False, fontsize=8)
    ax.grid(axis="y", alpha=0.25)

    fig.suptitle("Timestamp collisions and duplicate numbers have different causes", fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    out = os.path.join(CHARTS, "timestamp_burst_analysis.png")
    fig.savefig(out, dpi=170)
    plt.close(fig)
    print("wrote", out, os.path.getsize(out))


if __name__ == "__main__":
    main()
