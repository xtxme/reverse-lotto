#!/usr/bin/env python3
"""
Full-archive cross-check: every trading day 2026-08-13 .. 2026-11-07,
LINE-derived values vs the authorized THLotto result page.

Produces:
  outputs/site_all_days_verification.csv
  outputs/site_complete_results.csv   (site values, used only for sensitivity)
  outputs/site_all_days_summary.json
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
DATA = ROOT / "data"


def parse_site(path: Path):
    raw = json.load(open(path, encoding="utf-8"))
    d = json.loads(raw) if isinstance(raw, str) else raw
    out = {}
    for title, values in d.items():
        m = re.match(r"^จับยี่กี รอบที่ (\d+)$", title)
        if not m:
            continue
        kv = {x["key"]: x.get("val") for x in values}
        top, bot = kv.get("สามตัวบน"), kv.get("สองตัวล่าง")
        if top and bot:
            out[int(m.group(1))] = (top, bot)
    return out


def main():
    rows = list(csv.DictReader(open(OUT / "results_dedup_independent.csv", encoding="utf-8-sig")))
    line = {(r["trading_day"], int(r["round"])): (r["top3"], r["bottom2"], r["source_line"]) for r in rows}
    report = []
    complete = []
    days = sorted(p.stem for p in (DATA / "site_days").glob("*.json"))
    for day in days:
        site = parse_site(DATA / "site_days" / f"{day}.json")
        for rnd in range(1, 89):
            lin = line.get((day, rnd))
            sit = site.get(rnd)
            if lin and sit:
                status = "match" if lin[:2] == sit else "value_mismatch"
            elif lin and not sit:
                status = "line_present_site_absent"
            elif not lin and sit:
                status = "line_missing_site_present"
            else:
                status = "absent_both"
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
            if sit:
                complete.append(
                    {
                        "trading_day": day,
                        "round": rnd,
                        "top3": sit[0],
                        "bottom2": sit[1],
                        "source": "thlotto_member_result_page",
                        "line_present": int(bool(lin)),
                        "line_agree": int(bool(lin) and lin[:2] == sit),
                    }
                )

    with open(OUT / "site_all_days_verification.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(report[0].keys()))
        w.writeheader()
        w.writerows(report)
    complete.sort(key=lambda r: (r["trading_day"], r["round"]))
    with open(OUT / "site_complete_results.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(complete[0].keys()))
        w.writeheader()
        w.writerows(complete)

    counts = {}
    for status in sorted({r["status"] for r in report}):
        counts[status] = sum(1 for r in report if r["status"] == status)
    mismatches = [r for r in report if r["status"] == "value_mismatch"]
    summary = {
        "site_days": len(days),
        "rounds_checked": len(report),
        "status_counts": counts,
        "n_value_mismatch": len(mismatches),
        "value_mismatch_examples": mismatches[:10],
        "line_rounds": len(line),
        "site_rounds": len(complete),
        "line_gaps_filled_by_site": counts.get("line_missing_site_present", 0),
        "line_agreement_rate_among_overlap": round(
            counts.get("match", 0) / max(1, counts.get("match", 0) + counts.get("value_mismatch", 0)), 6
        ),
        "note": "The site page for the current day may not yet contain future rounds; those are 'absent_both' or 'line_present_site_absent'.",
    }
    (OUT / "site_all_days_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
