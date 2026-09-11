# SnappFood API (reverse-engineered, Sept 2026)

Source: `https://snappfood.ir/_next/static/chunks/pages/_app-*.js`
extracted via `(0,i.U)({url, method, baseURL})` triples + live curl probes.

## Base URLs

| Base | Use |
|---|---|
| `https://snappfood.ir` | legacy `/mobile/*`, group-order, product reviews |
| `https://apigw.snappfood.ir` | gateway: `menu-read-model/*`, `search/*`, `voucher/*`, `cashback/*` |
| `https://marketing-area.snappfood.ir` | geo resolve, needs `X-API-KEY` (public web key below) |
| `https://user.snappfood.ir/` | OTP + token |
| `https://api-titan.snappfood.ir` | seo, tapsell/yektanet tokens, address delete |
| `https://payment.snappfood.ir` | DirectDebit details |
| `https://adsfeedback.snappfood.ir` | `/v1/event/` POST |
| `https://api.mediaad.org` | post-back |

Public web key (found twice in `_app.js`, not a secret):
`X-API-KEY: 88sqcXFr5QHtvZKt6lJTySCxflFG5CPrs8XyfXUhQRSjyrrRI0TRB3595LxDvF8i`

## Auth — Heimdall OTP (shapes VERIFIED from LoginOtp.tsx + live 400s, Sept 2026)

```
POST https://user.snappfood.ir/v1/auth/otp/send
  headers: Accept-Language: fa, withCredentials
  body: {"mobile_number": "<phone>", "type": "Customer"}   # 5-digit SMS
  empty-body probe -> 400 {"errors":{"MobileNumber":["The MobileNumber field is required."]}}

POST https://user.snappfood.ir/v1/auth/token
  body: {"cellphone": "<phone>", "otpCode": <Number>, "grantType": "Otp"}
  # grantType enum (module 12092): Password="Password", Otp="Otp",
  #   HeimdallRefreshToken="RefreshToken", ...
  # empty-body probe -> {"success":false,"error":{"message":"Request model is not valid"}}
  # web stores: heimdall_jwt_accessToken / heimdall_jwt_refreshToken (+ExpiresAt keys)
  #
  # WIRE FORMAT (proven by decompiling wrapper U=module 18238 + clients=module 20890):
  #   sendOtp/verifyOtp pass !0 => Q2 = cleanInstance (BARE): NO base params,
  #   NO X-Is-Bonyan, NO token. Only baseURL + withCredentials + Accept-Language.
  #   Body {mobile_number,type} / {cellphone,otpCode,grantType} as JSON, NO query.
  # GATEWAY EVIDENCE (live probes, no real number harmed):
  #   phone=123 -> HTTP 503 {"success":false,"error":{"message":"Error sending SMS."}}
  #     => invalid input reaches the SMS gateway and fails THERE (API shape correct).
  #   phone=09000000000 -> {"data":null,"success":true} (accepted, gateway swallows unknown subscriber)
  #   => success:true means ACCEPTED BY GATEWAY. Missing SMS afterwards is
  #      throttle (repeated sends, resend cooldown) / carrier / account state, NOT format.
```

CLI: `snapppp.py food-send-otp --phone 0912...` then
`food-verify-otp --phone 0912... --code 12345` (persists to
`~/.config/snapppp/tokens.json`, mode 0600). Do NOT probe with fake numbers
beyond empty-body validation — a valid-format number triggers a real SMS.

```
POST https://user.snappfood.ir/v1/auth/otp/send      # sendOtp, headers Accept-Language: fa
POST https://user.snappfood.ir/v1/auth/token         # exchange OTP -> token
GET  https://user.snappfood.ir/v1/token/third-party  # loginSSO (skipGlobalErrorHandler)
POST https://snappfood.ir/mobile/v4/user/loginMobileWithNoPass
POST https://snappfood.ir/mobile/v2/user/loginMobileWithPass
POST https://snappfood.ir/mobile/v2/user/loginMobileWithToken
POST https://snappfood.ir/mobile/v2/user/load
POST https://snappfood.ir/mobile/v2/user/logout
POST https://snappfood.ir/mobile/v1/user/registerWithOptionalPass
POST https://snappfood.ir/mobile/v2/user/password/check
POST https://snappfood.ir/mobile/{v}/user/password/forget
POST https://snappfood.ir/oauth2/default/token
GET  https://snappfood.ir/oauth2/default/status
```

CLI implication: implement `snapppp food login --phone 09...` doing
otp/send -> prompt code -> auth/token -> persist token in `~/.config/snapppp/`.

## Geo / address (read)

```
GET https://snappfood.ir/mobile/v2/area/cities
  # VERIFIED live, no auth. Returns {status,data:{cities:[{id,code,title,latitude,longitude}]}}.
  # Tehran id=1 (35.691156,51.399248).

GET https://marketing-area.snappfood.ir/marketing/api/v1/marketing-area/get-by-location/{lat}/{lng}
  # VERIFIED live with X-API-KEY. 35.7219/51.3347 -> {"id":154,"cityId":1}

GET https://marketing-area.snappfood.ir/availability/api/v1/city/get-by-location/{lat}/{lng}
  # same key, withCredentials:false (inferred same shape).

GET https://snappfood.ir/map/address/reverse   (skipBaseParams)
GET https://snappfood.ir/map/address/place     (returns place_id,name,description,lat/long)
GET https://snappfood.ir/mobile/v4/user/user-addresses
POST https://snappfood.ir/mobile/v4/user/address/create
POST https://snappfood.ir/mobile/v4/user/address/edit
POST https://snappfood.ir/mobile/v2/user/address/delete
POST https://snappfood.ir/mobile/v1/user/address/delete
```

## Vendors / search / menu (core read surface)

Gateway base `https://apigw.snappfood.ir`:

```
{url:"search/api/v4/restaurant/vendors-list"}   # vendorsList(e)
  # VERIFIED Sept 2026: GET https://snappfood.ir/search/api/v4/restaurant/vendors-list
  #   REQUIRED query: lat + long (NOTE: `long`, not `lng` — base params are
  #   {lat, long, optionalClient, client, deviceType, appVersion, UDID, Bonyan}).
  #   WRONG base (apigw) or `lng` -> {"error":"lat long not valid"}.
  #   CORRECT: ?lat=35.7219&long=51.3347 -> {status,data:{count:931,finalResult:[...]}}.
  #   Optional: superType, page. Response types: TEXT/VENDOR/Carousel/MealForOne/...

GET /menu-read-model/vendor-details/${vendorCode}   # LIVE (bad id -> {"data":null,"message":"Bad Request"})
GET /menu-read-model/${vendorCode}?segments=...
GET menu-read-model/vendor-review/${vendorCode}
GET https://snappfood.ir/mobile/v3/restaurant/productReviews
GET https://snappfood.ir/mobile/v2/restaurant/details/state
POST https://snappfood.ir/mobile/v3/restaurant/favorites
POST https://snappfood.ir/mobile/{v}/restaurant/coupons/${vendorCode}
```

Frontend route helpers (deep-link building, from same bundle):
`/search?superType=`, `/search/vendor-list?item_name=&superType=&filters=&sort=`,
`/search/product-list?query=&extra-filter=&superType=`,
`/restaurant/menu/{vendorCode}?is_pickup=`, `/{vendorCode}/information?active_tab=`.

## Basket / order / payment (auth required, shapes from JS names only)

```
GET    https://snappfood.ir/mobile/v1/order/userPendingOrders
POST   https://snappfood.ir/mobile/v1/order/new
POST   https://snappfood.ir/mobile/v1/group-order/payment/new
GET    https://snappfood.ir/api/group-order/info?basketIdentifier=${id}
POST   https://snappfood.ir/mobile/v2/basket/
PUT    https://snappfood.ir/mobile/v2/basket/${id}
DELETE https://snappfood.ir/mobile/v2/basket/${id}
DELETE https://snappfood.ir/mobile/v2/basket/group-basket/${id}
POST   https://snappfood.ir/mobile/v2/product-variation/similar
GET    https://snappfood.ir/customer/order/v1/vendor/${id}/min-basket-rules
GET    https://apigw.snappfood.ir/decomposition/payment-service/order/paymentOptions
GET    https://apigw.snappfood.ir/mobile/v1/order/banks
POST   https://snappfood.ir/mobile/v1/ap/getPaymentResult
GET    https://apigw.snappfood.ir/mobile/v1/ap/check-contract-status
POST   https://snappfood.ir/landing/biker-location
POST   https://snappfood.ir/mobile/v1/order-review/submit-comment
```

Vouchers/cashback/membership (gateway):
```
GET /voucher/api/v1/users/me/vouchers/direct-debit
GET /voucher/api/v1/users/me/vouchers/checkout
GET /cashback/api/client/v1/vendorscredit/count
GET /cashback/api/client/v1/vendorscredit/${vendorCode}
POST /foodpro/voucher/validate
GET /membership/v1/active-subscription?plan_id=71
GET /foodpro/free-trial/users/me/campaigns?cityId=${id}&type=mini
...
```

## What to do next (ordered)

1. `cities` + `marketing-area` already give CLI `food geo` without auth — build first.
2. `vendor-details` with a real vendorCode from site HTML/Next data
   (`__NEXT_DATA__` on snappfood.ir) to confirm shape, then lock response schema.
3. vendors-list needs one HAR capture with Chrome to pin params — do not guess further.
4. OTP login last (live phone needed, rate-limited).
