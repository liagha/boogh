# Snapp ride API (reverse-engineered, Sept 2026)

Sources:
- `https://app.snapp.taxi/` inline `window.configuration` + `window.rawConfiguration`
- `https://app.snapp.taxi/assets/index-*.js` (~1.3 MB, saved as `/tmp/opencode/taxi_main.js`)
- Legacy: `https://raw.githubusercontent.com/kharazi/snapp-cli/master/taxi/snapp.py`

## PWA config (verbatim keys, values are paths or hosts)

```
VITE_API: /api                                  # main proxy root
VITE_API_BASE: /api/api-base
VITE_API_BLACKGATE: /api/api-blackgate
VITE_API_GABRIEL: /api/api-gabriel
VITE_API_ACKERMAN: /api/api-ackerman
VITE_API_EVENTS: /api/api-events
VITE_API_HELIOGRAPH: /api/api-heliograph/call
VITE_API_LOYALTY: /api/api-loyalty
VITE_API_OAUTH: /api/api-passenger-oauth
VITE_API_USER_AUTH: /api/userauth-ap/passengers/api
VITE_API_GUARDIAN: /api/guardian
VITE_API_BARADUR: /api/baradur
VITE_API_ANALYTICS: /api/analytics/events
VITE_SNAPP_PRO_API_BASE: /api/subscription/pro
VITE_SUPER_APP_API_BASE: /api/superapp
VITE_API_SSO: https://oauth2.snapp.taxi
VITE_API_STATUS: https://status.snapp.site
VITE_API_LOCATIONS / VITE_API_MURCHE: https://locations.snapp.site
VITE_DRIVER_SIGN_UP: https://digitalsignup.snapp.ir
VITE_SNAPP_CLUB_URL: https://snapp-club.snapp.ir
VITE_SNAPP_PRO_URL: https://pro.snapp.taxi
VITE_VOUCHER_CENTER_URL: https://voucher-center.snapp.ir
```

Tokens live in `localStorage accessToken/refreshToken`, injected via
`window.updatePWATokens(params)` / `getParams()` bridge from native wrapper.
CLI must persist its own passenger JWT instead.

## Ride endpoints found in main bundle (`api.get/post`, 15 total)

```
POST v3/price                                   # price estimate (current flow)
POST v3/flexi                                   # flexi/street-hail(?) flow
POST v1/signal
GET  v1/ride/cards?ride-hri=${hri}
GET  v1/passenger/ride/${id}/extra-info
GET  v1/passenger/ride/${id}/target-cellphone
GET  v1/passenger/campaigns/${id}
GET  v2/passenger/ride/change-origin/validate/${id}
PATCH v2/passenger/ride/change-origin/update/${id}
POST v2/passenger/${id}/boarded
POST v1/passenger/carpooling/convert-offer/accept/${id}
POST v1/passenger/carpooling/convert-offer/reject/${id}
POST v1/passenger/carpooling/convert-offer/dismiss/${id}${q}
GET  v1/passenger/carpooling/convert-offer
```

Keyword hits also show (price chunk, split bundle):
```
$.api.post(`v3/price`, ...)
eL.base.post(`v2/passenger/ride/${id}/price/service`, {extra_destination_lat, extra_destination_lng...})
`v2/passenger/ride/${id}/change-destination/price/${...}` with {destination_lat, destination_lng}
```

Base path for the above is `VITE_API_BASE` (`/api/api-base` proxied) — i.e.
`https://app.snapp.taxi/api/api-base/v3/price` from browser. Direct host
behind proxy is not exposed in JS; needs HAR capture or proxy-header inspection.

## Legacy web-api (kharazi/snapp-cli, 2017 — shapes only, expect drift)

```python
POST https://web-api.snapp.ir/api/v1/auth/login
  body: {"username": ..., "password": ...} -> {"token": ...}
POST https://web-api.snapp.ir/api/v1/ride/price   (Authorization: <token>)
  body: {origin_lat, origin_lng, destination_lat, destination_lng, round_trip, waiting}
  -> {"prices": [{"service": {"name": ...}, "final": ...}]}
```

Probed Sept 2026: `POST /api/v1/ride/price` without session fails (curl exit, no JSON)
— consistent with auth-walled + possibly rotated. Keep only as fallback note;
current PWA uses `v3/price` + OAuth2 (`https://oauth2.snapp.taxi`), not this.

## Ride price (VERIFIED live, Sept 2026)

```
POST https://app.snapp.taxi/api/v3/price   # $.api client (VITE_API=/api), NOT /api/api-base!
```

- `$.api` calls (v3/price, v1/*) → `{VITE_API}` = `https://app.snapp.taxi/api`
- `$.base` calls (v2/passenger/*) → `{VITE_API_BASE}` = `https://app.snapp.taxi/api/api-base`
- Mixing them up: 404 HTML (Laravel) on wrong base; 403 nginx without client headers.
- REQUIRED on every call (from `e9` factory + `Y7`): `App-Version: pwa`,
  `x-app-version: v18.44.1`, `x-app-name: passenger-pwa`, `Content-Type: json`,
  plus `Referer: https://app.snapp.taxi/` and primed cookies (sendCredentials).
- Live result: `status:200`, categories ماشین/موتور/پیک, eco service
  `price.final=2130000` ریال, ETA 19 min. CLI: `ride-price`.

## More data (VERIFIED live, Sept 2026 — 61 endpoints enumerated in bundle)

| CLI | Endpoint | Notes |
|---|---|---|
| `ride-profile` | `GET base/v2/passenger/profile` | name, phone, referral, credit, lifetime km |
| `ride-history` | `GET base/v2/passenger/ride/history?page=` | rides w/ addresses, human IDs |
| `ride-status` | `GET base/v2/passenger/ride` | current/last ride + pending driver rating |
| `ride-rating` | `GET base/v1/passenger/rating` | badges (وقت‌شناس) |
| `ride-debts` | `GET base/api/v1/passenger/debts` | total_debt + list |
| `ride-wallets` | `GET base/api/v1/passengers/payments` | wallet list |
| `ride-balance` | `POST base/v2/passenger/balance {}` | balance, max_topup |
| `ride-reasons` | `GET base/v2/passenger/ride/{id}/cancellation-reasons` | needs ride id |

Base rule: `$.api` calls → `/api/...`, `$.base` calls → `/api/api-base/...`
(incl. `api/...`-prefixed paths which live under api-base). `active-rides` 404s
when idle; carpooling 2104 = no offer (normal empty states, not errors).

## Write endpoints (ALL implemented, ALL dry-run by default — need --confirm)

Bodies recovered verbatim from bundle builders. Verified: shapes vs bundle +
dry-run output; safe companions fired live (headsup 200). Nothing below was
executed (no money moved, no rides touched).

| CLI | Endpoint | Body |
|---|---|---|
| `ride-request` | `POST base/v2/passenger/ride` | origin/destination lat/lng, service_type |
| `ride-cancel --reason` | `PATCH base/v2/passenger/ride/{id}/cancel/{state}` | {reason} (headsup: fee warning read live) |
| `ride-clone` | `POST base/v1/passenger/ride/{id}/clone` | {cancellation_reason_id, description:""} |
| `ride-block-driver` | `POST base/v1/passenger/ride/{id}/block-driver` | {} |
| `ride-flexi` | `POST api/v3/flexi` | points[], service_types[], locale/os/version |
| `ride-pay-debt` | `POST base/api/v1/passenger/pay-debt` | {wallet_type} |
| `ride-voucher` | `PUT base/v2/passenger/finance/voucher` | {voucher_code} |
| `ride-profile-set` | `PUT base/v2/passenger/profile` | {fullname, meta:{gender,birthdate,address}} |
| `ride-options-set` | `PUT base/v2/passenger/options` | {disabilities} |
| `ride-ride-options` | `POST base/v1/ride-options` | {service_id, points[]} |
| `ride-carpool accept/reject/dismiss` | `POST api/v1/passenger/carpooling/convert-offer/...` | {} |
| `ride-boarded` | `POST api/v2/passenger/{id}/boarded` | {boarded:true} |
| `food-basket-create/update/delete` | SnappFood basket APIs | passthrough body |
| `food-order-new` | `POST snappfood.ir/mobile/v1/order/new` | passthrough + Payment-Provider hdr |
| `food-review-submit` | order-review/submit-comment | {order_id, comment, rate} |

## Token refresh (RECOVERED from bundle, Sept 2026 — needs one live refresh token to activate)

```js
// q7 / Wce in index-*.js:
POST {VITE_API_OAUTH}/v2/auth   // = https://app.snapp.taxi/api/api-passenger-oauth/v2/auth
body: {grant_type: "refresh_token",
       client_id: "ios_sadjfhasd9871231hfso234",
       client_secret: "23497shjlf982734-=1031nln",
       device_id: <persisted localStorage deviceId>,
       refresh_token: <refresh>}
headers: {"App-Version": "pwa", "x-app-version": "v18.44.1",
          "x-app-name": "passenger-pwa", "Content-Type": "application/json"}
-> {access_token, refresh_token}  // persist both (H7)
```

CLI: `ride-token-import --access .. --refresh .. [--device ..]` once, then every
ride command auto-uses stored access token and auto-refreshes on 401
(`_call_authed`). Fully non-interactive after bootstrap.

## Auth (current, from config names only — not yet traced)

- `VITE_API_OAUTH` (`/api/api-passenger-oauth`), `VITE_API_USER_AUTH`
  (`/api/userauth-ap/passengers/api`), `VITE_API_SSO` (`https://oauth2.snapp.taxi`),
  `VITE_API_WEBAUTHN` (`/api`), plus passkey strings (`passkey_login`, `passkey_login_match`)
  in bundle. OTP/passkey flow needs HAR capture; do not implement blind.
- `snapp://open/main` fallback in `getParams()` confirms native-wrapper SSO.

## What to do next (ordered)

1. HAR-capture `v3/price` request/response (one Chrome session) — highest value.
2. Trace OAuth2 OTP endpoints under `/api/api-passenger-oauth` same session.
3. Only then implement `snapppp ride price/request/status/cancel`.
