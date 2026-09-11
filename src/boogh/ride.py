"""boogh ride is Snapp taxi reads and writes."""
import time

from boogh import config


class Ride:
    def __init__(self, vault, net, auth, geo):
        self.vault = vault
        self.net = net
        self.auth = auth
        self.geo = geo

    def show(self, path, args, tidy=None):
        data = self.auth.call("ride", "GET", f"{config.proxy}/{path}", args.token)
        if tidy and isinstance(data, dict):
            return tidy(data.get("data", data))
        return data

    def price(self, args):
        flat, flng = self.geo.coords(args, "from_lat", "from_lng", "origin")
        tlat, tlng = self.geo.coords(args, "to_lat", "to_lng", "dest")
        body = {"points": [{"lat": str(flat), "lng": str(flng)},
                           {"lat": str(tlat), "lng": str(tlng)}],
                "locale": "fa", "os": 6, "version": 0}
        if args.voucher:
            body["voucher_code"] = args.voucher
        data = self.auth.call("ride", "POST", f"{config.api}/v3/price", args.token, body=body)
        if not getattr(args, "compact", False) or not isinstance(data, dict):
            return data
        rows = data.get("data", {})
        return [{"service": s.get("info", {}).get("name"),
                 "final": (s.get("price") or {}).get("final"),
                 "eta_min": ((s.get("estimation") or {}).get("eta") or [None])[0]}
                for s in (rows.get("services") or [])]

    def request(self, args):
        flat, flng = self.geo.coords(args, "from_lat", "from_lng", "origin")
        tlat, tlng = self.geo.coords(args, "to_lat", "to_lng", "dest")
        return self.auth.guard(args, "ride", "POST", f"{config.proxy}/v2/passenger/ride",
                               {"origin_lat": flat, "origin_lng": flng,
                                "destination_lat": tlat, "destination_lng": tlng,
                                "service_type": args.service},
                               headers={"x-app-version-code": "0"},
                               note="REQUESTS A REAL RIDE - driver dispatched, fare charged!")

    def cancel(self, args):
        return self.auth.guard(args, "ride", "PATCH",
                               f"{config.proxy}/v2/passenger/ride/{args.ride_id}/cancel/{args.state}",
                               {"reason": args.reason} if args.reason else {},
                               note="cancels a live ride (may affect rating)")

    def reasons(self, args):
        return self.show(f"v2/passenger/ride/{args.ride_id}/cancellation-reasons", args)

    def clone(self, args):
        return self.auth.guard(args, "ride", "POST",
                               f"{config.proxy}/v1/passenger/ride/{args.ride_id}/clone",
                               {"cancellation_reason_id": args.reason_id,
                                "cancellation_description": ""},
                               note="re-requests a cancelled ride")

    def block(self, args):
        return self.auth.guard(args, "ride", "POST",
                               f"{config.proxy}/v1/passenger/ride/{args.ride_id}/block-driver",
                               {}, note="blocks driver from future matches")

    def flexi(self, args):
        return self.auth.guard(args, "ride", "POST", f"{config.api}/v3/flexi",
                               {"points": [{"lat": str(args.from_lat), "lng": str(args.from_lng)},
                                            {"lat": str(args.to_lat), "lng": str(args.to_lng)}],
                                "service_types": [args.service], "locale": "fa", "os": 6,
                                "version": 0},
                               note="flexi quote (preview)")

    def debt(self, args):
        return self.auth.guard(args, "ride", "POST",
                               f"{config.proxy}/api/v1/passenger/pay-debt",
                               {"wallet_type": args.wallet}, note="PAYS MONEY from wallet!")

    def voucher(self, args):
        return self.auth.guard(args, "ride", "PUT",
                               f"{config.proxy}/v2/passenger/finance/voucher",
                               {"voucher_code": args.code}, note="applies voucher")

    def profile_set(self, args):
        return self.auth.guard(args, "ride", "PUT", f"{config.proxy}/v2/passenger/profile",
                               {"fullname": args.name, "meta": {
                                   "passenger_gender": args.gender,
                                   "passenger_birthdate": args.birthdate,
                                   "passenger_address": args.address}},
                               note="edits profile")

    def options_set(self, args):
        return self.auth.guard(args, "ride", "PUT", f"{config.proxy}/v2/passenger/options",
                               {"disabilities": args.disabilities},
                               note="edits ride options")

    def options(self, args):
        return self.auth.guard(args, "ride", "POST", f"{config.proxy}/v1/ride-options",
                               {"service_id": args.service,
                                "points": [{"lat": str(args.from_lat), "lng": str(args.from_lng)},
                                           {"lat": str(args.to_lat), "lng": str(args.to_lng)}]},
                               note="ride-options quote (preview)")

    def carpool(self, args):
        return self.auth.guard(args, "ride", "POST",
                               f"{config.api}/v1/passenger/carpooling/convert-offer/{args.act}/{args.offer_id}",
                               {}, note=f"carpool offer {args.act}")

    def boarded(self, args):
        return self.auth.guard(args, "ride", "POST",
                               f"{config.api}/v2/passenger/{args.ride_id}/boarded",
                               {"boarded": True}, note="confirms you boarded")

    def headsup(self, args):
        return self.show(f"v3/passenger/ride/{args.ride_id}/cancellation-headsup", args)

    def profile(self, args):
        return self.show("v2/passenger/profile", args, lambda d: {
            "fullname": d.get("fullname"), "cellphone": d.get("cellphone"),
            "referral": d.get("referral_code"), "credit": d.get("credit"),
            "total_km": round((d.get("total_distance") or 0) / 1000, 1)})

    def history(self, args):
        def tidy(d):
            return [{"id": r.get("human_readable_id"), "title": r.get("title"),
                     "from": (r.get("origin") or {}).get("formatted_address"),
                     "to": (r.get("destination") or {}).get("formatted_address")}
                    for r in (d.get("rides") or [])[:(args.limit or 10)]]
        return self.show(f"v2/passenger/ride/history?page={args.page or 0}", args, tidy)

    def status(self, args):
        return self.show("v2/passenger/ride", args)

    def rating(self, args):
        return self.show("v1/passenger/rating", args)

    def debts(self, args):
        return self.show("api/v1/passenger/debts", args)

    def wallets(self, args):
        return self.show("api/v1/passengers/payments", args, lambda d: [
            {"title": w.get("wallet_title"), "type": w.get("wallet_type")}
            for w in (d.get("wallets") or [])])

    def balance(self, args):
        data = self.auth.call("ride", "POST", f"{config.proxy}/v2/passenger/balance",
                              args.token, body={})
        found = data.get("data", data) if isinstance(data, dict) else {}
        return {"balance": found.get("balance"), "max_topup": found.get("max_topup_amount")}

    def places(self, args):
        return [{"name": p.get("name"), "addr": (p.get("location") or {}).get("formatted_address"),
                 "lat": (p.get("location") or {}).get("lat"),
                 "lng": (p.get("location") or {}).get("lng")}
                for p in self.geo.saved(args, force=True)]

    def place_add(self, args):
        return self.auth.guard(args, "ride", "POST", f"{config.proxy}/v2/passenger/place",
                               {"name": args.name, "detailed_address": args.address or "",
                                "lat": args.lat, "lng": args.lng},
                               note="saves a favorite place")

    def snapshot(self, data):
        found = data.get("data", data) if isinstance(data, dict) else {}
        active = found.get("ride") or found.get("started_ride")
        if not active:
            pending = found.get("need_rate") or {}
            info = pending.get("ride_info") or {}
            driver = pending.get("driver") or {}
            return {"active": False,
                    "unrated_ride": info.get("ride_id"),
                    "unrated_driver": driver.get("driver_name")}
        driver = active.get("driver") or {}
        vehicle = active.get("vehicle") or driver.get("vehicle") or {}
        origin = active.get("origin") or {}
        dest = active.get("destination") or active.get("dest") or {}
        return {"active": True,
                "state": active.get("state") or active.get("status"),
                "ride_id": active.get("human_readable_id") or active.get("ride_id") or active.get("id"),
                "driver": driver.get("driver_name") or driver.get("name"),
                "vehicle": vehicle.get("vehicle_model") or vehicle.get("model"),
                "plate": vehicle.get("plate") or vehicle.get("number"),
                "eta_min": active.get("eta") or (active.get("estimation") or {}).get("eta"),
                "fare": (active.get("price") or {}).get("final") or active.get("final_price"),
                "from": origin.get("formatted_address"),
                "to": dest.get("formatted_address")}

    def track(self, args):
        wait = getattr(args, "follow", 0) or 0
        limit = getattr(args, "timeout", 600) or 600
        if not wait:
            data = self.auth.call("ride", "GET", f"{config.proxy}/v2/passenger/ride",
                                  args.token)
            return self.snapshot(data)
        end = time.time() + limit
        seen = None
        out = []
        while time.time() < end:
            data = self.auth.call("ride", "GET", f"{config.proxy}/v2/passenger/ride",
                                  args.token)
            snap = self.snapshot(data)
            if snap != seen:
                out.append(snap)
                seen = snap
            if not snap["active"]:
                return out
            time.sleep(wait)
        out.append({"active": None, "note": "track timed out, ride still active"})
        return out
