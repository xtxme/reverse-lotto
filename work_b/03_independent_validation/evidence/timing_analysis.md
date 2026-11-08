# Timing and Publication Analysis

All times are Asia/Bangkok (UTC+7) on 2026-11-07 unless stated otherwise. HTTP `Date` headers were compared with the local UTC clock; the offset was within ±1 second (limited by one-second header granularity). The site itself instructs users to trust server time.

## 1. Clock reference

```
server: Sat, 07 Nov 2026 12:06:30 GMT
local : 2026-11-07 19:06:29.6 +07  → 12:06:29.6Z
server: Sat, 07 Nov 2026 12:06:31 GMT
local : 2026-11-07 19:06:30.9 +07  → 12:06:30.9Z
```

Observed offset: effectively 0, with ≤1 s measurement uncertainty. No evidence of server clock drift relative to the research host.

## 2. What controls the countdown

- The page embeds a server timestamp (`serDateTime`) at render time and a server-provided `close_date`.
- The script computes `offset = serDateTime − Date.now()` once, then renders the remaining time each second from the server anchor.
- It does not re-sync with the server on every tick.
- When the **shoot-window** target (`close_date + 2 minutes`) goes negative, the page calls `window.location.reload()`.

Consequences:

- The countdown is robust to a wrong client clock at page load.
- A tab left open for hours can drift by the host’s clock drift (not measured).
- The transition to the result is a full page reload, not an AJAX update.

Classification: OBSERVED for the mechanism; drift magnitude UNKNOWN.

## 3. Scheduled vs observed close

For round 55 (period 231), the server payload contained:

```
open_date        = 2026-11-06T22:00:00.000Z  (= 05:00 local)
close_date       = 2026-11-07T12:30:00.000Z  (= 19:30 local)
closeDateYeekee  = 2026-11-07T12:32:00.000Z  (= 19:32 local)
```

The betting close was exactly 19:30:00 and the shoot close exactly 19:32:00, matching the 15-minute grid and the +2-minute extend time. No delay or advance was observed in the three measured rounds.

## 4. Publication measurements

### Round 55 — tightest measurement

The result page was fetched every 5 seconds around the transition:

| Local time | Page status | Result block present? | Sum | 16th | Raw result |
|---|---|---|---|---|---|
| 19:32:01 | 200 | **no** | — | — | — |
| 19:32:18 | 200 | **yes** | 7,422,657 | 58,470 | 7,364,187 |
| 19:32:23 | 200 | yes | 7,422,657 | 58,470 | 7,364,187 |
| … | … | yes (stable) | … | … | … |

- Shoot window closed at 19:32:00.
- Result was absent at 19:32:01 and present at 19:32:18.
- **Upper bound: 18 seconds after shoot close.**
- No client-side delay was involved: the result is in the server HTML.

### Round 53

- Betting closed 19:00:00; shoot closed 19:02:00.
- The result was already present when the page was read at approximately 19:02:30–19:02:47.
- **Upper bound: ~47 seconds after shoot close** (looser because the exact read time was not logged to the second).

### Round 54

- Betting closed 19:15:00; shoot closed 19:17:00.
- The result was present at 19:20:19 when next checked.
- **Upper bound: 3 m 19 s**, but this is a checkpoint, not a tight measurement.

### Summary

| Round | Betting close | Shoot close | First observed result | Bound after shoot close |
|---|---|---|---|---|
| 53 | 19:00:00 | 19:02:00 | ~19:02:30–47 | ≤47 s |
| 54 | 19:15:00 | 19:17:00 | ≤19:20:19 | ≤3 m 19 s |
| 55 | 19:30:00 | 19:32:00 | 19:32:18 | **≤18 s** |

## 5. Documented vs observed announcement timing

The published rules say:

> After betting closes, the shooting system remains open for 2 minutes. One minute after shooting closes, tickets are checked; payouts take about 2–5 minutes. Example: round 1 closes at 06:00, shooting until 06:02, checking at 06:03, payouts complete by 06:08.

Observed behavior:

- The result block was already present **18 seconds** after shooting closed in round 55, i.e. well before the documented 06:03-style check time.
- The result computation therefore appears to run immediately at/after shoot close, not on a one-minute delay.
- Payout completion is a separate process and was not observed from the member UI (balances were not monitored).

Classification: OBSERVED for result presence; INFERRED for “immediate processing”; payout timing UNKNOWN.

## 6. Browser display vs server response

- The result is not fetched by JavaScript. It is part of the HTML response.
- A browser that auto-reloads exactly at `close + 2 min` may arrive **before** the server has finished computing. In round 55, a fetch at 19:32:01 had no result; the result appeared by 19:32:18.
- Since the auto-reload only happens once (when the shoot countdown crosses zero), a user who reloads too early may see “pending” and must refresh manually. This is a plausible explanation for the site’s conservative “check at +3 minutes” wording.

Classification: INFERRED from the reload code and the 19:32:01/19:32:18 bracket. The exact browser behavior at 19:32:00 was not directly observed because the research used server fetches rather than a live reloading tab at that instant.

## 7. Caching and polling effects

- Member HTML and JSON responses carried `cf-cache-status: DYNAMIC`; no edge caching of round state was observed.
- The JSON list endpoint carried an `ETag`, but the data changed as submissions arrived, so a conditional request would revalidate.
- The page does not poll. Any stale display is due to the absence of a reload, not to cached API data.
- Cloudflare RUM requests (`POST /cdn-cgi/rum`) are telemetry only and do not update the UI.

## 8. Measurement uncertainty

- HTTP `Date` granularity: 1 second.
- Polling interval: 5 seconds in the round-55 publication probe.
- The 19:32:01 fetch is a single point; the true transition lies in `(19:32:01, 19:32:18]`.
- Session invalidation by the site’s single-login policy interrupted some probes; gaps are stated rather than interpolated.
- No attempt was made to access unpublished results or server internals.

## 9. Practical takeaways

1. The betting close is exactly on the 15-minute grid; the shoot close is exactly +2 minutes.
2. The result is usually available within seconds of the shoot close; 18 seconds is the observed upper bound in round 55.
3. Anyone who can read the final pool and sum at 19:32:00 can compute the result before the UI shows it, because the formula is public. This is a **transparency/UI timing gap**, not a betting advantage: betting has already closed at 19:30:00.
4. The auto-reload at 19:32:00 can race the result computation; a manual refresh may be needed.

