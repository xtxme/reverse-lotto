# Passive Client-Side Exposure Review

This is a passive review of resources the site normally delivered to an authorized browser. Nothing was exploited, fuzzed, or used to access data beyond the member’s own view. No credentials, session cookies, or tokens are reproduced in this report.

## Summary

No private backend source code, database credentials, administrative interface, or secret key was found in the delivered frontend. The notable observations are hardening gaps (cookie flags, missing security headers, a non-expiring bearer JWT, public source maps) and the intentional public disclosure of masked usernames plus submitted numbers.

| ID | Finding | Category | Classification | Confidence |
|---|---|---|---|---|
| EXP-01 | Production JavaScript source maps are publicly served | Information disclosure / hygiene | OBSERVED | High |
| EXP-02 | Page embeds a JWT bearer token with no `exp` claim | Token hygiene | OBSERVED claim structure; INFERRED risk | Medium |
| EXP-03 | Session cookies lack `Secure` and `SameSite` | Cookie hardening | OBSERVED | High |
| EXP-04 | No CSP, HSTS, Referrer-Policy, or Permissions-Policy | Security headers | OBSERVED | High |
| EXP-05 | Masked usernames + full submission numbers are public | Intentional transparency | OBSERVED | High |
| EXP-06 | `/api` base URL and `/pusher/auth` visible in bundle | Architecture disclosure | OBSERVED | High |
| EXP-07 | No client-side result algorithm or secret constants | Negative finding | OBSERVED | High |
| EXP-08 | Asset/build version exposed (`?v=7.5`) | Fingerprinting | OBSERVED | High |
| EXP-09 | Single active session enforced | Access control | OBSERVED | High |

## EXP-01 — Public source maps

- `https://thlotto.com/assets/js/app/main.js.map` — 1,086,250 bytes, HTTP 200, `sources: ["webpack:///public/assets/js/app/main.js"]`, `sourcesContent: true`.
- `vendor.js.map` — 100,777 bytes, same pattern.
- `manifest.js.map` — 1,714 bytes.
- The maps point to the compiled bundle itself, not to original Vue single-file components. They do not reveal server code, API secrets, or the result algorithm.
- Other libraries (PNotify, Bootstrap) serve their usual public maps.

Impact (assessed without exploitation): mild aid to code review/fingerprinting; no sensitive data. Recommendation: stop serving `.map` files in production, or restrict them, as routine hygiene.

## EXP-02 — Embedded JWT

The HTML contains:

```js
window.App = {
  csrfToken: "<redacted>",
  jwtToken: "<redacted>"
};
```

Decoded JWT metadata (no signature verification attempted):

- Header: `{"alg":"HS256","typ":"JWT"}`
- Payload: `{"payload":{"uid":<member id>},"iat":<render time>}`
- No `exp`, `nbf`, `aud`, `iss`, or `jti` claim.
- Signature length: 32 bytes.

The client uses it as:

```js
axios.defaults.baseURL = "/api";
axios.defaults.headers.common = {
  "X-CSRF-TOKEN": window.App.csrfToken,
  "X-Requested-With": "XMLHttpRequest",
  Authorization: "Bearer " + window.App.jwtToken
};
pusher = new Pusher(window.Config.PUSH_KEY, {
  cluster: "ap1",
  authEndpoint: "/pusher/auth",
  auth: { headers: { ..., Authorization: "Bearer " + window.App.jwtToken } }
});
```

Assessment:

- Minting a per-render JWT is normal. Embedding it in HTML is common for this architecture.
- The absence of `exp` means the token’s validity window is enforced only server-side (if at all). If it leaks (XSS, logs, referrer, browser extension), it may be replayable longer than intended.
- The payload contains only a numeric member id, not PII.
- No `/api` or `/pusher/auth` endpoint was probed; only the delivered code was read.

Recommendation: add short `exp`, `aud`, `iss`, and `jti`; rotate per session; ensure tokens are never logged; consider `HttpOnly` cookie transport instead of a JS-readable bearer token.

## EXP-03 — Cookie flags

Observed `Set-Cookie` attributes on `/login`:

| Cookie | HttpOnly | Secure | SameSite | Expiry |
|---|---|---|---|---|
| `core-session` | yes | **no** | **not set** | ~30 days |
| `core-session-value` | yes | **no** | **not set** | ~30 days |
| `XSRF-TOKEN` | no (by design, JS must read it) | **no** | **not set** | 2 hours |
| `language` | not observed | not observed | not observed | — |

Plain HTTP `http://thlotto.com/` returns `301` to HTTPS, which mitigates cleartext transmission, but the missing `Secure` and `SameSite` attributes are still hardening gaps (e.g., a single misconfigured HTTP endpoint or a browser that does not default to `Lax`). The 30-day session lifetime is long for a financial/gambling account.

Recommendation: `Secure; HttpOnly; SameSite=Lax` (or `Strict` where compatible), shorter idle/absolute timeout, `__Host-` prefix for the session cookie.

## EXP-04 — Security headers

Not present on observed application responses:

- `Content-Security-Policy`
- `Strict-Transport-Security`
- `Referrer-Policy`
- `Permissions-Policy`

Present:

- `X-Frame-Options: SAMEORIGIN`
- `X-Content-Type-Options: nosniff`
- `X-XSS-Protection: 1; mode=block`
- `X-Download-Options: noopen`

Assessment: clickjacking and MIME sniffing are addressed; XSS mitigation and transport enforcement are weaker than current best practice. A CSP would be particularly relevant given inline scripts and a JS-readable CSRF token.

Recommendation: add HSTS (`max-age=31536000; includeSubDomains`), a nonce-based CSP (the app uses inline scripts, so `unsafe-inline` would be required initially), `Referrer-Policy: strict-origin-when-cross-origin`, and a minimal Permissions-Policy.

## EXP-05 — Public submission data

The round page lists every submission with:

- a masked username (`Ab***cd`),
- the full 5-digit number,
- the row number,
- a timestamp.

The rules explicitly promise verifiability (“สามารถตรวจสอบได้”), so this is intentional transparency, not a leak. Risks:

- The pool can be scraped continuously, enabling analysis of submission behavior and possibly automated strategies.
- Masked usernames still reveal partial identifiers and can be correlated across rounds.
- Same-second bursts and repeated numbers suggest automated shooting; public visibility may amplify copy-trading.

No bet amounts, balances, emails, or real names are exposed.

Recommendation: keep transparency, but add per-account/IP rate limits on the list endpoint, consider coarser timestamp granularity, and monitor scraping.

## EXP-06 — Architecture disclosure

The bundle reveals:

- `axios.defaults.baseURL = "/api"`.
- `POST /member/lottery/yeekee` and the GET list/chart endpoints.
- `/pusher/auth` for private-channel authorization.
- Laravel-Mix-style bundles and `XSRF-TOKEN`.

These are normal client needs, not secrets. They do, however, give an attacker a precise map of the member API surface. No undocumented endpoint was probed.

## EXP-07 — No result algorithm on the client

Searches of `main.js`, `vendor.js`, `custom.js`, and the served source maps found:

- no subtraction of a 16th number,
- no modulo-100000 logic,
- no result-generation function,
- no hidden constants related to the draw.

The only “random” code is the UI convenience button (`Math.random()` for generating a 5-digit candidate). It does not affect the result.

Classification: OBSERVED (absence of evidence in delivered code). This does not prove the server algorithm; it only shows the result is not computed in the browser.

## EXP-08 — Build/version disclosure

- `?v=7.5` on `manifest.js`, `vendor.js`, `main.js`.
- `custom.css?v=1.5`.
- No server version banner, no `X-Powered-By`, no framework debug page.
- Cloudflare and Google frontend indicators are visible in headers.

Impact: low; useful for cache busting and minor fingerprinting.

## EXP-09 — Single-session enforcement

During the research, the site repeatedly returned:

```json
{"error":"Your session is invalid (prevent multiple login)"}
```

after another login to the same account. This is an intentional single-active-session control. It is a security-positive behavior for account sharing, though it complicated long observations.

## Negative findings (important)

- No database credentials, connection strings, or SQL.
- No private API keys or HMAC secrets.
- No administrative routes or debug consoles.
- No server source code or stack traces beyond generic framework error pages.
- No private member data (email, phone, balance, bet amounts) in the reviewed responses.
- No evidence that unpublished results are retrievable before the shooting window closes.

## Responsible-disclosure note

If the operator wants to act on these findings, the highest-value items are EXP-02 (JWT `exp`), EXP-03 (cookie flags), and EXP-04 (CSP/HSTS). None of them grants prediction capability; they are conventional web-security hardening items.
