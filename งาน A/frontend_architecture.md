# Frontend Architecture — THLotto Yeekee

Scope: `https://thlotto.com/member/lottery/yeekee` and round pages, observed with an authorized account on 2026-11-07 (Asia/Bangkok). All statements below are classified OBSERVED / INFERRED / HYPOTHESIS / UNKNOWN.

## 1. Verified stack

| Layer | Evidence | Classification |
|---|---|---|
| Server-rendered HTML | Every round list and round detail is present in the initial HTML; no round-data XHR was observed. | OBSERVED |
| jQuery 3.5.1 | `assets/js/front/jquery-3.5.1.min.js` (89,476 bytes, SHA-256 in REA evidence). | OBSERVED |
| Bootstrap bundle | `assets/js/front/bootstrap.bundle.min.js` (84,152 bytes). | OBSERVED |
| Vue component bundle (2.x-style render functions) | `assets/js/app/manifest.js`, `vendor.js`, `main.js?v=7.5`; `main.js` contains Vue render-function output (`staticClass`, `domProps`), `Vue.use`, `v-validate`, axios; the exact Vue version string is not exposed. | OBSERVED for Vue usage; INFERRED for 2.x |
| Laravel-style asset pipeline | `assets/js/app/manifest.js` + `vendor.js` + `main.js`, `?v=` cache-busting, `XSRF-TOKEN` cookie. | INFERRED (strong) |
| Pusher JS 7.0 | `js.pusher.com/7.0/pusher.min.js`; inline subscription code. | OBSERVED |
| PNotify, Nanobar, Hotkeys, Magnific Popup | Delivered `<script>`/`<link>` tags. | OBSERVED |
| Cloudflare edge | `server: cloudflare`, `cf-ray` with BKK suffix, `cf-cache-status: DYNAMIC` on member HTML/JSON. | OBSERVED |
| Google frontend for some static assets | `server: ESF` on Google Fonts responses. App assets are served from thlotto.com. | OBSERVED |

No Next.js, Nuxt, React root, Angular, or Vue devtools global was present. `window.__NEXT_DATA__`, `__NUXT__`, `[data-reactroot]`, `window.ng` were all absent. Classification: OBSERVED.

## 2. Rendering and navigation

- The 88-round grid is rendered server-side as `.card-items` (open/closed pending) and `.card-result` (published). Each card carries `data-href="/member/lottery/yeekee/{periodId}"`.
- Navigation to a round is a normal document request (`/member/lottery/yeekee/229`, `/230`, `/231`, ...). No client-side router was observed.
- Round detail pages are paginated server-side: 50 submission rows per page (`?page=2`, ...).
- The result page is also server-rendered; the result block is part of the HTML, not fetched by JS.

Classification: OBSERVED.

## 3. Countdown implementation

The countdown is seeded from a server timestamp embedded in the HTML (`serDateTime = 1794052631488` on the first capture, roughly the render time). The page script then:

1. Reads `finalDate` (the round close time, from the server-provided `betconfig`).
2. Computes `offset = serverDateTime - Date.now()` and `now = offset + Date.now()`.
3. Recomputes the remaining time every second and increments the stored server time by 1000 ms.

Consequences:

- The displayed countdown is anchored to server time; a wrong client clock only affects the one-time offset measurement, not the absolute target.
- The countdown is not periodically re-synchronized with the server. Long-lived tabs accumulate local drift.
- When the **shoot-window** countdown (`close_date + 2 minutes`) goes negative, the code calls `window.location.reload()`. This is why a round page transitions from “ปิดรับการทายผลตัวเลข” to the published result without any polling.
- The published rules also state that displayed submission times use real server time.

Classification: OBSERVED for the code path and embedded timestamp; INFERRED for drift magnitude (not measured over hours).

## 4. Client state and storage

Observed browser storage on the Yeekee page after login:

- `localStorage`: `pusherTransportTLS` only (Pusher transport latency cache).
- `sessionStorage`: empty.
- Cookies (names only): `language`, `XSRF-TOKEN`, `core-session`, `core-session-value`.
- IndexedDB: none. CacheStorage: none.

Classification: OBSERVED (REA storage inventory + page script). Values redacted.

## 5. Real-time channel

The only Pusher subscription observed was:

- Cluster `ap1`, public key embedded in HTML (Pusher keys are public by design).
- Channel `notic.agentid.33`.
- Event `numbersets`.
- Handler calls `GET /member/number-recommend-notified?id=...` and displays a PNotify toast linking to `/member/number-recommend`.

No round, result, sum, or submission channel/event was observed. The WebSocket connection is therefore unrelated to round state.

Classification: OBSERVED for the code; INFERRED that it is an agent notification channel (name and handler agree).

## 6. Client-side calculation

- The number-shooting input is validated client-side with `required|numeric|digits:5` (VeeValidate), `maxlength=5`, `type=tel`, placeholder “กรอกเลข 5 หลัก”.
- The “สุ่มเลข” (random number) button generates 5 digits with `Math.random()` purely for UI convenience. It does not influence results.
- No client-side implementation of the result formula was found. The result is rendered by the server.
- `sumYeekee` is updated from the server response after a submission (or from the list endpoint), not computed locally from the visible list.

Classification: OBSERVED for the validation and random button; OBSERVED for absence of a client result function in the delivered bundles (searched for the formula terms and for `sum - 16th` logic).

## 7. Third-party and tracking

- Cloudflare Insights beacon (`static.cloudflareinsights.com/beacon.min.js`).
- Cloudflare RUM `POST /cdn-cgi/rum` (204), observed repeatedly.
- Google Fonts (Sarabun, Merienda).
- Pusher.

No advertising or analytics SDKs beyond Cloudflare were observed.

## 8. Data flow summary

```
Browser GET /member/lottery/yeekee
  -> server renders 88 cards + current round state
Browser GET /member/lottery/yeekee/{id}
  -> server renders betconfig JSON in an HTML attribute, countdown, submission UI
  -> JS fetch GET /member/lottery/yeekee-list-number?id={id}&limit=19&offset=0
  -> JS fetch GET /member/lottery/yeekee-chart?id={id}&limit=19&offset=0
  -> countdown runs locally; at close+2min window.location.reload()
Browser POST /member/lottery/yeekee {number, bet_category_id, yeekee_special}
  -> server validates, stores, returns {status, lists, sum}
```

The server is the sole authority for round state, submissions, sums, and results.

## 9. Version / build metadata

- Asset version query `?v=7.5` on `manifest.js`, `vendor.js`, `main.js`.
- `custom.css?v=1.5`.
- No `meta[name=generator]`, no framework build manifest, no version endpoint observed.
- `main.js.map` declares `webpack:///public/assets/js/app/main.js` and embeds only the bundled file as `sourcesContent` (1 source), not the original Vue SFCs.

Classification: OBSERVED. Backend framework version remains UNKNOWN.
