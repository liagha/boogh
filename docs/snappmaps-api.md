# SnappMaps API (from ride PWA config, Sept 2026)

The ride PWA outsources geo to dedicated hosts (verbatim from `window.configuration`):

```
VITE_API_ADDRESS:       https://api.snappmaps.ir/client-reverse/v1
VITE_API_BIFROST:       https://api.snappmaps.ir/client-route/v1
VITE_API_MAP:           https://api.snappmaps.ir/client-search/v1
VITE_API_FINDORA:       https://api.snappmaps.ir/recommendation/v1
VITE_API_MAP_ANALYTICS: https://api.snappmaps.ir/address-analytics/v1
VITE_API_SMAPP_SHOT:    https://smappshot.snappmaps.ir
```

## Probes (Sept 2026, unauthenticated)

- `GET https://api.snappmaps.ir/client-search/v1/search?query=...&lat=..&lng=..` → empty body
- `GET https://api.snappmaps.ir/client-reverse/v1/reverse?lat=35.7219&lng=51.3347` → empty body
- Both are live hosts (DNS+TLS ok) but need client key/headers the PWA injects
  (likely via `/api/*` proxy or signed header — check HAR, or grep split chunks
  for `client-search` request headers).

## CLI implication

- Do NOT build geo on SnappMaps first. SnappFood's `cities` + `marketing-area`
  (documented in `snappfood-api.md`) already work key-in-hand.
- Alternatively use the Neshan MCP (already connected in this env) for
  geocode/reverse/directions in Iran, and keep SnappMaps for phase 2 HAR capture.
