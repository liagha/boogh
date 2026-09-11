"""boogh auth is token refresh and guarded calls."""
import base64
import json
import sys
import urllib.error
import urllib.parse

from boogh import config


class Auth:
    def __init__(self, vault, net):
        self.vault = vault
        self.net = net

    def token(self, kind, explicit):
        if explicit:
            return explicit
        return self.vault.load().get(kind)

    def ride_refresh(self, explicit=None):
        data = self.vault.load()
        found = explicit or data.get("ride_refresh")
        if not found:
            return None
        body = {"grant_type": "refresh_token", "client_id": config.ride_client,
                "client_secret": config.ride_secret, "device_id": self.vault.device(),
                "refresh_token": found}
        try:
            self.net.prime()
            res = self.net.call("POST", f"{config.oauth}/v2/auth", body=body,
                                headers={**config.ride_headers, "Referer": "https://app.snapp.taxi/"})
        except urllib.error.HTTPError:
            return None
        access, fresh = res.get("access_token"), res.get("refresh_token")
        if access:
            data["ride"], data["ride_refresh"] = access, fresh or found
            self.vault.save(data)
            return access
        return None

    def food_refresh(self):
        data = self.vault.load()
        found = data.get("food_refresh")
        if not found:
            return None
        try:
            res = self.net.call("POST", f"{config.user}/v1/auth/token",
                                body={"grantType": "RefreshToken", "refreshToken": found},
                                headers={"Origin": "https://snappfood.ir",
                                         "Referer": "https://snappfood.ir/"})
        except urllib.error.HTTPError:
            return None
        for key in ("accessToken", "access_token", "token", "heimdall_jwt_accessToken"):
            if isinstance(res, dict) and res.get(key):
                data["food"] = res[key]
                self.vault.save(data)
                return res[key]
        return None

    def auto(self, kind, explicit):
        found = self.token(kind, explicit)
        if found:
            return found
        found = self.ride_refresh() if kind == "ride" else self.food_refresh()
        if not found:
            raise ValueError(f"no {kind} token and refresh failed. Login once (see --help).")
        return found

    def strict(self, kind, explicit):
        found = self.token(kind, explicit)
        if not found:
            raise ValueError(f"no {kind} token. Run login command or pass --token (see --help).")
        return found

    def ride_headers(self, referer="https://app.snapp.taxi/login"):
        self.net.prime()
        raw = base64.urlsafe_b64encode(json.dumps(
            {"custom_id": self.vault.device(), "fingerprint_version": "v1"}).encode()
        ).decode().rstrip("=")
        return {"Referer": referer, **config.ride_headers,
                "X-Raw-Fingerprint": raw,
                "Cookie": f"B106E2F6056FE017={self.vault.fingerprint()}"}

    def call(self, kind, method, url, explicit, **kw):
        if kind == "ride":
            self.net.prime()
            kw["headers"] = {"Referer": "https://app.snapp.taxi/", **config.ride_headers,
                             **kw.get("headers", {})}
        found = self.auto(kind, explicit)
        try:
            return self.net.call(method, url, token=found, **kw)
        except urllib.error.HTTPError as e:
            if e.code != 401 or explicit:
                raise
            fresh = self.ride_refresh() if kind == "ride" else self.food_refresh()
            if not fresh:
                raise
            return self.net.call(method, url, token=fresh, **kw)

    def guard(self, args, kind, method, url, body=None, headers=None, note=""):
        if not getattr(args, "confirm", False):
            return {"dry_run": True, "method": method, "url": url,
                    "body": body, "note": note or "re-run with --confirm to execute"}
        if kind == "ride":
            return self.call(kind, method, url, args.token, body=body, headers=headers)
        return self.net.call(method, url, body=body, headers=headers,
                             token=self.strict(kind, args.token))

    def phone(self, text):
        clean = text.strip().replace(" ", "")
        if clean.startswith("+98"):
            return clean
        if clean.startswith("0098"):
            return "+98" + clean[4:]
        if clean.startswith("98") and len(clean) == 12:
            return "+" + clean
        if clean.startswith("0") and len(clean) == 11:
            return "+98" + clean[1:]
        raise ValueError("phone must look like 0912xxxxxxx")
