# Historical Availability — 88-Round Yeekee

Phase C, 2026-11-07/08 (Asia/Bangkok). Authorized member account; read-only navigation only. No historical IDs were guessed and no undocumented endpoint was probed.

## 1. Questions and short answers

| Question | Answer | Class |
|---|---|---|
| Was the 53-result dataset only a time-of-capture snapshot? | **Yes.** The same current-day grid showed 51 results at 18:58, 53 at 19:23, 59 at 20:55, 62 at 21:30, and 71 at 23:49. | OBSERVED |
| Do all 88 results become visible after a complete lottery day? | **Not directly verified.** The grid reached 71/88 at 23:49 and increments at round boundaries. All 88 is expected by 03:45, but no completed-day archive was reachable. | INFERRED / UNKNOWN |
| Does the 88-round product have a historical date filter or archive? | **No.** The main page ignores `?date=`. The results page date filter changes the 264-round product, but the 88-round block always shows only the latest round. | OBSERVED |
| Oldest/newest dates verified through ordinary UI? | **88-round:** only 2026-11-07 (current day). **264-round product (comparison):** 2026-01-01 through 2026-11-07. | OBSERVED |
| Do result history and submission-list history differ? | For the 88-round product, both are current-day only; older period detail pages return 404. | OBSERVED / INFERRED |
| Are 404s attributable to a known route/access limitation? | The route exists (current period IDs work). The cause of old-period 404 is **UNKNOWN** (pruning, retention, or access scope). | OBSERVED 404 / UNKNOWN cause |
| Can the actual database retention period be determined? | **No.** The UI exposes no retention metadata; the datepicker has no `startDate`. | UNKNOWN |

## 2. The 53-result dataset was a snapshot

The 53-result dataset was collected at 19:23 from `/member/lottery/yeekee`. Later observations of the same endpoint:

| Local time | Published results | Newest result |
|---|---:|---|
| 18:58 | 51 | round 51 |
| 19:23 | 53 | round 53 |
| 20:55 | 59 | round 59 |
| 21:30 | 62 | round 62 |
| 23:49 | 71 | round 71 |

The grid is a **current-day, growing list**, not a fixed archive. The 53-result file is therefore a snapshot, exactly as suspected.

Evidence: PC-HIST-01 (main page counts), Phase A/B raw observations, screenshot `charts/list_71_results_2349.png`.

### Midnight boundary (00:00:37 on 2026-11-08)

At 00:00:37 local, the page still showed **72 results** (rounds 1–72), with round 73 (closed at 00:00) pending and rounds 74–75 future. There was **no midnight reset**; the lottery day continues past 00:00, consistent with the 06:00 → 03:45 day definition. The grid added round 72 at the 00:00 boundary, consistent with the 15-minute grid refresh.

Classification: OBSERVED.

## 3. Main 88-round page

- Route: `/member/lottery/yeekee`.
- It has **no date input** and no history/archive link.
- Adding `?date=01/11/2569` or `?date=06/11/2569` returns the **same 71 current-day results**; the parameter is ignored.
- The page shows completed rounds as `.card-result` and future/current rounds as `.card-items`.
- It never showed a previous day's 88-round results in any tested state.

Classification: OBSERVED.

## 4. Results page date filter

Route: `/member/lottery/result?date=DD/MM/BBBB` (Buddhist year).

The page contains two relevant products:

1. **จับยี่กี (88 rounds)** — the target.
2. **จับยี่กีทันใจ (264 rounds)** — a different product shown for comparison only.

Tested dates: `07/11/2569`, `06/11/2569`, `01/11/2569`, `01/10/2569`, `01/01/2569`.

Result:

- The **264-round product** changed with the date and listed 355 result lines, including rounds 1–214, for every tested date.
- The **88-round product** always showed only `จับยี่กี รอบที่ 72` (the latest round at capture), regardless of the selected date.
- There is no per-date archive for the 88-round product on this page.

This is a critical distinction: a date filter exists, but it does **not** provide 88-round history. The 264-round history must not be used as a proxy for the 88-round product.

Evidence: PC-HIST-02 (date-filter tests), `HISTORICAL_ACCESS_MATRIX.csv` HA-03/HA-04.

## 5. Datepicker constraints

The results page initializes:

```js
$('.input-group.date').datepicker({
  format: "dd/mm/yyyy",
  thaiyear: true,
  language: "th",
  todayHighlight: true,
  endDate: '+1d',
  autoclose: true,
  todayBtn: "linked"
});
```

- There is **no `startDate`**.
- `endDate: '+1d'` allows today and tomorrow.
- The UI therefore accepts any past date but reveals nothing about server retention.

Classification: OBSERVED (configuration) / UNKNOWN (retention).

## 6. Oldest and newest dates

| Product | Oldest verified via UI | Newest verified via UI | Meaning |
|---|---|---|---|
| 88-round Yeekee | 2026-11-07 | 2026-11-07 | Current day only; no archive |
| 264-round Yeekee (comparison) | 2026-01-01 | 2026-11-07 | Per-date result history exists for this different product |

**Do not confuse the oldest observed date with the database retention period.** The 01/01/2569 observation belongs to the 264-round product. For the 88-round product, the oldest verified date is the current day; the actual retention is UNKNOWN.

## 7. Old-period detail pages

Phase C re-tested the status codes directly: period IDs 83 and 171 returned **404**, while current IDs 236, 244, and 249 returned **200** with ~100 KB HTML. This confirms the route exists and the 404 is specific to those old IDs.

- Current-day period IDs (e.g. 236–244, 249) load normally and expose the submission list.
- Older period IDs from Phase A (83, 84, 170, 171) returned **HTTP 404** in the authorized session.
- The route itself is valid; the 404 is specific to those period IDs.
- Possible explanations: pruning/retention, a route constraint, or an access scope. The available evidence cannot distinguish them.

Classification: OBSERVED 404; cause UNKNOWN.

## 8. Result history vs submission-list history

For the 88-round product:

- **Result history:** current-day grid only; the results page date filter does not provide per-date 88-round results.
- **Submission-list history:** current-day round detail pages only; older period IDs return 404.
- Therefore, for this product, result and submission history have the **same current-day limitation** in the observed UI.

Classification: OBSERVED / INFERRED.

## 9. Do all 88 results become visible after a complete day?

The current-day grid is monotonic:

- 51 → 53 → 59 → 62 → 71 as rounds complete.
- At 23:49 it had 71/88; rounds 72–88 were still pending or future.
- It is expected to reach 88 by 03:45, then reset for the next day at 05:00.
- **This was not directly observed.** There is no completed-day archive to inspect after the reset.

Verdict: the mechanism strongly suggests all 88 are visible during the 03:45–05:00 window, but this remains **INFERRED/UNKNOWN**, not OBSERVED.

## 10. ACCESS BLOCKED / not verifiable

- No completed-day snapshot (would require waiting until 03:50 or server-side data).
- No historical 88-round submission lists; old period IDs 404.
- No database retention metadata; datepicker has no start date.
- No server-side archive route; none was guessed or probed.
- The 264-round product’s history is real but out of scope and not a substitute.

## 11. Evidence

- `HISTORICAL_ACCESS_MATRIX.csv` — feature-by-feature matrix.
- `charts/list_71_results_2349.png` — current-day grid at 23:49.
- `charts/rea_round_249.png` — current round detail (round 73) captured for REA cross-check.
- PC-HIST-01/02/03/04 in `REA_EVIDENCE_VERIFICATION.md` and `PHASE_C_FINAL_REPORT.md`.
