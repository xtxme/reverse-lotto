#!/usr/bin/env python3
"""
Independent parser for the exported LINE chat.

Design principles
-----------------
1. Read the raw export only; never modify it.
2. Every parsed record keeps its source line number.
3. Round numbers are interpreted with the published 88-round schedule
   (round 1 = 06:00, round 72 = 23:45, round 73 = 00:00 next day,
    round 88 = 03:45 next day).  The trading day is the date of round 1.
4. Deduplicate by (trading_day, round).  Every conflicting value is retained
   in a separate conflict report rather than silently overwritten.
5. Repeated result messages and repeated table rows are counted, not treated
   as independent evidence.
"""
from __future__ import annotations

import csv
import os
import json
import re
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = Path(os.environ["LINE_EXPORT_PATH"])
OUT = ROOT / "outputs"
OUT.mkdir(parents=True, exist_ok=True)

DATE_RE = re.compile(r"^(20\d{2})\.(\d{2})\.(\d{2})\b")
MSG_RE = re.compile(r"^(\d{2}):(\d{2}) (.+)$")
ROUND_RE = re.compile(r"จับยี่กี\s*รอบที่\s*(\d+)")
PAIR_RE = re.compile(r"^\s*(\d{3})\s*-\s*(\d{2})\s*$")
TABLE_RE = re.compile(r"^\s*(\d{1,2}):\s*(\d{2}):(\d{2})\s*➡️\s*(\d{3})\s*-\s*(\d{2})")

# Display names observed in this export.  Longest first so that
# "FORECASTER_10" is not truncated to "FORECASTER_11".
SENDERS = sorted(json.loads(Path(os.environ["LINE_SENDERS_FILE"]).read_text(encoding="utf-8")), key=len, reverse=True)


def schedule_close(trading_day: date, round_no: int) -> datetime:
    """Scheduled betting-close time for a round on a trading day."""
    if not 1 <= round_no <= 88:
        raise ValueError(round_no)
    base = datetime.combine(trading_day, datetime.min.time())
    if round_no <= 72:
        return base + timedelta(hours=6, minutes=15 * (round_no - 1))
    return base + timedelta(days=1, minutes=15 * (round_no - 73))


def split_header(text: str):
    """Return (sender, message) or (None, text) for a non-message line."""
    for name in SENDERS:
        if text.startswith(name):
            return name, text[len(name) :].lstrip(" ")
    return None, text


def main() -> None:
    raw_lines = RAW.read_text(encoding="utf-8-sig").splitlines()

    current_date: date | None = None
    msg = None  # dict(ts, author, body, line)
    messages = []

    def flush():
        nonlocal msg
        if msg is not None:
            messages.append(msg)
        msg = None

    for lineno, text in enumerate(raw_lines, start=1):
        dm = DATE_RE.match(text)
        if dm:
            flush()
            current_date = date(*map(int, dm.groups()))
            continue
        mm = MSG_RE.match(text)
        if mm and current_date is not None and int(mm.group(1)) < 24 and int(mm.group(2)) < 60:
            author, body = split_header(mm.group(3))
            if author is not None:
                flush()
                ts = datetime.combine(current_date, datetime.min.time()) + timedelta(
                    hours=int(mm.group(1)), minutes=int(mm.group(2))
                )
                msg = {"ts": ts, "author": author, "body": [body], "line": lineno}
                continue
        if msg is not None:
            msg["body"].append(text)
    flush()

    # ---- extract headline result blocks -------------------------------------
    result_posts = []
    for m in messages:
        for idx, body_line in enumerate(m["body"]):
            rm = ROUND_RE.search(body_line)
            if not rm:
                continue
            rnd = int(rm.group(1))
            if not 1 <= rnd <= 88:
                continue
            pair = None
            for nxt in m["body"][idx + 1 : idx + 4]:
                pm = PAIR_RE.match(nxt)
                if pm:
                    pair = (pm.group(1), pm.group(2))
                    break
            if pair is None:
                continue
            result_posts.append(
                {
                    "round": rnd,
                    "top3": pair[0],
                    "bottom2": pair[1],
                    "posted": m["ts"],
                    "author": m["author"],
                    "line": m["line"],
                }
            )

    # ---- choose the trading day that makes the posting delay plausible -----
    for p in result_posts:
        candidates = []
        for delta in (0, -1, 1, -2):
            td = p["posted"].date() + timedelta(days=delta)
            close = schedule_close(td, p["round"])
            delay = (p["posted"] - close).total_seconds() / 60.0
            candidates.append((abs(delay - 2.0), delay, td, close))
        candidates.sort()
        _, delay, td, close = candidates[0]
        p["trading_day"] = td
        p["scheduled_close"] = close
        p["delay_min"] = delay

    # ---- deduplicate by (trading_day, round) --------------------------------
    grouped = defaultdict(list)
    for p in result_posts:
        grouped[(p["trading_day"], p["round"])].append(p)

    results = []
    conflicts = []
    for (td, rnd), posts in sorted(grouped.items()):
        values = Counter((p["top3"], p["bottom2"]) for p in posts)
        top, bottom = values.most_common(1)[0][0]
        first = min(posts, key=lambda p: (p["posted"], p["line"]))
        results.append(
            {
                "trading_day": td.isoformat(),
                "round": rnd,
                "scheduled_close": schedule_close(td, rnd).isoformat(sep=" "),
                "top3": top,
                "bottom2": bottom,
                "first_result_posted": first["posted"].isoformat(sep=" "),
                "delay_min": round(first["delay_min"], 2),
                "n_result_posts": len(posts),
                "n_distinct_values": len(values),
                "source_line": min(p["line"] for p in posts),
            }
        )
        if len(values) > 1:
            conflicts.append(
                {
                    "trading_day": td.isoformat(),
                    "round": rnd,
                    "n_posts": len(posts),
                    "values": "; ".join(f"{a}-{b} x{n}" for (a, b), n in values.items()),
                    "source_lines": ",".join(str(p["line"]) for p in posts),
                }
            )

    # ---- table-row evidence -------------------------------------------------
    # Attach every inline row to the trading day of the headline round in the
    # same message.  This is only used as corroboration, never as a new draw.
    table_rows = []
    for m in messages:
        head = None
        for body_line in m["body"]:
            rm = ROUND_RE.search(body_line)
            if rm:
                head = int(rm.group(1))
                break
        if head is None:
            continue
        # recover the trading day from the headline post using the same logic
        best = None
        for delta in (0, -1, 1, -2):
            td = m["ts"].date() + timedelta(days=delta)
            delay = (m["ts"] - schedule_close(td, head)).total_seconds() / 60.0
            score = abs(delay - 2.0)
            if best is None or score < best[0]:
                best = (score, td)
        td = best[1]
        for body_line in m["body"]:
            tm = TABLE_RE.match(body_line)
            if not tm:
                continue
            table_rows.append(
                {
                    "trading_day": td.isoformat(),
                    "round": int(tm.group(1)),
                    "clock": f"{tm.group(2)}:{tm.group(3)}",
                    "top3": tm.group(4),
                    "bottom2": tm.group(5),
                    "source_line": m["line"],
                }
            )

    table_group = defaultdict(Counter)
    for r in table_rows:
        table_group[(r["trading_day"], r["round"])][(r["top3"], r["bottom2"])] += 1

    table_conflicts = []
    for (td, rnd), counts in sorted(table_group.items()):
        if len(counts) > 1:
            table_conflicts.append(
                {
                    "trading_day": td,
                    "round": rnd,
                    "values": "; ".join(f"{a}-{b} x{n}" for (a, b), n in counts.items()),
                }
            )

    # agreement between headline values and table rows
    headline = {(r["trading_day"], r["round"]): (r["top3"], r["bottom2"]) for r in results}
    agree = disagree = 0
    mismatch_examples = []
    for key, counts in table_group.items():
        if key not in headline:
            continue
        val = counts.most_common(1)[0][0]
        if val == headline[key]:
            agree += 1
        else:
            disagree += 1
            if len(mismatch_examples) < 20:
                mismatch_examples.append(
                    {"key": key, "headline": headline[key], "table": val, "table_counts": dict(counts)}
                )

    # ---- round coverage -----------------------------------------------------
    by_day = defaultdict(list)
    for r in results:
        by_day[r["trading_day"]].append(r["round"])
    coverage = []
    for td in sorted(by_day):
        rounds = sorted(by_day[td])
        missing = [n for n in range(1, 89) if n not in set(rounds)]
        coverage.append(
            {
                "trading_day": td,
                "n_rounds": len(rounds),
                "missing_rounds": " ".join(map(str, missing)),
                "missing_count": len(missing),
                "first_round": rounds[0],
                "last_round": rounds[-1],
            }
        )

    # ---- write outputs ------------------------------------------------------
    with open(OUT / "results_dedup_independent.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        w.writeheader()
        w.writerows(results)

    with open(OUT / "result_conflicts.csv", "w", encoding="utf-8-sig", newline="") as f:
        fields = ["trading_day", "round", "n_posts", "values", "source_lines"]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(conflicts)

    with open(OUT / "table_row_conflicts.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["trading_day", "round", "values"])
        w.writeheader()
        w.writerows(table_conflicts)

    with open(OUT / "missing_rounds_by_day.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(coverage[0].keys()))
        w.writeheader()
        w.writerows(coverage)

    with open(OUT / "parse_audit.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "raw_lines": len(raw_lines),
                "date_headers": sum(1 for s in raw_lines if DATE_RE.match(s)),
                "messages": len(messages),
                "result_blocks": len(result_posts),
                "unique_round_records": len(results),
                "result_value_conflicts": len(conflicts),
                "inline_table_rows": len(table_rows),
                "inline_table_value_conflicts": len(table_conflicts),
                "headline_vs_table_agree": agree,
                "headline_vs_table_disagree": disagree,
                "mismatch_examples": mismatch_examples,
                "delay_min_summary": {
                    "min": min(p["delay_min"] for p in result_posts),
                    "max": max(p["delay_min"] for p in result_posts),
                    "median": sorted(p["delay_min"] for p in result_posts)[len(result_posts) // 2],
                    "n_over_60min": sum(1 for p in result_posts if p["delay_min"] > 60),
                    "n_negative": sum(1 for p in result_posts if p["delay_min"] < -1),
                },
                "authors_of_result_posts": dict(Counter(p["author"] for p in result_posts)),
                "trading_days": len(by_day),
                "total_missing_rounds": sum(c["missing_count"] for c in coverage),
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(json.dumps(json.load(open(OUT / "parse_audit.json")), ensure_ascii=False, indent=2))
    print("\nCoverage by day (first 10):")
    for c in coverage[:10]:
        print(c)


if __name__ == "__main__":
    main()
