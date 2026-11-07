# Site Evidence Log

## Environment and access

| Item | Value |
|---|---|
| Date | 2026-11-07 (Asia/Bangkok, UTC+7) |
| Research host | macOS (darwin, arm64) |
| Browser | Google Chrome for Testing 154.0.8037.57 (headless), CDP on loopback |
| Browser driver | `agent-browser` 0.38.1 |
| REA | MCP server connected; `list_browser_targets`, `inspect_web_page`, `analyze_web_bundle` all executed successfully |
| Account | authorized member account supplied by the requester |
| Authorization | normal login only; no bypass, no credential stuffing, no unauthorized endpoint access |
| Preconditions | `curl` reachability, DNS, TLS, Cloudflare BKK edge |

REA evidence identifiers produced during the session:

- `ev_c22a132a80bf21091e661895a5f5a249f351e7a2cec70361c89c71f9fa52ab87` — first passive page inspection.
- `ev_2b3144c7bae96720e97d027fddc0d897e71c07f9c219238189bab9487d6a28ec` — script-source inspection.
- `ev_62e71282347190c246e16d354fe5e9af77281e8796ac1618dcbd904a48d0f878` — concise script inventory.
- `ev_316f320729f6a784364d8ca99220c36c6f5d2568a76ebc5770fe43fe2c452176` — static bundle analysis (partial capture).
- REA noted limitations: observation starts at attach, source maps are not fetched by `inspect_web_page`, and some sections were policy-filtered by origin. These are recorded rather than hidden.

## Tool reliability

- REA was verified operationally, not just assumed: `list_browser_targets` returned the live `thlotto.com` page target, `inspect_web_page` produced evidence records, and `analyze_web_bundle` parsed the delivered scripts. A `rea doctor` CLI was not present in the shell; the MCP tool surface was used instead.
- One long-running MCP `eval` (a ~5-minute in-page polling loop) caused the agent-browser daemon socket to return `Resource temporarily unavailable (os error 35)` after retries. The browser process remained alive; short calls recovered immediately. That first timing attempt was discarded and replaced by a short-interval, non-blocking page timer. No result was fabricated from the lost run.
- The site invalidated the session repeatedly under its single-login policy. Each drop was handled by re-authentication; no observation was inferred across a gap.

## Observation timeline

| Time (local) | Event | Evidence |
|---|---|---|
| 18:56:40 | `HEAD /member/lottery/yeekee` returned 401; Cloudflare `cf-ray` BKK; session cookies set. | curl headers |
| 18:57 | Logged in with the authorized account; redirected to `/member/news`. | browser session |
| 18:57:33 | Page metadata: jQuery 3.5.1, Bootstrap, Pusher 7.0, Vue bundle, no React/Next/Nuxt; localStorage only `pusherTransportTLS`; timezone Asia/Bangkok. | `site_evidence`, `frontend_architecture.md` |
| 18:58 | 88-card grid captured: rounds 52–88 with close times 18:45 → 03:45; round 1 derived as 06:00. | `screenshots/yeekee_initial.png`, `observed_schedule.json` |
| 18:58 | Countdown rooted at server `serDateTime`; no round AJAX; Pusher channel is `notic.agentid.33`. | inline script, network log |
| 18:59–19:02 | Round 53 closed at 19:00; shoot window to 19:02; result observed by ~19:02:30–47. | round page, `timing_observations.json` |
| 19:02 | Full 173-row list captured; Σ = 9,281,577; row 16 = 80,308; result 9,201,269; top 269 / bottom 01. | `round_229_numbers.csv`, `verify_formula.py` |
| 19:06 | Server `Date` compared with local clock: within ±1 s. | curl headers |
| 19:06 | Round 54 pool empty 8 minutes before close. | list endpoint |
| 19:16:59 | Round 54 final submissions timestamped; sum 7,724,164. | list endpoint |
| 19:20:19 | Round 54 result present: 7,661,325; top 325 / bottom 61; full 164-row list captured. | `round_230_numbers.csv` |
| 19:26–19:29 | Round 55 pool live before betting close: 1 submission at 19:28:02, 5 by 19:29:02; sum 188,748. | `timing_observations.json` |
| 19:30:00 | Round 55 betting close (server `close_date`). | `betconfig` |
| 19:32:00 | Shoot close (`closeDateYeekee`). | `betconfig` |
| 19:32:01 | Page fetch: no result block. | `timing_observations.json` |
| 19:32:18 | Page fetch: result block present; sum 7,422,657; row 16 58,470; result 7,364,187; top 187 / bottom 64. | `timing_observations.json` |
| 19:33 | Full 151-row list reconstructed; Σ = 7,422,657; exact match. | `timing_observations.json` |
| 19:35 | Result page screenshot captured. | `screenshots/round_55_result.png` |
| 19:36 | Rules modal captured (`#modal-rule`) with the published formula and example. | `screenshots/rules_modal_round55.png`, `published_rules_th_en.md` |
| Throughout | Single-login invalidation occurred repeatedly; re-authentication performed as instructed. | error JSON, session notes |

## Screenshots

- `evidence/screenshots/yeekee_initial.png` — 88-card grid at 18:57, rounds 52+.
- `evidence/screenshots/round_55_result.png` — round 55 published result, sum, row 16, bonuses.
- `evidence/screenshots/rules_modal_round55.png` — official rules and worked example.

## Sanitized data artifacts

- `evidence/sanitized_observations/round_229_numbers.csv` — 173 rows, sequence + number only.
- `evidence/sanitized_observations/round_230_numbers.csv` — 164 rows, sequence + number only.
- `evidence/sanitized_observations/results_2026-11-07.json` — 53 published top/bottom results.
- `evidence/sanitized_observations/observed_schedule.json` — 88-round schedule, observed vs derived flags.
- `evidence/sanitized_observations/api_samples_sanitized.json` — endpoint inventory and schemas.
- `evidence/sanitized_observations/timing_observations.json` — close/publication measurements.
- `evidence/sanitized_observations/published_rules_th_en.md` — verbatim Thai rules plus translation.

No cookies, JWTs, CSRF values, passwords, or unmasked usernames are stored in any artifact.

## Reproduction

1. Start `agent-browser` with an isolated session and navigate to `https://thlotto.com/login`.
2. Log in with an authorized account (do not store credentials in files).
3. Navigate to `/member/lottery/yeekee`; read `.card-items` and `.card-result`.
4. Open a round page; read `betconfig` from the HTML attribute; read the submission table.
5. Fetch `GET /member/lottery/yeekee-list-number?id={id}&limit=19&offset=0` from the page context.
6. After publication, fetch `GET /member/lottery/yeekee/{id}?page=N` for all rows and run `verify_formula.py`.
7. For timing, record the HTTP `Date` header and poll the round page at a light interval around `close_date + 2 min`.

## Classification legend

- **OBSERVED** — directly supported by reproducible evidence.
- **INFERRED** — reasonable interpretation of observations.
- **HYPOTHESIS** — proposed explanation requiring testing.
- **UNKNOWN** — cannot be established from available evidence.

## Ethical constraints honored

- No authentication bypass, CAPTCHA bypass, rate-limit evasion, or vulnerability exploitation.
- No automated number submissions, bets, or wagering.
- No access to other members’ private data.
- No probing of undocumented services, `/api`, or `/pusher/auth`.
- Any potentially sensitive observation is described by type and location only; values are redacted.
