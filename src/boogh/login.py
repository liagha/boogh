"""boogh login is otp and token bootstrap."""
import base64
import json
import os
import sys
import urllib.error
import urllib.parse

from boogh import config


class Login:
    def __init__(self, vault, net, auth):
        self.vault = vault
        self.net = net
        self.auth = auth

    def food_send(self, args):
        if getattr(args, "via", "heimdall") == "legacy":
            return self.food_legacy_send(args)
        self.net.prime()
        return self.net.call("POST", f"{config.user}/v1/auth/otp/send",
                             body={"mobile_number": args.phone, "type": "Customer"},
                             headers={"Origin": "https://snappfood.ir",
                                      "Referer": "https://snappfood.ir/"})

    def food_legacy_send(self, args):
        self.net.prime()
        query = urllib.parse.urlencode(self.vault.params())
        return self.net.form({"cellphone": args.phone, "optionalLoginToken": "true"},
                             url=f"{config.base}/mobile/v4/user/loginMobileWithNoPass?{query}")

    def food_legacy_verify(self, args):
        self.net.prime()
        query = urllib.parse.urlencode(self.vault.params())
        res = self.net.form({"cellphone": args.phone, "code": args.code},
                            url=f"{config.base}/mobile/v2/user/loginMobileWithToken?{query}")
        data = self.vault.load()
        found = res.get("oauth2_token") or (res.get("data") or {}).get("oauth2_token")
        if found:
            data["food"] = found
            self.vault.save(data)
            print("oauth2 token stored.", file=sys.stderr)
        return res

    def food_verify(self, args):
        if getattr(args, "via", "heimdall") == "legacy":
            return self.food_legacy_verify(args)
        self.net.prime()
        res = self.net.call("POST", f"{config.user}/v1/auth/token",
                            body={"cellphone": args.phone, "otpCode": int(args.code),
                                  "grantType": "Otp"},
                            headers={"Origin": "https://snappfood.ir",
                                     "Referer": "https://snappfood.ir/"})
        data = self.vault.load()
        for key in ("accessToken", "access_token", "token", "heimdall_jwt_accessToken"):
            if isinstance(res, dict) and res.get(key):
                data["food"] = res[key]
                break
        else:
            data["food_last_response"] = res
        self.vault.save(data)
        print("token store updated (check tokens.json).", file=sys.stderr)
        return res

    def ride_send(self, args):
        if args.captcha_solution:
            return self.ride_solve(args)
        self.net.prime()
        head = self.auth.ride_headers()
        try:
            self.net.call("POST", f"{config.proxy}/v2/passenger/config",
                          body={"locale": "fa-IR", "device_type": 6, "version_code": 2,
                                "os_version": "Linux", "device_name": "Firefox", "referrer": 0},
                          headers=head)
        except urllib.error.HTTPError:
            pass
        phone = self.auth.phone(args.phone)
        try:
            return self.net.call("POST", f"{config.oauth}/v3/mutotp",
                                 body={"cellphone": phone,
                                       "attestation": {"method": "skip", "platform": "skip"},
                                       "extra_methods": []},
                                 headers=self.auth.ride_headers())
        except urllib.error.HTTPError as e:
            raw = e.read().decode()
            if e.code != 401:
                raise ValueError(f"otp send failed: http {e.code} {raw[:200]}")
        client = args.captcha_client or config.captcha_client
        cap = self.net.call("GET",
                            f"https://app.snapp.taxi/api/captcha/api/v1/generate/text/numeric/{client}",
                            headers=self.auth.ride_headers())
        img = cap.get("image", "")
        path = args.captcha_out or "/tmp/opencode/ride_captcha.jpg"
        if img.startswith("data:image"):
            with open(path, "wb") as f:
                f.write(base64.b64decode(img.split(",", 1)[1]))
        return {"captcha_client": client, "ref_id": cap.get("ref_id"), "image": path,
                "next": f"ride-send-otp --phone {args.phone} --captcha-client {client} "
                        f"--captcha-ref {cap.get('ref_id')} --captcha-solution <digits>"}

    def ride_solve(self, args):
        phone = self.auth.phone(args.phone)
        head = self.auth.ride_headers()
        try:
            self.net.call("POST", f"{config.oauth}/v3/mutotp",
                          body={"cellphone": phone,
                                "attestation": {"method": "skip", "platform": "skip"},
                                "extra_methods": []}, headers=head)
        except urllib.error.HTTPError:
            pass
        return self.net.call("POST", f"{config.oauth}/v3/mutotp",
                             body={"cellphone": phone,
                                   "attestation": {"method": "numeric", "platform": "captcha"},
                                   "extra_methods": [],
                                   "captcha": {"client_id": args.captcha_client,
                                               "solution": args.captcha_solution,
                                               "ref_id": args.captcha_ref, "type": "numeric"}},
                             headers=head)

    def ride_verify(self, args):
        phone = self.auth.phone(args.phone)
        res = self.net.call("POST", f"{config.oauth}/v3/mutotp/auth",
                            body={"attestation": {"method": "skip", "platform": "skip"},
                                  "grant_type": args.method,
                                  "client_id": config.ride_client,
                                  "client_secret": config.ride_secret,
                                  "cellphone": phone, "token": args.code,
                                  "referrer": "pwa", "device_id": self.vault.device()},
                            headers={"Referer": "https://app.snapp.taxi/verify-cellphone-otp",
                                     **config.ride_headers})
        if isinstance(res, dict) and res.get("access_token"):
            data = self.vault.load()
            data["ride"], data["ride_refresh"] = res["access_token"], res.get("refresh_token")
            self.vault.save(data)
            print("ride tokens stored + auto-refresh armed.", file=sys.stderr)
        if isinstance(res, dict):
            return {k: (v if k not in ("access_token", "refresh_token") else v[:12] + "...")
                    for k, v in res.items()}
        return res

    def ride_import(self, args):
        data = self.vault.load()
        if args.access:
            data["ride"] = args.access
        if args.refresh:
            data["ride_refresh"] = args.refresh
        if args.device:
            data["ride_device_id"] = args.device
        self.vault.save(data)
        return {"stored": {k: (v[:8] + "..." if isinstance(v, str) and len(v) > 11 else v)
                           for k, v in data.items() if k.startswith("ride")}}

    def ride_refresh(self, args):
        found = self.auth.ride_refresh(args.refresh)
        if not found:
            raise ValueError("refresh failed (bad/expired refresh token). Re-bootstrap.")
        return {"access_token": found[:12] + "..."}

    def food_refresh(self, args):
        found = self.auth.food_refresh()
        if not found:
            raise ValueError("refresh failed. Re-login.")
        return {"access_token": found[:12] + "..."}

    def ride_guided(self, args):
        import subprocess
        helper = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "..", "..", "..", "snapppp", "login-helper", "ride_login.py")
        legacy = "/home/alee/Projects/snapppp/login-helper/ride_login.py"
        path = legacy if os.path.exists(legacy) else helper
        venv = "/home/alee/Projects/snapppp/login-helper/.venv/bin/python"
        cmd = venv if os.path.exists(venv) else sys.executable
        done = subprocess.run([cmd, path, "--timeout", str(args.timeout)],
                              capture_output=True, text=True)
        if done.returncode != 0:
            raise ValueError(f"guided login failed/timed out: {(done.stdout or '') + (done.stderr or '')}"[:500])
        try:
            found = json.loads(done.stdout.strip().splitlines()[-1])
        except (ValueError, IndexError):
            raise ValueError("could not read tokens from helper.")
        data = self.vault.load()
        if found.get("accessToken"):
            data["ride"] = found["accessToken"]
        if found.get("refreshToken"):
            data["ride_refresh"] = found["refreshToken"]
        if found.get("deviceId"):
            data["ride_device_id"] = found["deviceId"]
        self.vault.save(data)
        return {"stored": True, "auto_refresh": bool(data.get("ride_refresh"))}
