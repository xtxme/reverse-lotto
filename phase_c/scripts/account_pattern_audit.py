#!/usr/bin/env python3
"""Phase C — masked-account pattern audit (hash-only, privacy-preserving).

Reads phase_c/evidence/combined_events.csv and recomputes:
  - per-round distinct masked hashes, rows/user, users with 2+ rows
  - duplicate groups by number and ownership (same/mixed/different)
  - same-second vs different-second duplicate structure
  - +103s/+119s burst composition and user overlap
  - cross-round recurrence of masked hashes
  - same user + same number across rounds

Outputs phase_c/evidence/c_account_patterns.json.
No raw masked usernames are read or written.
"""

import csv
import json
import os
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
EVID = os.path.join(ROOT, "evidence")


def main():
    rows = list(csv.DictReader(open(os.path.join(EVID, "combined_events.csv"))))
    for r in rows:
        r["round"] = int(r["round"])
        r["seq"] = int(r["seq"])
        r["offset_s"] = int(r["offset_s"])
    rounds = sorted(set(r["round"] for r in rows))

    per_round = []
    dup = []
    burst = []
    total_dup_groups = same = mixed = diff = same_second = 0
    pairs_total = pairs_same_second = 0

    for rnd in rounds:
        rr = [r for r in rows if r["round"] == rnd]
        uc = Counter(r["user_hash"] for r in rr if r["user_hash"])
        per_round.append({
            "round": rnd,
            "n": len(rr),
            "distinct_masked_hashes": len(uc),
            "users_with_2plus_rows": sum(1 for v in uc.values() if v >= 2),
            "max_rows_per_masked_hash": max(uc.values()) if uc else 0,
            "rows_without_hash": sum(1 for r in rr if not r["user_hash"]),
        })

        by_num = defaultdict(list)
        for r in rr:
            by_num[r["number"]].append(r)
        groups = [(k, v) for k, v in by_num.items() if len(v) > 1]
        rsame = rmixed = rdiff = rsame_second = 0
        for _, g in groups:
            total_dup_groups += 1
            us = set(x["user_hash"] for x in g)
            if len(us) == 1:
                rsame += 1; same += 1
            elif len(us) == len(g):
                rdiff += 1; diff += 1
            else:
                rmixed += 1; mixed += 1
            if len(set(x["ts_iso"] for x in g)) == 1:
                rsame_second += 1; same_second += 1
            for i in range(len(g)):
                for j in range(i + 1, len(g)):
                    pairs_total += 1
                    if g[i]["ts_iso"] == g[j]["ts_iso"]:
                        pairs_same_second += 1
        dup.append({
            "round": rnd, "duplicate_groups": len(groups),
            "same_user": rsame, "mixed": rmixed, "all_different": rdiff,
            "all_same_second": rsame_second,
            "duplicate_entries": len(rr) - len(by_num),
            "colliding_pairs": sum(len(g) * (len(g) - 1) // 2 for _, g in groups),
        })

        g103 = [r for r in rr if r["offset_s"] == 103]
        g119 = [r for r in rr if r["offset_s"] == 119]
        u103, u119 = set(r["user_hash"] for r in g103), set(r["user_hash"] for r in g119)
        burst.append({
            "round": rnd,
            "b103_rows": len(g103), "b103_users": len(u103),
            "b103_unique_numbers": len(set(r["number"] for r in g103)),
            "b119_rows": len(g119), "b119_users": len(u119),
            "b119_unique_numbers": len(set(r["number"] for r in g119)),
            "user_intersection": len(u103 & u119),
            "user_union": len(u103 | u119),
            "user_jaccard": round(len(u103 & u119) / len(u103 | u119), 3) if (u103 | u119) else None,
            "number_intersection": len(set(r["number"] for r in g103) & set(r["number"] for r in g119)),
        })

    by_user = defaultdict(set)
    by_user_number = defaultdict(set)
    for r in rows:
        if r["user_hash"]:
            by_user[r["user_hash"]].add(r["round"])
            by_user_number[(r["user_hash"], r["number"])].add(r["round"])
    recurrence = Counter(len(v) for v in by_user.values())
    multi_round = [(k, v) for k, v in by_user_number.items() if len(v) >= 2]

    out = {
        "rounds": len(rounds),
        "events": len(rows),
        "distinct_masked_hashes": len(by_user),
        "hashes_in_2plus_rounds": sum(1 for v in by_user.values() if len(v) >= 2),
        "recurrence_histogram": dict(sorted(recurrence.items())),
        "same_user_number_in_2plus_rounds": len(multi_round),
        "duplicate_groups": total_dup_groups,
        "same_user_groups": same,
        "mixed_groups": mixed,
        "all_different_groups": diff,
        "all_same_second_groups": same_second,
        "colliding_pairs": pairs_total,
        "same_second_pairs": pairs_same_second,
        "per_round": per_round,
        "duplicates": dup,
        "bursts": burst,
        "note": "user_hash is a truncated SHA-256 of the site-masked display name with the fixed prefix 'phase_c:'. It is a display identifier, not a verified natural person. Two accounts that render the same mask are indistinguishable.",
    }
    with open(os.path.join(EVID, "c_account_patterns.json"), "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(json.dumps({k: out[k] for k in out if k not in ("per_round", "duplicates", "bursts")}, indent=2))
    print("per-round rows:", len(per_round), "duplicate rows:", len(dup), "burst rows:", len(burst))


if __name__ == "__main__":
    main()
