# Unknowns and Limitations

This file records what could not be established, why, and what evidence would be needed. It is deliberately conservative: absence of evidence is not evidence of absence.

## 1. Access and session limitations

- The account is subject to **single-active-session enforcement**. During the research the site repeatedly returned `{"error":"Your session is invalid (prevent multiple login)"}` after another login to the same account. Each drop required re-authentication and interrupted in-flight timers.
- Long uninterrupted observations (e.g. a full 88-round day in one tab) were therefore not possible.
- All observations are from a normal member account. No administrative, agent, or operator interface was accessed.

Classification: OBSERVED limitation.

## 2. Historical data limitations

- Older round pages (`/member/lottery/yeekee/{id}` for ids 83, 84, 170, 171, …) returned **404** in this session. Only current-day periods (172–264 on 2026-11-07) were reachable.
- The results page supports a date filter, but for the 88-round Yeekee product it showed only the latest round; the 264-round “จับยี่กีทันใจ” product did show per-round history for past dates.
- `?date=` on the main Yeekee page was ignored (same content returned).
- Consequence: the statistical dataset is **53 published rounds**, not thousands. This is far too small to test 3-digit uniformity or subtle serial dependence.

Classification: OBSERVED.

## 3. Backend unknowns

The following could not be established from client-visible evidence:

- Server language/framework version (Laravel is a strong inference from `XSRF-TOKEN`, Mix-style bundles, and error/header patterns, but not proven).
- Database engine, schema, table names, keys, indexes, or storage architecture.
- Whether the sum is computed in SQL, PHP, a queue job, or another service.
- Whether submissions are inserted in real time or batched at the end of the window.
- The exact ordering/tie-break used for rows with the same `created_at` second.
- Whether the server validates the 5-digit rule independently of the client.
- Rate limits, CAPTCHA, fingerprinting, or anti-automation controls (none observed in the UI; not tested).
- Whether cancelled rounds (`is_cancel`) suppress results or refund automatically.
- How negative or underflowed results are handled.
- How the “fewer than 20 submissions → refund” rule is implemented and displayed.
- The exact trigger for the shooting window opening (~close − 2 min).
- Whether any hidden administrative adjustment exists.

Classification: UNKNOWN.

## 4. Things deliberately not tested

The research rules prohibit active exploitation and gambling automation. The following were therefore **not** performed:

- submitting a number to `/member/lottery/yeekee` (even a test number),
- placing any bet,
- testing whether bets are accepted after `close_date`,
- probing undocumented endpoints, `/api`, or `/pusher/auth`,
- brute-forcing identifiers or enumerating other members,
- vulnerability scanning, fuzzing, or rate-limit testing,
- retrieving unpublished results or internal services.

As a result, server-side enforcement of the betting cut-off, the submission cut-off, and validation rules remains INFERRED rather than proven.

## 5. Measurement limitations

- HTTP `Date` headers have 1-second granularity; clock comparison is ±1 s.
- The publication probe used a 5-second interval; the round-55 transition is bracketed as `(19:32:01, 19:32:18]`.
- The browser tab itself was not observed reloading at 19:32:00; the bracket comes from server fetches.
- Network latency to the Cloudflare BKK edge was not measured per request.
- No packet capture was taken; only browser-level request/response metadata.
- Pusher frames were not captured; the channel/event names come from the inline client script, not from decoded frames.

## 6. Client-side evidence limitations

- `main.js.map` is a self-map: `sources: ["webpack:///public/assets/js/app/main.js"]` and `sourcesContent` contains the bundled file, not the original Vue SFCs. It does not expose original comments or component structure.
- The bundle is minified; some dynamic behavior may be obscured by string construction or runtime configuration not visible statically.
- No client-side result function was found, but that does not prove the server has no other logic; it only proves the browser does not compute the result.
- The JWT was decoded for claims only; no signature verification or replay test was attempted.

## 7. Rules interpretation unknowns

- The published worked example subtracts `34529` from `2543565` and presents `2509036`. The example does not state modulo arithmetic; only the last five digits are used. For negative `R`, the display is undefined.
- “เลขลำดับที่ 16” is not explicitly defined as newest-first. The observed UI makes row 16 the 16th newest, but the prose could be read as the 16th chronologically. The UI behavior is authoritative for the observed rounds.
- The bonus wording (“ลำดับที่ 1”) conflicts with a newest-first reading if one assumes “first to submit”. The site rewards whatever row 1 displays; that is the newest submission in the observed UI.

## 8. Temporal validity

All observations are a snapshot of 2026-11-07 (Asia/Bangkok). The operator can change:

- the result rule,
- the shooting window,
- the row ordering,
- the API schema,
- the asset bundle version (`?v=7.5` at capture),
- Cloudflare/header configuration.

Any downstream simulator should pin the observed rule and date, and re-verify against fresh rounds before relying on it.

## 9. What additional evidence would resolve the open questions

| Open question | Evidence needed |
|---|---|
| Exact backend rule and edge cases | Operator documentation, a responsible-disclosure response, or a controlled audit with authorization |
| Historical result distribution | A lawful archive of thousands of rounds (public results, or operator export) |
| Tie-break within one second | Server-side ordering field or a documented rule; API does not expose a submission id |
| Betting cut-off enforcement | Authorized test of a rejected late bet (not performed; would require operator permission) |
| Submission validation and rate limits | Authorized negative tests with operator consent |
| Payout/refund behavior | Observation of a <20-submission round or a cancelled round |
| Shooting-window trigger | Server logs or operator documentation |
| Whether results are computed on demand or by a job | Server logs/metrics; not visible to clients |
| Bias in final sum | Tens of thousands of complete pools with timestamps, not just results |

## 10. Bottom line

The arithmetic is well established. The backend implementation, exceptional cases, and long-run statistical properties are not. No conclusion in this report should be read as proof of private backend behavior; the strongest claims are the ones backed by exact reproduction of publicly displayed data.
