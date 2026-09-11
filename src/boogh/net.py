"""boogh net is http transport."""
import http.cookiejar
import json
import urllib.error
import urllib.parse
import urllib.request

from boogh import config


class Net:
    def __init__(self, vault=None):
        jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        self.primed = False

    def prime(self):
        if self.primed:
            return
        for url in (config.base + "/", "https://app.snapp.taxi/"):
            try:
                self.opener.open(urllib.request.Request(url, headers=dict(config.agent)), timeout=15).read()
            except Exception:
                pass
        self.primed = True

    def call(self, method, url, params=None, body=None, headers=None, token=None):
        if params:
            url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
        head = dict(config.agent)
        if headers:
            head.update(headers)
        if token:
            head["Authorization"] = f"Bearer {token}"
        data = json.dumps(body).encode() if body is not None else None
        if data and "Content-Type" not in head:
            head["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, headers=head, method=method)
        with self.opener.open(req, timeout=25) as r:
            raw = r.read().decode()
            return json.loads(raw) if raw else {}

    def get(self, url, params=None, headers=None, token=None):
        return self.call("GET", url, params=params, headers=headers, token=token)

    def post(self, url, body, token=None, headers=None):
        return self.call("POST", url, body=body, headers=headers, token=token)

    def form(self, body, url, token=None):
        head = dict(config.agent, **{"Content-Type": "application/x-www-form-urlencoded",
                                     "X-Is-Bonyan": "true"})
        if token:
            head["Authorization"] = f"Bearer {token}"
        data = urllib.parse.urlencode(body).encode()
        req = urllib.request.Request(url, data=data, headers=head, method="POST")
        with self.opener.open(req, timeout=25) as r:
            raw = r.read().decode()
            return json.loads(raw) if raw else {}

    def emit(self, obj):
        print(json.dumps(obj, ensure_ascii=False, indent=2))
