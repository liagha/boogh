"""boogh geo is place lookup and point parsing."""
import re
import sys
import time

from boogh import config


class Geo:
    def __init__(self, vault, net, auth):
        self.vault = vault
        self.net = net
        self.auth = auth

    def resolve(self, text, lat=35.69, lon=51.39):
        res = self.net.get(f"{config.base}/map/address/place",
                           {"place": text, "lat": lat, "lon": lon})
        items = (res[0].get("data") if isinstance(res, list) and res else []) or []
        if not items:
            sys.exit(f"error: no place found for {text!r}")
        top = items[0]
        loc = top.get("location", {})
        return {"name": top.get("name"), "desc": top.get("description"),
                "lat": float(loc.get("latitude")), "lng": float(loc.get("longitude"))}

    def saved(self, args=None, force=False):
        data = self.vault.load()
        cache = data.get("ride_places_cache") or {}
        if not force and cache.get("at", 0) > time.time() - 86400 and cache.get("places"):
            return cache["places"]
        found = self.auth.token("ride", getattr(args, "token", None) if args else None)
        if not found:
            return []
        try:
            res = self.auth.call("ride", "GET",
                                 f"{config.proxy}/v2/passenger/place?frequents=1", found)
        except Exception:
            return cache.get("places", [])
        places = ((res.get("data") or {}) if isinstance(res, dict) else {}).get("places", [])
        data["ride_places_cache"] = {"at": time.time(), "places": places}
        self.vault.save(data)
        return places

    def point(self, spec, lat=None, lon=None):
        m = re.match(r"^\s*(-?\d+(?:\.\d+)?)\s*[,،]\s*(-?\d+(?:\.\d+)?)\s*$", spec or "")
        if m:
            return float(m.group(1)), float(m.group(2))
        for place in self.saved():
            if (place.get("name") or "").strip().lower() == (spec or "").strip().lower():
                loc = place.get("location") or {}
                print(f"shortcut {spec!r} -> {place.get('name')} ({loc.get('lat')},{loc.get('lng')})",
                      file=sys.stderr)
                return float(loc["lat"]), float(loc["lng"])
        found = self.resolve(spec, lat or 35.69, lon or 51.39)
        print(f"resolved {spec!r} -> {found['name']} ({found['lat']},{found['lng']})", file=sys.stderr)
        return found["lat"], found["lng"]

    def coords(self, args, flat="from_lat", flng="from_lng", text="origin"):
        label = getattr(args, text, None)
        flat_v, flng_v = getattr(args, flat, None), getattr(args, flng, None)
        if label:
            return self.point(label, flat_v, flng_v)
        if flat_v is not None and flng_v is not None:
            return float(flat_v), float(flng_v)
        sys.exit(f"error: give --{text} 'lat,lng' or text (or --{flat} + --{flng})")
