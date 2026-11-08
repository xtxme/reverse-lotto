#!/usr/bin/env python3
"""
Compare the independent LINE-derived results with the authorized THLotto
result pages captured for selected full trading days.

The site date parameter is a trading day: rounds 1-72 occur on that calendar
date and rounds 73-88 occur after midnight on the next calendar date.
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
DATA = ROOT / "data"

SITES = {
    "2026-08-13": DATA / "site_13-08-2569.json",
    "2026-10-06": DATA / "site_06-10-2569.json",
    "2026-10-19": DATA / "site_19-10-2569.json",
    "2026-11-04": DATA / "site_2026-11-04.json",
    "2026-11-07": DATA / "site_07-11-2569.json",
}


def parse_site(path: Path):
    raw = json.load(open(path, encoding="utf-8"))
    d = json.loads(raw) if isinstance(raw, str) else raw
    out = {}
    for title, values in d.items():
        m = re.match(r"^จับยี่กี รอบที่ (\d+)$", title)
        if not m:
            continue
        kv = {x["key"]: x.get("val") for x in values}
        top = kv.get("สามตัวบน")
        bot = kv.get("สองตัวล่าง")
        if top and bot:
            out[int(m.group(1))] = (top, bot)
    return out


def main():
    rows = list(csv.DictReader(open(OUT / "results_dedup_independent.csv", encoding="utf-8-sig")))
    line = {(r["trading_day"], int(r["round"])): (r["top3"], r["bottom2"]) for r in rows}
    report = []
    for day, path in SITES.items():
        site = parse_site(path)
        for rnd in range(1, 89):
            lin = line.get((day, rnd))
            sit = site.get(rnd)
            status = "match"
            if lin is None and sit is None:
                status = "absent_both"
            elif lin is None:
                status = "line_missing_site_present"
            elif sit is None:
                status = "site_missing"
            elif lin != sit:
                status = "value_mismatch"
            report.append(
                {
                    "trading_day": day,
                    "round": rnd,
                    "line_top3": lin[0] if lin else "",
                    "line_bottom2": lin[1] if lin else "",
                    "site_top3": sit[0] if sit else "",
                    "site_bottom2": sit[1] if sit else "",
                    "status": status,
                }
            )
    with open(OUT / "site_verification.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(report[0].keys()))
        w.writeheader()
        w.writerows(report)

    summary = {}
    for day in SITES:
        sub = [r for r in report if r["trading_day"] == day]
        summary[day] = {
            "rounds_checked": len(sub),
            "match": sum(r["status"] == "match" for r in sub),
            "line_missing_site_present": sum(r["status"] == "line_missing_site_present" for r in sub),
            "value_mismatch": sum(r["status"] == "value_mismatch" for r in sub),
            "absent_both": sum(r["status"] == "absent_both" for r in sub),
            "site_missing": sum(r["status"] == "site_missing" for r in sub),
        }
    (OUT / "site_verification_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
