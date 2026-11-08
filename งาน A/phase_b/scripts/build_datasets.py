#!/usr/bin/env python3
"""
Phase B dataset builder.

Reads the sanitized raw round JSON collected in Phase B, reconstructs the
submission timeline, and validates the Phase A claims about timestamps,
sums, and the position-16 rule.

Inputs : phase_b/evidence/raw_rounds/round_<periodId>.json
Outputs: phase_b/evidence/submission_events.csv
         phase_b/evidence/round_summary.csv
         phase_b/submission_timeline.csv   (per-round summary)
         phase_b/timestamp_collisions.csv  (per-timestamp collisions)
         phase_b/evidence/per_second.csv
"""

import csv
import datetime as dt
import json
import os
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                 # /Users/icy/research/phase_b
EVID = os.path.join(ROOT, "evidence")
RAW = os.path.join(EVID, "raw_rounds")

PERIOD_TO_ROUND = {pid: round(pid - 176) for pid in range(229, 236)}  # 229->53 ... 235->59
# Cross-check: period 229 = round 53, 230 = 54, ..., 235 = 59.
ANCHOR_ROUND = 52
ANCHOR_CLOSE = dt.datetime(2026, 11, 7, 18, 45, 0)

PUBLISHED = {
    53: {"sum": 9281577, "r16": "80308", "result": 9201269, "top": "269", "bot": "01"},
    54: {"sum": 7724164, "r16": "62839", "result": 7661325, "top": "325", "bot": "61"},
    55: {"sum": 7422657, "r16": "58470", "result": 7364187, "top": "187", "bot": "64"},
    56: {"top": "487", "bot": "32"},
    57: {"top": "849", "bot": "90"},
    58: {"top": "728", "bot": "49"},
    59: {"top": "416", "bot": "46"},
}


def parse_ts(s):
    # '07/11/2569 19:31:59' -> datetime(2026,11,7,19,31,59)
    d, t = s.split()
    day, month, year = map(int, d.split("/"))
    year -= 543
    hh, mm, ss = map(int, t.split(":"))
    return dt.datetime(year, month, day, hh, mm, ss)


def close_for_round(r):
    return ANCHOR_CLOSE + dt.timedelta(minutes=15 * (r - ANCHOR_ROUND))


def bucket(ts, close):
    shoot_open = close - dt.timedelta(minutes=2)
    shoot_close = close + dt.timedelta(minutes=2)
    if ts < shoot_open:
        return "before_shoot_open"
    if ts < close:
        return "pre_close_shoot_window"
    if ts <= shoot_close:
        return "post_close_shoot_window"
    return "after_shoot_close"


def main():
    events = []
    for fn in sorted(os.listdir(RAW)):
        if not fn.endswith(".json"):
            continue
        raw = json.load(open(os.path.join(RAW, fn)))
        # CLI returns a JSON string; handle both.
        if isinstance(raw, str):
            raw = json.loads(raw)
        pid = raw["id"]
        rnd = PERIOD_TO_ROUND[pid]
        close = close_for_round(rnd)
        for row in raw["rows"]:
            ts = parse_ts(row["ts"])
            events.append({
                "round": rnd,
                "period_id": pid,
                "seq": row["seq"],
                "number": row["num"],
                "ts": ts,
                "ts_local": row["ts"],
                "ts_iso": ts.strftime("%Y-%m-%dT%H:%M:%S+07:00"),
                "minutes_from_close": (ts - close).total_seconds() / 60.0,
                "bucket": bucket(ts, close),
            })

    events.sort(key=lambda e: (e["round"], e["seq"]))

    os.makedirs(EVID, exist_ok=True)
    with open(os.path.join(EVID, "submission_events.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["round", "period_id", "seq", "number", "ts_iso", "minutes_from_close", "bucket"])
        for e in events:
            w.writerow([e["round"], e["period_id"], e["seq"], e["number"], e["ts_iso"],
                        f"{e['minutes_from_close']:.3f}", e["bucket"]])

    # Per-round summary
    summaries = []
    per_second = []
    for rnd in sorted(set(e["round"] for e in events)):
        rr = [e for e in events if e["round"] == rnd]
        pid = rr[0]["period_id"]
        close = close_for_round(rnd)
        nums = [e["number"] for e in rr]        # seq order = display order
        total = sum(int(n) for n in nums)
        r16 = nums[15]
        raw_result = total - int(r16)
        last5 = f"{raw_result:05d}"[-5:]
        ts_counter = Counter(e["ts"] for e in rr)
        max_ts, max_n = ts_counter.most_common(1)[0]
        ties = [t for t, c in ts_counter.items() if c > 1]
        tie_rows = sum(c for t, c in ts_counter.items() if c > 1)
        collision_pairs = sum(c * (c - 1) // 2 for c in ts_counter.values())
        before = sum(1 for e in rr if e["ts"] < close)
        after = len(rr) - before
        s = {
            "round": rnd, "period_id": pid, "n": len(rr),
            "close_local": close.strftime("%Y-%m-%d %H:%M:%S"),
            "first_ts": min(e["ts"] for e in rr).strftime("%Y-%m-%d %H:%M:%S"),
            "last_ts": max(e["ts"] for e in rr).strftime("%Y-%m-%d %H:%M:%S"),
            "before_close": before, "after_close": after,
            "pct_before_close": round(100.0 * before / len(rr), 2),
            "pct_after_close": round(100.0 * after / len(rr), 2),
            "before_shoot_open": sum(1 for e in rr if e["bucket"] == "before_shoot_open"),
            "pre_close_shoot_window": sum(1 for e in rr if e["bucket"] == "pre_close_shoot_window"),
            "post_close_shoot_window": sum(1 for e in rr if e["bucket"] == "post_close_shoot_window"),
            "after_shoot_close": sum(1 for e in rr if e["bucket"] == "after_shoot_close"),
            "distinct_seconds": len(ts_counter),
            "max_per_second": max_n,
            "max_second": max_ts.strftime("%Y-%m-%d %H:%M:%S"),
            "tied_timestamps": len(ties), "rows_in_ties": tie_rows,
            "collision_pairs": collision_pairs,
            "sum": total, "row16": r16, "raw_result": raw_result,
            "top3": last5[-3:], "bottom2": last5[:2],
        }
        pub = PUBLISHED.get(rnd, {})
        for k in ("sum", "r16", "result", "top", "bot"):
            if k in pub:
                got = s["sum"] if k == "sum" else s["raw_result"] if k == "result" else s["row16"] if k == "r16" else s["top3"] if k == "top" else s["bottom2"]
                s[f"match_{k}"] = (str(got) == str(pub[k]))
        summaries.append(s)
        for t, c in sorted(ts_counter.items()):
            per_second.append({"round": rnd, "period_id": pid, "ts": t.strftime("%Y-%m-%d %H:%M:%S"), "count": c})

    with open(os.path.join(EVID, "round_summary.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summaries[0].keys()))
        w.writeheader(); w.writerows(summaries)
    with open(os.path.join(ROOT, "submission_timeline.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summaries[0].keys()))
        w.writeheader(); w.writerows(summaries)
    with open(os.path.join(EVID, "per_second.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["round", "period_id", "ts", "count"])
        w.writeheader(); w.writerows(per_second)

    # Collisions: timestamps with >1 row
    with open(os.path.join(ROOT, "timestamp_collisions.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["round", "period_id", "timestamp", "count", "collision_pairs",
                    "first_seq", "last_seq", "numbers"])
        for rnd in sorted(set(e["round"] for e in events)):
            rr = [e for e in events if e["round"] == rnd]
            for t, c in sorted(Counter(e["ts"] for e in rr).items()):
                if c > 1:
                    group = sorted([e for e in rr if e["ts"] == t], key=lambda x: x["seq"])
                    w.writerow([rnd, rr[0]["period_id"], t.strftime("%Y-%m-%d %H:%M:%S"), c,
                                c * (c - 1) // 2, group[0]["seq"], group[-1]["seq"],
                                "|".join(e["number"] for e in group)])

    # Console audit
    print("round period  n  before after  max/s  distinct  sum       row16   result    top/bot  match")
    for s in summaries:
        print(f"{s['round']:5d} {s['period_id']:6d} {s['n']:3d} {s['before_close']:6d} {s['after_close']:5d} "
              f"{s['max_per_second']:5d} {s['distinct_seconds']:8d} {s['sum']:9d} {s['row16']:>7s} "
              f"{s['raw_result']:9d} {s['top3']}/{s['bottom2']:<3s} "
              f"{','.join(k for k in s if k.startswith('match_') and not s[k]) or 'all'}")
    print("\nClaim check round 55 (period 231):")
    s = next(x for x in summaries if x["round"] == 55)
    print(f"  n={s['n']} before_close={s['before_close']} after_close={s['after_close']} "
          f"max_per_second={s['max_per_second']} at {s['max_second']} distinct={s['distinct_seconds']}")
    print(f"  sum={s['sum']} row16={s['row16']} result={s['raw_result']} top/bot={s['top3']}/{s['bottom2']}")


if __name__ == "__main__":
    main()
