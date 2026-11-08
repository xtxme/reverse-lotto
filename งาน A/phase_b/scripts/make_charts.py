#!/usr/bin/env python3
"""Phase B charts (matplotlib, English labels for portable fonts)."""

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
os.makedirs(CHARTS, exist_ok=True)

ROUNDS = list(range(53, 60))


def load_events():
    rows = []
    with open(os.path.join(EVID, "submission_events.csv")) as f:
        for r in csv.DictReader(f):
            r["round"] = int(r["round"])
            r["seq"] = int(r["seq"])
            r["minutes_from_close"] = float(r["minutes_from_close"])
            rows.append(r)
    return rows


def chart_timing(events):
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.2))

    # Panel A: aggregate 10-second bins, -180s .. +150s
    rel = np.array([e["minutes_from_close"] * 60 for e in events])
    bins = np.arange(-180, 151, 10)
    counts, _ = np.histogram(rel, bins=bins)
    centers = (bins[:-1] + bins[1:]) / 2
    ax = axes[0]
    ax.bar(centers, counts, width=9, color="#c0392b", edgecolor="white", linewidth=0.4)
    ax.axvline(0, color="black", linestyle="--", linewidth=1.2, label="betting close")
    ax.axvline(120, color="#2c3e50", linestyle=":", linewidth=1.2, label="shoot close (+120 s)")
    ax.set_xlabel("Seconds relative to betting close")
    ax.set_ylabel("Submissions (10-second bins)")
    ax.set_title(f"A. All {len(events):,} submissions, 7 rounds")
    ax.legend(frameon=False, fontsize=9)
    ax.grid(axis="y", alpha=0.25)

    # Panel B: cumulative share per round
    ax = axes[1]
    for r in ROUNDS:
        rr = sorted([e["minutes_from_close"] * 60 for e in events if e["round"] == r])
        y = np.arange(1, len(rr) + 1) / len(rr)
        ax.plot(rr, y, marker="", linewidth=1.6, label=f"round {r} (n={len(rr)})")
    ax.axvline(0, color="black", linestyle="--", linewidth=1.2)
    ax.axvline(120, color="#2c3e50", linestyle=":", linewidth=1.2)
    ax.set_xlim(-180, 150)
    ax.set_ylim(0, 1.02)
    ax.set_xlabel("Seconds relative to betting close")
    ax.set_ylabel("Cumulative share of submissions")
    ax.set_title("B. Within-round cumulative distribution")
    ax.legend(frameon=False, fontsize=7, ncol=2)
    ax.grid(alpha=0.25)

    fig.suptitle("Yeekee submission timing: almost all numbers arrive after betting closes", fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(os.path.join(CHARTS, "submission_timing_distribution.png"), dpi=170)
    plt.close(fig)


def chart_bursts():
    # per-round summary
    summ = {}
    with open(os.path.join(EVID, "round_summary.csv")) as f:
        for r in csv.DictReader(f):
            summ[int(r["round"])] = r

    # user concentration
    uc_raw = json.load(open(os.path.join(EVID, "user_concentration.json")))
    uc = {int(k) - 176: v for k, v in uc_raw.items()}  # period 229 -> round 53

    fig, axes = plt.subplots(1, 3, figsize=(16, 5.2))

    # A: max/mean/distinct
    ax = axes[0]
    rs = ROUNDS
    maxps = [int(summ[r]["max_per_second"]) for r in rs]
    distinct = [int(summ[r]["distinct_seconds"]) for r in rs]
    meanps = [int(summ[r]["n"]) / max(1, int(summ[r]["distinct_seconds"])) for r in rs]
    x = np.arange(len(rs))
    ax.bar(x - 0.22, maxps, width=0.22, label="max per second", color="#c0392b")
    ax.bar(x, meanps, width=0.22, label="mean per active second", color="#7f8c8d")
    ax.bar(x + 0.22, distinct, width=0.22, label="distinct seconds", color="#2980b9")
    ax.set_xticks(x); ax.set_xticklabels([str(r) for r in rs])
    ax.set_xlabel("Round"); ax.set_ylabel("Count")
    ax.set_title("A. Burst concentration by round")
    ax.legend(frameon=False, fontsize=8)
    ax.grid(axis="y", alpha=0.25)

    # B: distribution of per-second counts (log y)
    ax = axes[1]
    per_second = []
    with open(os.path.join(EVID, "per_second.csv")) as f:
        for r in csv.DictReader(f):
            per_second.append(int(r["count"]))
    vals, counts = np.unique(per_second, return_counts=True)
    ax.scatter(vals, counts, s=18, color="#c0392b")
    ax.set_yscale("log")
    ax.set_xscale("log")
    ax.set_xlabel("Submissions in one second")
    ax.set_ylabel("Number of seconds (log)")
    ax.set_title("B. Per-second count distribution")
    ax.grid(alpha=0.25, which="both")

    # C: top burst vs distinct users
    ax = axes[2]
    for r in rs:
        tb = uc[r]["top_burst"]
        if tb:
            ax.scatter(tb["count"], tb["distinct_users"], s=70, label=f"round {r}")
            ax.annotate(str(r), (tb["count"], tb["distinct_users"]), textcoords="offset points",
                        xytext=(4, 4), fontsize=8)
    ax.plot([0, 70], [0, 70], color="black", linestyle="--", linewidth=1, label="1 user per row")
    ax.set_xlabel("Rows in largest same-second burst")
    ax.set_ylabel("Distinct masked users in that burst")
    ax.set_title("C. Largest burst: rows vs distinct users")
    ax.set_xlim(0, 70); ax.set_ylim(0, 70)
    ax.legend(frameon=False, fontsize=7)
    ax.grid(alpha=0.25)

    fig.suptitle("Timestamp collisions are multi-user bursts, not a single automated client", fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(os.path.join(CHARTS, "timestamp_burst_analysis.png"), dpi=170)
    plt.close(fig)


def chart_duplicates():
    # observed duplicate entries vs uniform expectation, and frequency distribution
    dup = []
    with open(os.path.join(EVID, "duplicate_stats.csv")) as f:
        for r in csv.DictReader(f):
            dup.append(r)
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.2))

    ax = axes[0]
    rs = [int(r["round"]) for r in dup]
    obs = [int(r["duplicate_entries"]) for r in dup]
    # expected n - E[unique] under uniform; E[unique]=100000*(1-(1-1/100000)^n)
    exp = []
    for r in dup:
        n = int(r["n"])
        u = 100000 * (1 - (1 - 1 / 100000) ** n)
        exp.append(n - u)
    x = np.arange(len(rs))
    ax.bar(x - 0.2, obs, width=0.4, label="observed duplicate entries", color="#c0392b")
    ax.bar(x + 0.2, exp, width=0.4, label="uniform-model expectation", color="#7f8c8d")
    ax.set_xticks(x); ax.set_xticklabels([str(r) for r in rs])
    ax.set_xlabel("Round"); ax.set_ylabel("n − unique")
    ax.set_title("A. Duplicate entries vs uniform null")
    ax.legend(frameon=False, fontsize=8)
    ax.grid(axis="y", alpha=0.25)

    # B: pooled frequency distribution
    freq = {}
    with open(os.path.join(ROOT, "number_frequency.csv")) as f:
        for r in csv.DictReader(f):
            freq[int(r["total_count"])] = freq.get(int(r["total_count"]), 0) + 1
    ax = axes[1]
    ks = sorted(freq)
    ax.bar([str(k) for k in ks], [freq[k] for k in ks], color="#2980b9")
    ax.set_yscale("log")
    ax.set_xlabel("Times a number appears in 7 rounds")
    ax.set_ylabel("Number of distinct values (log)")
    ax.set_title("B. Pooled frequency distribution (1,097 submissions)")
    ax.grid(axis="y", alpha=0.25, which="both")

    fig.suptitle("Repeated 5-digit values are far above the uniform model", fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(os.path.join(CHARTS, "duplicate_distribution.png"), dpi=170)
    plt.close(fig)


def main():
    events = load_events()
    chart_timing(events)
    chart_bursts()
    chart_duplicates()
    print("charts written to", CHARTS)
    for f in sorted(os.listdir(CHARTS)):
        print(" ", f, os.path.getsize(os.path.join(CHARTS, f)))


if __name__ == "__main__":
    main()
