#!/usr/bin/env python3
"""
Extract "เลขนิ่ง" hourly digit tables, attribute them, and resolve
first-seen vs last-seen-before-target versions.

The table format is:
    06.00=5=172-52//06.00
    07.00=3=926-83//07.00
    ...
    24.00=5
    01.00=1
    02.00=8
    03.00=2

Only lines that carry a single digit after "HH.00=" are treated as forecasts.
Anything after the digit is an annotation (result / hit marker / next time)
and is never used as a prediction.
"""
from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = Path(os.environ["LINE_EXPORT_PATH"])
OUT = ROOT / "outputs"

DATE_RE = re.compile(r"^(20\d{2})\.(\d{2})\.(\d{2})\b")
MSG_RE = re.compile(r"^(\d{2}):(\d{2}) (.+)$")
FORECAST_RE = re.compile(r"^\s*(\d{2})\.00\s*=\s*([0-9])(.*)$")
ROUND_RE = re.compile(r"จับยี่กี\s*รอบที่\s*(\d+)")

SENDERS = sorted(json.loads(Path(os.environ["LINE_SENDERS_FILE"]).read_text(encoding="utf-8")), key=len, reverse=True)


def split_header(text: str):
    for name in SENDERS:
        if text.startswith(name):
            return name, text[len(name) :].lstrip(" ")
    return None, text


def load_messages():
    lines = RAW.read_text(encoding="utf-8-sig").splitlines()
    current_date = None
    msg = None
    out = []

    def flush():
        nonlocal msg
        if msg:
            out.append(msg)
        msg = None

    for lineno, text in enumerate(lines, start=1):
        dm = DATE_RE.match(text)
        if dm:
            flush()
            current_date = date(*map(int, dm.groups()))
            continue
        mm = MSG_RE.match(text)
        if mm and current_date and int(mm.group(1)) < 24 and int(mm.group(2)) < 60:
            author, body = split_header(mm.group(3))
            if author:
                flush()
                msg = {
                    "ts": datetime.combine(current_date, datetime.min.time())
                    + timedelta(hours=int(mm.group(1)), minutes=int(mm.group(2))),
                    "author": author,
                    "body": [body],
                    "line": lineno,
                }
                continue
        if msg:
            msg["body"].append(text)
    flush()
    return lines, out


def target_datetime(post_ts: datetime, hour_label: int) -> datetime:
    """
    The table is anchored to the trading day whose round 1 is at 06:00.
    Labels 06..23 are that same calendar date; 24 is the next midnight;
    01..03 are the next calendar date.
    A post is always made during the trading day (05:00 -> 03:59 next day).
    """
    d = post_ts.date()
    if post_ts.hour < 5:
        trading_day = d - timedelta(days=1)
    else:
        trading_day = d
    if hour_label == 24:
        return datetime.combine(trading_day + timedelta(days=1), datetime.min.time())
    if 1 <= hour_label <= 3:
        return datetime.combine(trading_day + timedelta(days=1), datetime.min.time()) + timedelta(
            hours=hour_label
        )
    if 6 <= hour_label <= 23:
        return datetime.combine(trading_day, datetime.min.time()) + timedelta(hours=hour_label)
    return None


def main():
    lines, messages = load_messages()

    posts = []
    for m in messages:
        if "เลขนิ่ง" not in m["body"][0]:
            continue
        entries = []
        for body_line in m["body"][1:]:
            if ROUND_RE.search(body_line):
                break
            fm = FORECAST_RE.match(body_line)
            if not fm:
                continue
            hour_label = int(fm.group(1))
            digit = int(fm.group(2))
            target = target_datetime(m["ts"], hour_label)
            if target is None:
                continue
            entries.append(
                {
                    "hour_label": hour_label,
                    "digit": digit,
                    "target": target,
                    "annotation": fm.group(3).strip(),
                    "raw": body_line.strip(),
                }
            )
        if entries:
            posts.append({"posted": m["ts"], "author": m["author"], "line": m["line"], "entries": entries})

    # ---- resolve per (author, target hour) ---------------------------------
    by_author_hour = defaultdict(list)
    for p in posts:
        for e in p["entries"]:
            by_author_hour[(p["author"], e["target"])].append(
                {
                    "posted": p["posted"],
                    "digit": e["digit"],
                    "line": p["line"],
                    "annotation": e["annotation"],
                    "raw": e["raw"],
                }
            )

    rows = []
    for (author, target), entries in sorted(by_author_hour.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        entries.sort(key=lambda x: (x["posted"], x["line"]))
        pre = [x for x in entries if x["posted"] < target]
        post = [x for x in entries if x["posted"] >= target]
        if not pre:
            continue
        first = pre[0]
        last = pre[-1]
        post_digits = {x["digit"] for x in post}
        rows.append(
            {
                "author": author,
                "target_hour": target.isoformat(sep=" "),
                "trading_day": (target.date() if target.hour >= 6 else target.date() - timedelta(days=1)).isoformat(),
                "first_digit": first["digit"],
                "first_posted": first["posted"].isoformat(sep=" "),
                "first_source_line": first["line"],
                "lead_minutes": round((target - first["posted"]).total_seconds() / 60),
                "last_digit": last["digit"],
                "last_posted": last["posted"].isoformat(sep=" "),
                "last_source_line": last["line"],
                "n_pre_posts": len(pre),
                "n_distinct_pre_digits": len({x["digit"] for x in pre}),
                "changed_before_target": int(first["digit"] != last["digit"]),
                "post_result_digits": "".join(map(str, sorted(post_digits))),
                "post_result_has_different_digit": int(bool(post_digits - {last["digit"]})),
            }
        )

    # ---- table-version clustering (are providers copying one source?) -----
    # group messages by the exact vector of future digits + trading day
    vec = defaultdict(list)
    for p in posts:
        trading_day = p["posted"].date() if p["posted"].hour >= 5 else p["posted"].date() - timedelta(days=1)
        digits = tuple(sorted((e["hour_label"], e["digit"]) for e in p["entries"]))
        vec[(trading_day, digits)].append((p["author"], p["posted"], p["line"]))

    with open(OUT / "hourly_forecast_posts.json", "w", encoding="utf-8") as f:
        json.dump(
            [
                {
                    "posted": p["posted"].isoformat(sep=" "),
                    "author": p["author"],
                    "line": p["line"],
                    "entries": [
                        {
                            "hour_label": e["hour_label"],
                            "digit": e["digit"],
                            "target": e["target"].isoformat(sep=" "),
                            "annotation": e["annotation"],
                        }
                        for e in p["entries"]
                    ],
                }
                for p in posts
            ],
            f,
            ensure_ascii=False,
            indent=1,
        )

    with open(OUT / "hourly_forecasts_resolved.csv", "w", encoding="utf-8-sig", newline="") as f:
        fields = list(rows[0].keys())
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    audit = {
        "forecast_posts": len(posts),
        "posts_by_author": dict(Counter(p["author"] for p in posts)),
        "entries": sum(len(p["entries"]) for p in posts),
        "resolved_author_hours": len(rows),
        "resolved_by_author": dict(Counter(r["author"] for r in rows)),
        "changed_before_target": sum(r["changed_before_target"] for r in rows),
        "post_result_has_different_digit": sum(r["post_result_has_different_digit"] for r in rows),
        "n_message_vectors": len(vec),
        "n_vectors_shared_by_multiple_authors": sum(1 for v in vec.values() if len({a for a, _, _ in v}) > 1),
        "largest_shared_vectors": sorted(
            [
                {
                    "n_messages": len(v),
                    "authors": sorted({a for a, _, _ in v}),
                    "posted_first": min(t for _, t, _ in v).isoformat(sep=" "),
                }
                for v in vec.values()
                if len(v) > 1
            ],
            key=lambda x: -x["n_messages"],
        )[:10],
        "examples_changed_before_target": [r for r in rows if r["changed_before_target"]][:10],
        "examples_post_result_changed": [r for r in rows if r["post_result_has_different_digit"]][:10],
    }
    (OUT / "hourly_forecast_parse_audit.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
