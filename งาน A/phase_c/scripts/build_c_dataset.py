#!/usr/bin/env python3
"""
Phase C dataset builder.

Inputs : phase_c/evidence/raw_rounds_hash/round_<period>.json
Outputs: phase_c/evidence/combined_events.csv
         phase_c/c_round_summary.csv
         phase_c/c_ordering_inversions.csv
         phase_c/evidence/c_burst_overlap.csv
         phase_c/evidence/c_same_user_duplicates.csv
         phase_c/evidence/c_account_summary.csv

The only account identifier retained is a truncated SHA-256 of the masked
username (prefix "phase_c:"). Raw masked usernames are never written.
"""

import csv
import datetime as dt
import hashlib
import json
import os
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
EVID = os.path.join(ROOT, "evidence")
RAW = os.path.join(EVID, "raw_rounds_hash")
ANCHOR_ROUND = 52
ANCHOR_CLOSE = dt.datetime(2026, 11, 7, 18, 45, 0)


def period_to_round(pid):
    if 229 <= pid <= 235:
        return pid - 176
    if 236 <= pid <= 244:
        return pid - 176
    raise ValueError(pid)


def parse_ts(s):
    d, t = s.split()
    day, month, year = map(int, d.split("/"))
    year -= 543
    hh, mm, ss = map(int, t.split(":"))
    return dt.datetime(year, month, day, hh, mm, ss)


def close_for_round(r):
    return ANCHOR_CLOSE + dt.timedelta(minutes=15 * (r - ANCHOR_ROUND))


def bucket(offset_s):
    if offset_s < -120:
        return "before_shoot_open"
    if offset_s < 0:
        return "pre_close_shoot_window"
    if offset_s <= 120:
        return "post_close_shoot_window"
    return "after_shoot_close"


def main():
    events = []
    for fn in sorted(os.listdir(RAW)):
        if not fn.endswith(".json"):
            continue
        raw = json.load(open(os.path.join(RAW, fn)))
        if isinstance(raw, str):
            raw = json.loads(raw)
        pid = raw["id"]
        rnd = period_to_round(pid)
        close = close_for_round(rnd)
        for row in raw["rows"]:
            ts = parse_ts(row["ts"])
            off = (ts - close).total_seconds()
            events.append({
                "round": rnd, "period_id": pid, "seq": row["seq"],
                "number": row["num"], "ts_iso": ts.strftime("%Y-%m-%dT%H:%M:%S+07:00"),
                "offset_s": int(off), "user_hash": row.get("uh", ""),
                "bucket": bucket(off),
            })
    events.sort(key=lambda e: (e["round"], e["seq"]))

    with open(os.path.join(EVID, "combined_events.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["round", "period_id", "seq", "number", "ts_iso", "offset_s", "user_hash", "bucket"])
        for e in events:
            w.writerow([e["round"], e["period_id"], e["seq"], e["number"], e["ts_iso"],
                        e["offset_s"], e["user_hash"], e["bucket"]])

    rounds = sorted(set(e["round"] for e in events))
    summary = []
    inversions = []
    burst_rows = []
    dup_rows = []
    acct_rows = []
    for r in rounds:
        rr = [e for e in events if e["round"] == r]
        rr.sort(key=lambda x: x["seq"])
        n = len(rr)
        pid = rr[0]["period_id"]
        ts = [e["ts_iso"] for e in rr]
        by_ts = Counter(ts)
        max_ts, max_n = by_ts.most_common(1)[0]
        inv = 0
        for i in range(n - 1):
            if rr[i]["ts_iso"] < rr[i + 1]["ts_iso"]:
                inv += 1
                inversions.append({
                    "round": r, "period_id": pid,
                    "seq_a": rr[i]["seq"], "seq_b": rr[i + 1]["seq"],
                    "ts_a": rr[i]["ts_iso"], "ts_b": rr[i + 1]["ts_iso"],
                    "delta_s": (dt.datetime.fromisoformat(rr[i + 1]["ts_iso"]) -
                                dt.datetime.fromisoformat(rr[i]["ts_iso"])).total_seconds(),
                })
        row16 = rr[15]
        # duplicates
        by_num = defaultdict(list)
        for e in rr:
            by_num[e["number"]].append(e)
        dup_groups = [(k, v) for k, v in by_num.items() if len(v) > 1]
        same = mixed = diff = 0
        for _, g in dup_groups:
            us = set(x["user_hash"] for x in g)
            if len(us) == 1:
                same += 1
            elif len(us) == len(g):
                diff += 1
            else:
                mixed += 1
        dup_rows.append({
            "round": r, "period_id": pid, "duplicate_groups": len(dup_groups),
            "same_user": same, "mixed": mixed, "all_different": diff,
            "duplicate_entries": n - len(by_num),
            "colliding_pairs": sum(len(g) * (len(g) - 1) // 2 for _, g in dup_groups),
        })
        # +103/+119 exact offsets
        g103 = [e for e in rr if e["offset_s"] == 103]
        g119 = [e for e in rr if e["offset_s"] == 119]
        u103 = set(e["user_hash"] for e in g103)
        u119 = set(e["user_hash"] for e in g119)
        n103 = set(e["number"] for e in g103)
        n119 = set(e["number"] for e in g119)
        inter = len(u103 & u119)
        union = len(u103 | u119)
        burst_rows.append({
            "round": r, "period_id": pid,
            "b103_rows": len(g103), "b103_users": len(u103), "b103_unique_numbers": len(n103),
            "b119_rows": len(g119), "b119_users": len(u119), "b119_unique_numbers": len(n119),
            "user_intersection": inter, "user_union": union,
            "user_jaccard": round(inter / union, 3) if union else None,
            "number_intersection": len(n103 & n119),
        })
        # account summary
        uc = Counter(e["user_hash"] for e in rr if e["user_hash"])
        acct_rows.append({
            "round": r, "period_id": pid, "n": n,
            "distinct_user_hashes": len(uc),
            "users_with_2plus_rows": sum(1 for v in uc.values() if v >= 2),
            "max_rows_per_user": max(uc.values()) if uc else 0,
            "rows_without_user_hash": sum(1 for e in rr if not e["user_hash"]),
        })
        summary.append({
            "round": r, "period_id": pid, "n": n,
            "first_ts": min(ts), "last_ts": max(ts),
            "before_close": sum(1 for e in rr if e["offset_s"] < 0),
            "after_close": sum(1 for e in rr if e["offset_s"] >= 0),
            "before_shoot_open": sum(1 for e in rr if e["bucket"] == "before_shoot_open"),
            "pre_close_window": sum(1 for e in rr if e["bucket"] == "pre_close_shoot_window"),
            "post_close_window": sum(1 for e in rr if e["bucket"] == "post_close_shoot_window"),
            "after_shoot_close": sum(1 for e in rr if e["bucket"] == "after_shoot_close"),
            "distinct_seconds": len(by_ts), "max_per_second": max_n, "max_second": max_ts,
            "inversions": inv,
            "row16_number": row16["number"], "row16_ts": row16["ts_iso"],
            "row16_offset_s": row16["offset_s"],
            "row16_in_119_group": row16["offset_s"] == 119,
            "b103_rows": len(g103), "b119_rows": len(g119),
        })

    with open(os.path.join(ROOT, "c_round_summary.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0].keys()))
        w.writeheader(); w.writerows(summary)
    with open(os.path.join(ROOT, "c_ordering_inversions.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(inversions[0].keys()))
        w.writeheader(); w.writerows(inversions)
    with open(os.path.join(EVID, "c_burst_overlap.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(burst_rows[0].keys()))
        w.writeheader(); w.writerows(burst_rows)
    with open(os.path.join(EVID, "c_same_user_duplicates.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(dup_rows[0].keys()))
        w.writeheader(); w.writerows(dup_rows)
    with open(os.path.join(EVID, "c_account_summary.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(acct_rows[0].keys()))
        w.writeheader(); w.writerows(acct_rows)

    print(f"rounds={len(rounds)} events={len(events)} inversions={len(inversions)}")
    print("inversion deltas:", Counter(x["delta_s"] for x in inversions))
    print("row16 +119:", sum(1 for s in summary if s["row16_in_119_group"]), "/", len(summary))
    print("row16 offsets:", Counter(s["row16_offset_s"] for s in summary))
    print("total b103:", sum(s["b103_rows"] for s in summary),
          "total b119:", sum(s["b119_rows"] for s in summary))
    print("duplicate entries total:", sum(d["duplicate_entries"] for d in dup_rows),
          "pairs:", sum(d["colliding_pairs"] for d in dup_rows))
    print("same-user groups:", sum(d["same_user"] for d in dup_rows),
          "mixed:", sum(d["mixed"] for d in dup_rows),
          "diff:", sum(d["all_different"] for d in dup_rows))


if __name__ == "__main__":
    main()
