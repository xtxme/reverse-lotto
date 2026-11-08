# Findings Register

Every finding below carries the eight required fields. Times are Asia/Bangkok on 2026-11-07 unless stated. Classification: OBSERVED / INFERRED / HYPOTHESIS / UNKNOWN.

## ENV-01 — REA and browser stack operational

- **Classification:** OBSERVED
- **Evidence:** `agent-browser doctor` passed CLI, Chrome-for-Testing 154, state dir, and daemons. REA `list_browser_targets`, `inspect_web_page`, and `analyze_web_bundle` returned evidence IDs without timeout.
- **Observed at:** 18:56–19:01
- **Source:** local tool output; REA evidence `ev_c22a…`, `ev_2b31…`, `ev_62e7…`, `ev_316f…`
- **Reproduction:** run `agent-browser doctor`; call REA `list_browser_targets` against the loopback CDP endpoint.
- **Confidence:** High
- **Limitations:** Chrome-for-Testing CDN was unreachable, but the installed browser worked; update checks are not part of the observation path.

## FE-01 — Frontend stack

- **Classification:** OBSERVED
- **Evidence:** served scripts include jQuery 3.5.1, Bootstrap bundle, Laravel-Mix-style `manifest.js`/`vendor.js`/`main.js?v=7.5`, PNotify, Nanobar, Hotkeys, Pusher 7.0. No Next/Nuxt/React/Angular roots.
- **Observed at:** 18:57
- **Source:** DOM script list, `main.js`, page HTML
- **Reproduction:** open the Yeekee page, list `script[src]`, check `window.__NEXT_DATA__`, `__NUXT__`, `[data-reactroot]`, `window.ng`.
- **Confidence:** High
- **Limitations:** framework inference (Laravel) is not proven; only the client stack is proven.

## FE-02 — Server-rendered round state

- **Classification:** OBSERVED
- **Evidence:** round grid, round detail, submission rows, sum, 16th row, and result are all present in the initial HTML. No round-data XHR is needed to render them.
- **Observed at:** 18:58–19:02
- **Source:** page HTML, network log
- **Reproduction:** disable JavaScript or inspect the raw HTML; the 88 cards and result block remain.
- **Confidence:** High
- **Limitations:** the Vue island still hydrates the betting UI; not every element is static.

## FE-03 — Countdown seeded from server time

- **Classification:** OBSERVED
- **Evidence:** inline script embeds `serDateTime` and computes `offset = serDateTime − Date.now()`; the stored server time increments by 1000 ms each tick.
- **Observed at:** 18:57:33
- **Source:** inline page script
- **Reproduction:** read the inline script on a round page; compare `serDateTime` with the HTTP `Date` header.
- **Confidence:** High
- **Limitations:** no periodic re-sync; long-tab drift magnitude not measured.

## FE-04 — Pusher is agent-notification only

- **Classification:** OBSERVED
- **Evidence:** `new Pusher(<public key>, {cluster:"ap1"})`; subscribes to `notic.agentid.33`, binds `numbersets`, calls `/member/number-recommend-notified`, shows a PNotify toast.
- **Observed at:** 18:57:33
- **Source:** inline script; network log
- **Reproduction:** inspect the inline Pusher block on the Yeekee page.
- **Confidence:** High
- **Limitations:** WebSocket frames were not captured; channel/event names come from the script.

## FE-05 — Page auto-reloads at shoot close

- **Classification:** OBSERVED
- **Evidence:** `a<0 && (…, window.location.reload())` in `intervalTimer`, where `a` is the countdown to `close_date + 2 min`.
- **Observed at:** 19:00–19:02 (behavior consistent with the code)
- **Source:** `main.js`
- **Reproduction:** read the `intervalTimer` function in `main.js`.
- **Confidence:** High
- **Limitations:** the exact reload instant was not captured with a live tab; server fetches bracketed the result.

## RS-01 — 88 rounds at 15-minute intervals

- **Classification:** OBSERVED (52–88) / INFERRED (1–51)
- **Evidence:** 37 pending cards from 18:45 to 03:45, all 15 minutes apart; 53 published results; rules state 88 rounds.
- **Observed at:** 18:58
- **Source:** `/member/lottery/yeekee` HTML
- **Reproduction:** parse `.card-items` close times; subtract 15 minutes.
- **Confidence:** High
- **Limitations:** exceptional delays/cancellations not observed.

## RS-02 — First and last round times

- **Classification:** OBSERVED (rules/UI) + INFERRED (round 1 arithmetic)
- **Evidence:** rules say first 06:00, last 03:45; observed round 52 = 18:45, so round 1 = 06:00; observed round 88 = 03:45 next day.
- **Observed at:** 18:58, 19:36
- **Source:** rules modal; card grid
- **Reproduction:** `18:45 − 51×15 min = 06:00`.
- **Confidence:** High
- **Limitations:** round 1 card was not directly observed as a future card.

## RS-03 — Cross-midnight scheduling

- **Classification:** OBSERVED
- **Evidence:** rounds 73–88 display `08/11/2569` while numbering continues 73…88.
- **Observed at:** 18:58
- **Source:** card grid
- **Reproduction:** parse close dates for rounds 73–88.
- **Confidence:** High
- **Limitations:** none material.

## RS-04 — Period IDs are not a constant round offset

- **Classification:** OBSERVED
- **Evidence:** round 1→172, 32→203, 33→209 (gap 204–208), 52→228, 88→264; internal `current_period_id` differs (round 55→802206).
- **Observed at:** 18:58–19:36
- **Source:** card `data-href`; `betconfig`
- **Reproduction:** compare round numbers to URL IDs.
- **Confidence:** High
- **Limitations:** reason for gaps unknown.

## SUB-01 — Five-digit submission contract

- **Classification:** OBSERVED
- **Evidence:** `name=ykn`, `type=tel`, `maxlength=5`, placeholder “กรอกเลข 5 หลัก”, VeeValidate `required|numeric|digits:5`.
- **Observed at:** 18:59
- **Source:** round page DOM and `main.js`
- **Reproduction:** open the “ยิงเลข” tab and inspect the input.
- **Confidence:** High
- **Limitations:** server-side enforcement not tested.

## SUB-02 — Public masked submission list

- **Classification:** OBSERVED
- **Evidence:** rows show masked username, 5-digit number, row number, timestamp; 50 rows/page; API returns at most 20 latest.
- **Observed at:** 19:02–19:33
- **Source:** round page; `yeekee-list-number`
- **Reproduction:** `/member/lottery/yeekee/229?page=2`.
- **Confidence:** High
- **Limitations:** no bet amounts or private fields are exposed.

## SUB-03 — Newest-first order; row 16 is display position

- **Classification:** OBSERVED (order); UNKNOWN (intra-second tie-break)
- **Evidence:** row 1 is the latest timestamp, last row is the earliest; row 16 falls in the final-second batch in all three observed rounds. Counter-test: using the 16th chronological submission gives 9,202,621 (round 53) and 7,637,296 (round 54), which do not match the published 9,201,269 and 7,661,325, while display row 16 matches both.
- **Observed at:** 19:02–19:33
- **Source:** round pages; timestamps per row
- **Reproduction:** parse row timestamps and compare with row index.
- **Confidence:** High for order; Medium for tie-break semantics
- **Limitations:** no submission ID exposed.

## SUB-04 — Shooting window spans roughly close −2 min to close +2 min

- **Classification:** OBSERVED (timestamps) / INFERRED (window rule)
- **Evidence:** earliest submissions 18:58:55 (close 19:00), 19:13:35 (close 19:15), 19:27:53 (close 19:30); latest always `close+1:59`; `closeDateYeekee = close+2 min`.
- **Observed at:** 19:00–19:32
- **Source:** row timestamps; `betconfig`
- **Reproduction:** list the earliest and latest `created_at` per round.
- **Confidence:** High for the end boundary; Medium for the start boundary
- **Limitations:** the server’s exact open trigger is unknown.

## SUB-05 — Bursty, non-uniform submissions

- **Classification:** OBSERVED (counts); INFERRED (automation)
- **Evidence:** 151–173 submissions; 51 at one second in round 55; duplicate excess 9/173 and 13/164 vs ~0.15 expected; recurring numbers `37553`, `55014`, `55555`.
- **Observed at:** 19:02–19:33
- **Source:** CSV lists; timestamps
- **Reproduction:** `randomness_tests.py` duplicate/first-digit sections; count timestamps.
- **Confidence:** High for statistics; Low for the automation explanation
- **Limitations:** automation is not proven; members may repeat favorites.

## NET-01 — `yeekee-list-number` endpoint

- **Classification:** OBSERVED
- **Evidence:** `GET /member/lottery/yeekee-list-number?id=229&limit=19&offset=0` → `{lists:[…],sum:"9281577"}`; 20-row cap; newest-first; dynamic; ETag.
- **Observed at:** 18:58–19:33
- **Source:** network log; page-initiated call
- **Reproduction:** call the endpoint from the authenticated page context.
- **Confidence:** High
- **Limitations:** non-empty chart payload not observed; POST contract inferred.

## NET-02 — `yeekee-chart` endpoint

- **Classification:** OBSERVED (endpoint/empty response) / UNKNOWN (non-empty shape)
- **Evidence:** `GET /member/lottery/yeekee-chart?id=229&limit=19&offset=0` → `{"lists":[]}`; client maps `lists` to sum/created_at.
- **Observed at:** 18:58
- **Source:** network log; `main.js`
- **Reproduction:** call the endpoint on an unprocessed round.
- **Confidence:** High for the endpoint; Medium for the shape
- **Limitations:** chart history was not retained.

## NET-03 — Submission POST contract (not executed)

- **Classification:** OBSERVED in code / INFERRED contract
- **Evidence:** `axios.post("/member/lottery/yeekee", {number, bet_category_id, yeekee_special})`; success path reads `status`, `lists`, `sum`.
- **Observed at:** 18:59
- **Source:** `main.js`
- **Reproduction:** read `submitYeekeeNumber` in `main.js`.
- **Confidence:** High for the request; Medium for the response
- **Limitations:** deliberately not invoked; server validation unknown.

## NET-04 — No round polling

- **Classification:** OBSERVED
- **Evidence:** idle page produced only Cloudflare RUM; no periodic round/list requests; updates require reload.
- **Observed at:** 19:01 (5 s REA observation) and 19:26–19:29 (15 s timer)
- **Source:** network log; REA inspection
- **Reproduction:** idle on the page and list XHRs for 60 s.
- **Confidence:** High
- **Limitations:** observation windows were short; hidden long-interval polling cannot be fully excluded.

## EXP-01 — Public source maps

- **Classification:** OBSERVED
- **Evidence:** `main.js.map` 1,086,250 bytes, 200, `sources:["webpack:///public/assets/js/app/main.js"]`, `sourcesContent:true`; vendor/manifest maps also served.
- **Observed at:** 19:00
- **Source:** curl of public assets
- **Reproduction:** `curl -I https://thlotto.com/assets/js/app/main.js.map`.
- **Confidence:** High
- **Limitations:** self-maps, not original Vue sources; no secrets found.

## EXP-02 — JWT without `exp`

- **Classification:** OBSERVED (claims) / INFERRED (risk)
- **Evidence:** HS256; payload `{payload:{uid},iat}`; no `exp`/`aud`/`iss`/`jti`; used as Bearer for axios `/api` and `/pusher/auth`.
- **Observed at:** 18:57
- **Source:** inline `window.App`; `main.js`
- **Reproduction:** decode the JWT payload in the page (metadata only).
- **Confidence:** High for claims; Medium for exploitability
- **Limitations:** server-side token validation/rotation unknown; no replay test.

## EXP-03 — Cookie flags

- **Classification:** OBSERVED
- **Evidence:** `core-session` and `core-session-value` are HttpOnly, lack Secure and SameSite, ~30-day expiry; `XSRF-TOKEN` is JS-readable by design.
- **Observed at:** 18:56–19:46
- **Source:** `Set-Cookie` headers
- **Reproduction:** `curl -I https://thlotto.com/login`.
- **Confidence:** High
- **Limitations:** HTTP 301 to HTTPS mitigates cleartext; browser defaults may apply SameSite=Lax.

## EXP-04 — Missing security headers

- **Classification:** OBSERVED
- **Evidence:** no CSP, HSTS, Referrer-Policy, or Permissions-Policy on observed app responses; XFO/nosniff/XSS-protection present.
- **Observed at:** 19:07–19:40
- **Source:** curl headers
- **Reproduction:** `curl -I https://thlotto.com/login`.
- **Confidence:** High
- **Limitations:** headers may vary by path/edge; only sampled paths.

## EXP-05 — Public submission transparency

- **Classification:** OBSERVED
- **Evidence:** masked usernames + full 5-digit numbers + timestamps are public and paginated; rules promise verifiability.
- **Observed at:** 19:02–19:33
- **Source:** round pages
- **Reproduction:** open any published round.
- **Confidence:** High
- **Limitations:** intentional; no private fields exposed; scraping risk not tested.

## EXP-06 — `/api` and `/pusher/auth` visible

- **Classification:** OBSERVED
- **Evidence:** `axios.defaults.baseURL="/api"`; Pusher `authEndpoint:"/pusher/auth"` with Bearer JWT.
- **Observed at:** 18:59
- **Source:** `main.js`
- **Reproduction:** search `main.js` for `baseURL` and `authEndpoint`.
- **Confidence:** High
- **Limitations:** endpoints not probed; only the client configuration is shown.

## ALG-01 — Published result rule

- **Classification:** OBSERVED
- **Evidence:** rules modal: sum all submitted 5-digit numbers, subtract the 16th number, use the difference; example 2,543,565 − 34,529 = 2,509,036 → 036/09.
- **Observed at:** 18:59, 19:36
- **Source:** `#modal-rule`; screenshot `rules_modal_round55.png`
- **Reproduction:** open “กติกา” on any round page.
- **Confidence:** High
- **Limitations:** prose does not define negative/modulo edge cases or tie-break.

## ALG-02 — Three-round exact verification

- **Classification:** OBSERVED
- **Evidence:** rounds 53/54/55 reproduce sum, 16th, result, top3, bottom2 exactly from complete public lists (488 submissions total).
- **Observed at:** 19:02–19:33
- **Source:** round pages; `verify_formula.py`; `timing_observations.json`
- **Reproduction:** `python3 verify_formula.py`; round 55 reconstructed from 151 rows.
- **Confidence:** High for these rounds
- **Limitations:** not proof of every backend side-effect; only observed rounds.

## ALG-03 — Digit extraction

- **Classification:** OBSERVED
- **Evidence:** example and live rounds show last five digits; leftmost two = bottom2, rightmost three = top3 (e.g. 01269 → 01/269).
- **Observed at:** 19:02–19:33
- **Source:** rules example; published results
- **Reproduction:** apply the mapping to any verified round.
- **Confidence:** High
- **Limitations:** negative results not observed.

## ALG-04 — Leading zeros treated as integers

- **Classification:** OBSERVED
- **Evidence:** rows `00753`, `03002`, `00000` occur; integer summation reproduces the published total exactly.
- **Observed at:** 19:02–19:20
- **Source:** CSVs; sum match
- **Reproduction:** sum the CSV with `int()`.
- **Confidence:** High
- **Limitations:** none material for non-negative sums.

## TIM-01 — Server clock aligned with local clock

- **Classification:** OBSERVED
- **Evidence:** HTTP `Date` and local UTC agree within ±1 s across three samples.
- **Observed at:** 19:06:29–19:06:31
- **Source:** curl `-I`
- **Reproduction:** compare the `date` header with `date -u`.
- **Confidence:** High
- **Limitations:** 1-second header granularity.

## TIM-02 — Result published within 18 s of shoot close

- **Classification:** OBSERVED (bracket)
- **Evidence:** round 55 page had no result at 19:32:01 and had it at 19:32:18; shoot close 19:32:00.
- **Observed at:** 19:32:01–19:32:18
- **Source:** server HTML fetches; `timing_observations.json`
- **Reproduction:** poll the round page at 5 s intervals around `close+2 min`.
- **Confidence:** High for the bracket
- **Limitations:** single-round tight measurement; true instant within the 17 s window.

## TIM-03 — Documented +1 min check vs observed near-immediate result

- **Classification:** OBSERVED (presence) / INFERRED (processing model)
- **Evidence:** rules say checking at close+3 min; round 55 had a result at ~close+2m18s.
- **Observed at:** 19:32
- **Source:** rules modal; timing probe
- **Reproduction:** compare the first result time with `close_date + 3 min`.
- **Confidence:** Medium
- **Limitations:** payout timing not observed; result presence ≠ payout completion.

## PRED-01 — Final inputs arrive after betting close

- **Classification:** OBSERVED
- **Evidence:** 146/151 round-55 submissions at/after 19:30:00; row 16 can change until 19:32; pool visible but incomplete before close.
- **Observed at:** 19:26–19:32
- **Source:** row timestamps; list endpoint
- **Reproduction:** bucket submission timestamps around `close_date`.
- **Confidence:** High
- **Limitations:** one round quantified precisely; rounds 53/54 show the same end-boundary pattern.

## PRED-02 — No statistical dependence in 53 results

- **Classification:** OBSERVED (tests) / INFERRED (no predictability)
- **Evidence:** last-digit χ² p=0.50; runs p=0.68; lag-1 r=−0.12 within ±0.27; hot-digit p=0.41.
- **Observed at:** 19:23
- **Source:** `results_2026-11-07.json`; `randomness_tests.py`
- **Reproduction:** run the script.
- **Confidence:** Medium (underpowered)
- **Limitations:** n=53; 3-digit uniformity untestable.

## PRED-03 — Empirical-pool Monte Carlo remains near-uniform

- **Classification:** OBSERVED (simulation) / INFERRED (generality)
- **Evidence:** 20k simulations, 337-number empirical pool, 168 draws/round; last-digit χ²=14.04, p=0.12; counts 1923–2086/20000.
- **Observed at:** 19:23
- **Source:** `randomness_tests.py`
- **Reproduction:** run the script (seed 20261107).
- **Confidence:** Medium
- **Limitations:** simulation assumes independence and the observed pool distribution; not a proof about the operator.

## UNK-01 — Backend internals unknown

- **Classification:** UNKNOWN
- **Evidence:** no server code, schema, logs, or admin access; client exposes only application-level IDs and HTML state.
- **Observed at:** entire session
- **Source:** scope constraints
- **Reproduction:** not reproducible without authorization
- **Confidence:** High that it is unknown
- **Limitations:** framework inference only.

## UNK-02 — Historical archive inaccessible

- **Classification:** OBSERVED (limitation)
- **Evidence:** older period pages returned 404; results date filter shows only the latest 88-round Yeekee result; 53 results available.
- **Observed at:** 19:07–19:40
- **Source:** round pages; results page
- **Reproduction:** request an older period ID.
- **Confidence:** High
- **Limitations:** may be account-, time-, or route-dependent; not probed further.
