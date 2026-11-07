# REA Evidence Verification

Phase C, 2026-11-08. This file records the exact REA operations used, their evidence IDs, the runtime evidence they corroborate, and their limitations. It deliberately separates what REA confirmed from what was obtained only through agent-browser or from the saved Phase A/B reports.

## 1. Environment

| Item | Value |
|---|---|
| CDP endpoint | `http://127.0.0.1:62118` |
| Browser | Chrome for Testing 154.0.8037.57 (headless) |
| Browser host | macOS arm64 |
| REA connection | MCP server, loopback CDP |
| Page origin | `https://thlotto.com` |
| Session | authorized member session; single-login policy active |

## 2. REA operations

| ID | Operation | Target / parameters | Evidence ID | What it confirmed | Limitations |
|---|---|---|---|---|---|
| REA-C01 | `list_browser_targets` | CDP 62118, allowed origin `https://thlotto.com` | `ev_f36b5417bcbc318aefdf575c28184557d2a00ed03b78a358318a39be4a2c7a1d` | A live page target exists at `https://thlotto.com/member/news` (later navigated to round detail) | Attachment state unknown; only exact-origin page targets listed |
| REA-C02 | `inspect_web_page` | Round detail `/member/lottery/yeekee/249`, observation 65,000 ms, JSON/WS/storage shapes | `ev_942135b8ad6c196646ea89acb139556bdce4f33389bd9b27a87996868c9005da` | One `GET /member/lottery/yeekee-list-number?id=249&limit=19&offset=0` request during the 65 s window; no WebSocket; `localStorage` key `pusherTransportTLS` | Attach starts after page load, so the initial list/chart requests are not captured; raw bodies/cookies/values not retained; accessibility/scripts policy-filtered |
| REA-C03 | `analyze_web_bundle` | Round detail 249, observation 1,200 ms, script sources, no source maps | `ev_84dfc67f4d52f13250f877cf030712a949d5db99edf74ee7a9d38731fc3637db` | 12 scripts parsed; `main.js?v=7.5` is 1,042,206 bytes with SHA-256 `74edfa0642efbbcbe127650a51bd04e5d87e22d0c6d8f3e323adaae593b27772`; endpoint candidate `POST /member/lottery/yeekee`; routes `/member/lottery/yeekee`, `/member/lottery/yeekee264`, etc. | Static only; REA does not execute JS; endpoint candidates are low-confidence; it does not enumerate `setInterval` timers |
| REA-C04 | `capture_web_screenshot` | Round detail 249 | `ev_f38aea83b8cf8d9a1f7ad902128a61ee30d309750d97e72a1739e4a64282088c` | Visible viewport of the authorized round page | Viewport only; no scroll, no JS evaluation |
| REA-C05 | `list_browser_targets` | CDP 62118, main list page | `ev_869c097d56a22e137a7754e09ad08faf93a23d63c30107d33e40f47f0bd49b50` | Live target at `/member/lottery/yeekee` | Attachment unknown |
| REA-C06 | `inspect_web_page` | Main list `/member/lottery/yeekee`, observation 70,000 ms | `ev_1113b5a09f78f11e9666d6225c583bad29b5d1b151aa252a4b4b2356790499f1` | **Zero allowed-origin network requests** during 70 s on the list page; no WebSocket | Attach-limited; prior activity unavailable; does not count DOM cards |

## 3. What REA confirmed

1. **Target identity:** the browser was on the exact `https://thlotto.com` origin and the expected routes.
2. **Round-detail XHR:** during the 65 s round-detail observation, REA saw a single `yeekee-list-number` request. This is consistent with the 60 s client timer and rules out continuous per-second polling.
3. **List-page inactivity:** during the 70 s list-page observation, REA saw **zero allowed-origin** network requests. This independently supports “the grid does not poll.”
4. **Bundle identity:** the delivered `main.js` hash matches the Phase B copy (`74ed...`), so the static analysis and the runtime page refer to the same artifact.
5. **Endpoint presence:** the bundle contains the POST `/member/lottery/yeekee` endpoint and the Yeekee route family.
6. **Storage:** `localStorage` contains only `pusherTransportTLS`; no round-state store.

## 4. What REA did not confirm (and what did)

| Observation | Confirmed by | REA role |
|---|---|---|
| Exact 60 s interval (59,991 ms; 119,991 ms) | agent-browser network log | REA saw one repeat within 65 s; did not measure the exact interval |
| Round-detail initial list + chart at page load | agent-browser network log | REA attached after load; initial requests not captured |
| Grid count 71→72 at 00:00 | agent-browser server fetch | Not REA-confirmed |
| 16-round dataset (2,474 rows) | agent-browser page fetches + parser | Not REA-confirmed |
| 13/18 ordering inversions | derived from saved rows | Not REA-confirmed |
| Row 16 in +119 s group (16/16) | derived from saved rows | Not REA-confirmed |
| Historical date-filter behavior | agent-browser fetches | Not REA-confirmed |
| Formula verification (Phase A/B) | `verify_formula.py` on saved CSVs | Not re-run by REA |

## 5. Runtime evidence referenced

From Phase B/C agent-browser observations:

- Round detail 238:
  - `21:03:28.278` list-number (initial)
  - `21:03:28.278` chart (initial)
  - `21:04:28.269` list-number (59,991 ms)
  - `21:05:28.269` list-number (119,991 ms)
- Main list: no round-data XHR over 70 s.
- Result page: no round-data XHR over 72 s.
- Grid counts: 51 (18:58), 53 (19:23), 59 (20:55), 62 (21:30), 71 (23:49), 72 (00:00:37).

## 6. REA limitations (verbatim from the tool, summarized)

- Observation starts at attach; prior network/console activity is unavailable.
- Raw headers, bodies, cookies, storage values, console objects, and WebSocket payloads are never retained.
- Source maps are reported only as declarative URLs and are not fetched.
- URL-less scripts and events are excluded.
- Attachment state is unknown.
- `analyze_web_bundle` does not execute JavaScript; endpoint candidates are low-confidence and not a complete call-site census.
- Screenshots are viewport-only and do not evaluate JavaScript.

## 7. Separation of evidence classes

**REA-confirmed:**
- exact origin/routes;
- one round-detail list-number request in 65 s;
- zero allowed-origin list-page requests in 70 s;
- main.js artifact hash and endpoint presence;
- visible round page screenshot.

**Agent-browser-confirmed (runtime):**
- exact 60 s poll intervals;
- initial list + chart;
- grid counts and midnight boundary;
- historical date-filter behavior;
- 16-round row data.

**Saved-report-only (not re-observed in Phase C):**
- Phase A round-55 5/146 and 51/49;
- Phase A p-values;
- Phase A 53-result snapshot;
- Phase B specific grid-lag timings.

The saved raw CSVs support many of these, but they were not re-collected in Phase C except where noted.

## 8. Verdict

REA is operational and adds independent confirmation of the key runtime claims:

- the round-detail page performs a **sparse XHR poll** (one request in 65 s), not per-second polling;
- the round-list page performs **no allowed-origin network requests** over 70 s;
- the delivered `main.js` is the same artifact analyzed statically;
- the page/origin/routes are exactly as reported.

REA does **not** replace the row-level timestamp analysis or the historical UI tests; those remain agent-browser/derived evidence.
