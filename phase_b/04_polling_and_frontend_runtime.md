# Investigation 4 — Resolving the Polling and Frontend Update Contradiction

Phase B, 2026-11-07. The two prior statements were:

- A previous Codex investigation found frontend code suggesting a **60-second update interval**.
- The OpenCode Phase A report stated there was **no polling of round state** during an idle observation, and that the idle page mainly produced Cloudflare RUM traffic.

Both observations are partly correct. They refer to **different pages and different data**.

## 1. The 60-second timer is real

In `main.js` (the Vue detail component), the mounted hook contains:

```js
this.isYeekee && this.yeekeeCountdownTimer &&
  setInterval(function () { t.getYeekeeNumberList(); }, 6e4)
```

`getYeekeeNumberList()` performs:

```js
$.getJSON("/member/lottery/yeekee-list-number",
  { id: this.betconfig.id, limit: 19, offset: 0 },
  function (t) { this.yeekeeLists = t.lists; this.sumYeekee = t.sum; })
```

So the timer:

- runs **only** on a round-detail page whose Vue component is mounted,
- runs **only** when `isYeekee` and `yeekeeCountdownTimer` are truthy,
- refreshes the **submission list and the running sum**,
- does **not** refresh the round state, the countdown target, the result, or the round grid,
- does **not** fetch the chart (the chart is fetched once on mount).

## 2. Runtime confirmation

Page: `/member/lottery/yeekee/238` (round 62), loaded 2026-11-07 21:03:28.278 local.

| Time | Request | Interval from load |
|---|---|---:|
| 21:03:28.278 | `GET /member/lottery/yeekee-list-number?id=238&limit=19&offset=0` | 0 ms |
| 21:03:28.278 | `GET /member/lottery/yeekee-chart?id=238&limit=19&offset=0` | 0 ms |
| 21:04:28.269 | `GET /member/lottery/yeekee-list-number?id=238&limit=19&offset=0` | **59,991 ms** |
| 21:05:28.269 | `GET /member/lottery/yeekee-list-number?id=238&limit=19&offset=0` | **119,991 ms** |

The second and third requests are exactly 60,000 ms apart. This is a direct runtime confirmation of the `setInterval(..., 6e4)` definition.

## 3. The list page does not poll

Page: `/member/lottery/yeekee`, loaded 21:06:25.541 local. Over the next 70 seconds:

- no `yeekee-list-number` request,
- no `yeekee-chart` request,
- no round-data XHR,
- only static assets and telemetry.

The round grid is server-rendered and is not refreshed by a client timer.

## 4. The result page does not poll

Page: `/member/lottery/yeekee/228`, loaded 21:21:40.117 local. Over the next 72 seconds:

- no round-data XHR,
- no list-number or chart request.

The result page is server-rendered and static.

## 5. Why Phase A saw “no polling”

Phase A’s REA observation window was 5 seconds, and its later timer was 10–15 seconds. A 60-second timer cannot be observed in a 5–15 second window. The Phase A statement was therefore a **capture-window limitation**, not a contradiction of the code. It was correct for the pages it observed (grid/result), and incomplete for the detail page.

## 6. What each timer updates

| Mechanism | Interval | Data | Runtime observed |
|---|---:|---|---|
| Inline countdown `intervalTimer` | 1,000 ms | countdown text | yes (visible) |
| Vue `intervalTimer` | 1,000 ms | bet countdown, `isOpen`, auto-reload | code path; reload not directly timed |
| Vue `intervalYeekee` | 1,000 ms | Yeekee countdown | code path |
| Vue `intervalCloseDate` | 1,000 ms | close countdown | code path (other bet components) |
| Vue `getYeekeeNumberList` | **60,000 ms** | submission list + sum | **yes, +60 s and +120 s** |
| Vue `getYeekeeChart` | once | chart | yes at load only |
| `processBtnYeekee` | 1,000 ms | button cooldown | not invoked (submissions prohibited) |
| `randomYeekeeNumber` | 20 ms | UI animation | not invoked |
| Pusher | 6,000/2,000 ms timeouts | WebSocket transport | loaded; not round data |
| Cloudflare RUM | browser-defined | telemetry | observed |

Full table: `phase_b/frontend_timers.csv`.

## 7. Auto-reload at shoot close

The 1-second `intervalTimer` computes the time to `yeekeeCloseDateExtendTime` (`close_date + 2 minutes`). When it goes negative:

```js
a < 0 && (clearInterval(this.intervalYeekee),
          this.yeekeeCountdownTimer = "หมดเวลาแทงพนัน",
          window.location.reload())
```

So the **result page is reached by a full document reload** at `close + 2 min`, not by polling. This is consistent with Phase A’s server-rendered result block.

The reload can race the result computation: in Phase A, a fetch at 19:32:01 had no result; the result was present at 19:32:18. A browser that reloaded exactly at 19:32:00 could see “pending” and would need a manual refresh.

## 8. The list page’s result grid lags the detail page

This is a separate server-side state issue, not a client polling issue.

| Event | Time | Grid boundary |
|---|---|---|
| Round 60 detail page shows result | 20:57:41 | — |
| Round 60 appears in the result grid | 21:00:56 (first observed) | 21:00:00 (round 61 close) |
| Round 61 appears in the result grid | 21:16:23 (observed) | 21:15:00 (round 62 close) |
| Round 62 detail page shows result | 21:17:16 | — |
| Round 62 appears in the result grid | 21:30:28 (observed) | 21:30:00 (round 63 close) |

The grid is not updated by the 60-second detail-page timer. The grid is a separate server-rendered view whose result set is refreshed on the **15-minute round boundary**:

- round 60 was added at the 21:00 boundary,
- round 61 was added at the 21:15 boundary,
- round 62 was added at the 21:30 boundary.

This is an INFERENCE from three consecutive boundaries, but the timing is exact to the minute and consistent. The detail page can show a result ~16 seconds after shoot close, while the grid will not show it until the next round closes — a lag of up to ~15 minutes. No client XHR was observed for the grid.

The likely implementation is a server-side result table or cache refreshed by a 15-minute job, but the exact mechanism is **UNKNOWN** without server logs.

**Implication:** a user looking only at the round list can see a stale “latest result” for several minutes after the detail page has the result. This is a frontend/state consistency issue, not evidence that the result is unpublished.

## 8.1 Tool reliability note

One 3-minute in-page monitor launched through a long CLI `eval` hit the agent-browser daemon socket error `Resource temporarily unavailable (os error 35)`. The browser process remained alive; the run was discarded and replaced with short, non-blocking reads and a page-side interval that returned immediately. No data from the failed run is used in this report.



Not measured. Chrome throttles background-tab timers, so the 60-second poll may run late in a background tab. The runtime test used the active tab. This does not affect the code-level conclusion; it affects the timing of stale data in a background tab.

## 10. Which observations are reproducible?

| Observation | Reproducible? |
|---|---|
| Detail page polls list-number every 60 s | **YES** (two intervals measured) |
| Detail page fetches chart once | **YES** |
| Grid page does not poll | **YES** (70 s window) |
| Result page does not poll | **YES** (72 s window) |
| Auto-reload at shoot close | Code path; not directly timed in Phase B |
| Grid lags detail page | **YES** for three consecutive rounds (60, 61, 62); refresh at 15-minute boundaries |
| Phase A “no polling” | **CONTRADICTED for the detail page**, correct for grid/result pages |

## 11. Verdict

The contradiction is resolved:

- **Codex was right** about a 60-second timer in the delivered code.
- **OpenCode was right** that the grid/result pages do not poll.
- The 60-second timer belongs to the **round-detail submission list/sum**, not to round state or the result.
- The grid’s lag is server-side and separate from the client timer.
- Phase A’s “no polling” claim must be narrowed to “no polling of round state or result on the grid/result pages.”
