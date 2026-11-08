# Round Schedule — 88-Round Yeekee

Observation date: 2026-11-07, Asia/Bangkok. Primary page: `/member/lottery/yeekee`. Round detail pages: `/member/lottery/yeekee/{periodId}`.

## 1. Published schedule

From the site’s own “กติกา” modal (OBSERVED, screenshot `rules_modal_round55.png`):

- 88 rounds per day.
- One result every 15 minutes.
- First round closes at **06:00**; betting opens at **05:00**.
- Last round stops accepting bets at **03:45** the next calendar day.
- Advance betting on future rounds is allowed.

## 2. Directly observed schedule (7 Nov 2026)

The server-rendered grid showed rounds 52–88 with these close times (all OBSERVED):

| Rounds | Close time (local) | Date |
|---|---|---|
| 52 | 18:45:00 | 07/11/2569 |
| 53 | 19:00:00 | 07/11/2569 |
| 54 | 19:15:00 | 07/11/2569 |
| 55 | 19:30:00 | 07/11/2569 |
| 56 | 19:45:00 | 07/11/2569 |
| 57 | 20:00:00 | 07/11/2569 |
| … | … (every 15 min) | 07/11/2569 |
| 72 | 23:45:00 | 07/11/2569 |
| 73 | 00:00:00 | 08/11/2569 |
| 74 | 00:15:00 | 08/11/2569 |
| … | … (every 15 min) | 08/11/2569 |
| 88 | 03:45:00 | 08/11/2569 |

Rounds 1–51 are not shown as future cards, because they are already published. Subtracting 15 minutes per round from round 52 yields round 1 = **06:00:00**, exactly matching the published rule (INFERRED from arithmetic, corroborated by the rule text and by 53 published results).

The full machine-readable table is `evidence/sanitized_observations/observed_schedule.json` (rounds 52–88 flagged `observed: true`; rounds 1–51 flagged `derived: true`).

## 3. Trading-day definition

- A “day” starts when round 1 betting opens at **05:00** and ends when round 88 stops accepting bets at **03:45** the next calendar day.
- The 88 results therefore span **06:00 → 03:45** (21 h 45 min of result times), while the betting window spans **05:00 → 03:45** (22 h 45 min).
- The site’s displayed date (Buddhist Era, `2569` = 2026 CE) changes at midnight for rounds 73–88, while the round numbering continues (73…88), not resetting at midnight.

Classification: OBSERVED for the displayed dates and numbering; INFERRED for the “trading day” terminology.

## 4. Round numbering and identifiers

- Round numbers reset to 1 each day and run 1–88.
- Period/category IDs are **not** a constant offset from the round number:
  - Round 1 → period 172
  - Round 32 → period 203
  - Round 33 → period 209 (IDs 204–208 are absent)
  - Round 52 → period 228
  - Round 55 → period 231
  - Round 88 → period 264
- Each period also has an internal `current_period_id` (e.g. round 55 → `802206`) distinct from the URL category ID.

Classification: OBSERVED. Reason for skipped IDs is UNKNOWN (cancelled/void periods, imports, or another product sharing the sequence are all plausible).

## 5. Server-provided timing fields

For round 55 (period 231), the server embedded `betconfig` in the page HTML:

```json
{
  "id": 231,
  "title": "จับยี่กี รอบที่ 55",
  "open_date": "2026-11-06T22:00:00.000Z",
  "close_date": "2026-11-07T12:30:00.000Z",
  "default_open_time": "05:00",
  "default_close_time": "19:30",
  "is_open": 1,
  "result_state": "none",
  "closeDateYeekee": "2026-11-07T12:32:00.000Z",
  "closeDateThai": "07/11/2569 19:30:00"
}
```

`open_date` and `close_date` are UTC ISO strings; `12:30Z` = 19:30 Bangkok. `closeDateYeekee` is exactly `close_date + 2 minutes`, matching the client’s `expireTimeOfShootNumber = 120000` ms.

Classification: OBSERVED. The server, not the browser, determines these timestamps.

## 6. Current / future round display

- The grid shows the current (already-closed, awaiting result) round with a countdown of `00 : 00 : 00`, then future rounds with live countdowns and their close times.
- Example at 18:58: round 52 displayed `00:00:00` with “ปิดรับ 07/11/2569 18:45:00”; round 53 displayed `00:02:48` until 19:00.
- The countdown is computed from the server-seeded clock, not from the user’s clock.
- When a round closes, the card does not disappear; it remains in the pending grid until the result is published, then moves to the result grid.

Classification: OBSERVED.

## 7. State transitions observed

For round 53 (period 229):

1. **Open for betting** until 19:00:00.
2. **Closed / pending result** after 19:00:00; card shows `00:00:00`; the round page shows “ปิดรับการทายผลตัวเลขออกรางวัล”.
3. **Number pool visible** during the shooting window; the page reloads at 19:02:00 (`close_date + 2 min`).
4. **Result published** by 19:02:47 at the latest; the result block (`ผลรางวัล`, top 3, bottom 2) appears in server HTML.
5. The round card appears in the result grid with top/bottom numbers.

For round 55 (period 231), the result was present by 19:32:18 and absent at 19:32:01.

Classification: OBSERVED.

## 8. Are all 88 rounds identical in timing?

- Rounds 52–88 on 7 Nov were all exactly 15 minutes apart (OBSERVED).
- Rounds 1–51 are inferred from the 15-minute grid and the published rule.
- No round-gap, skipped round in the visible grid, or daylight-saving transition exists (Thailand has no DST).
- Whether the server ever delays, advances, cancels, or pauses a round is UNKNOWN; the `is_cancel` field exists in the period payload, but no cancelled round was observed.

Classification: OBSERVED for the visible grid; UNKNOWN for exceptional server-side behavior.

## 9. What is not scheduled

- Result computation is not scheduled at a fixed posted minute; it follows the shooting window (close+2 min) and appears within seconds in the observed cases.
- The published rule says tickets are checked one minute after shooting closes (close+3 min) and payouts finish within 2–5 minutes; observed publication was earlier than the documented check time in round 55 (see `timing_analysis.md`).

