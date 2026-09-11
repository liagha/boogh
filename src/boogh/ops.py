"""boogh ops is the single op registry driving cli and mcp."""
import argparse
import types

from boogh.auth import Auth
from boogh.food import Food
from boogh.geo import Geo
from boogh.login import Login
from boogh.net import Net
from boogh.ride import Ride
from boogh.vault import Vault


def hub():
    vault = Vault()
    net = Net(vault)
    auth = Auth(vault, net)
    geo = Geo(vault, net, auth)
    return {"food": Food(vault, net, auth), "ride": Ride(vault, net, auth, geo),
            "login": Login(vault, net, auth), "geo": geo}


WHERE = [{"name": "lat", "kind": "str"}, {"name": "long", "kind": "str"}]
TOKEN = [{"name": "token", "kind": "str"}]
CONFIRM = [{"name": "confirm", "kind": "flag"}]
BODY = [{"name": "body-json", "kind": "str"}, {"name": "body-file", "kind": "str"}]
TRIP = [{"name": "from-lat", "kind": "float"}, {"name": "from-lng", "kind": "float"},
        {"name": "to-lat", "kind": "float"}, {"name": "to-lng", "kind": "float"},
        {"name": "origin", "kind": "str"}, {"name": "dest", "kind": "str"}]
VENDOR = [{"name": "code", "kind": "pos"}]
RIDE_ID = [{"name": "ride_id", "kind": "pos"}]
FROM_TO = [{"name": "from-lat", "kind": "float", "required": True},
           {"name": "from-lng", "kind": "float", "required": True},
           {"name": "to-lat", "kind": "float", "required": True},
           {"name": "to-lng", "kind": "float", "required": True}]

OPS = [
    (("geo",), "geo", "lookup", "Resolve place text to coords",
     [{"name": "query", "kind": "pos"}]),

    (("food", "cities"), "food", "cities", "List covered cities", []),
    (("food", "area"), "food", "area", "Marketing area for point", WHERE),
    (("food", "vendors"), "food", "vendors", "Nearby restaurants",
     WHERE + [{"name": "supertype", "kind": "str"}, {"name": "page", "kind": "str"},
               {"name": "compact", "kind": "noflag"}]),
    (("food", "vendor"), "food", "vendor", "Vendor details", VENDOR + WHERE),
    (("food", "menu"), "food", "menu", "Vendor menu", VENDOR + WHERE),
    (("food", "reviews"), "food", "reviews", "Vendor reviews", VENDOR + WHERE),
    (("food", "place"), "food", "place", "Address search",
     [{"name": "place", "kind": "str", "required": True}] + WHERE),
    (("food", "reverse"), "food", "reverse", "Reverse geocode", WHERE),
    (("food", "profile"), "food", "profile", "Food profile (needs login)", TOKEN),
    (("food", "pending"), "food", "pending", "Pending food orders (needs login)", TOKEN),
    (("food", "detail"), "food", "detail", "Order detail (needs login)", TOKEN),
    (("food", "rules"), "food", "rules", "Basket rules for vendor (needs login)",
     VENDOR + TOKEN),
    (("food", "basket", "create"), "food", "basket_create", "Create basket (dry-run)",
     BODY + TOKEN + CONFIRM),
    (("food", "basket", "update"), "food", "basket_update", "Update basket (dry-run)",
     [{"name": "basket_id", "kind": "pos"}] + BODY + TOKEN + CONFIRM),
    (("food", "basket", "delete"), "food", "basket_delete", "Delete basket (dry-run)",
     [{"name": "basket_id", "kind": "pos"}] + TOKEN + CONFIRM),
    (("food", "order", "new"), "food", "order_new", "PLACE ORDER (dry-run)",
     BODY + [{"name": "provider", "kind": "str"}] + TOKEN + CONFIRM),
    (("food", "review", "submit"), "food", "review_submit", "Post order review (dry-run)",
     [{"name": "order-id", "kind": "str", "required": True},
      {"name": "comment", "kind": "str", "default": ""},
      {"name": "rate", "kind": "float"}] + TOKEN + CONFIRM),
    (("food", "login", "send"), "login", "food_send", "Send food OTP",
     [{"name": "phone", "kind": "str", "required": True},
      {"name": "via", "kind": "str", "default": "heimdall"}]),
    (("food", "login", "verify"), "login", "food_verify", "Verify food OTP",
     [{"name": "phone", "kind": "str", "required": True},
      {"name": "code", "kind": "str", "required": True},
      {"name": "via", "kind": "str", "default": "heimdall"}]),
    (("food", "login", "refresh"), "login", "food_refresh", "Refresh food token", []),

    (("ride", "price"), "ride", "price", "Fare quote between two points",
     TRIP + [{"name": "compact", "kind": "noflag"},
             {"name": "voucher", "kind": "str"}] + TOKEN),
    (("ride", "request"), "ride", "request", "REQUEST A REAL RIDE (dry-run)",
     TRIP + [{"name": "service", "kind": "int", "default": 1}] + TOKEN + CONFIRM),
    (("ride", "cancel"), "ride", "cancel", "Cancel a live ride (dry-run)",
     RIDE_ID + [{"name": "state", "kind": "str", "default": "passenger"},
                {"name": "reason", "kind": "str"}] + TOKEN + CONFIRM),
    (("ride", "reasons"), "ride", "reasons", "Cancellation reasons", RIDE_ID + TOKEN),
    (("ride", "status"), "ride", "status", "Raw active-ride status", TOKEN),
    (("ride", "rating"), "ride", "rating", "Rating state", TOKEN),
    (("ride", "debts"), "ride", "debts", "Outstanding debts", TOKEN),
    (("ride", "wallets"), "ride", "wallets", "Payment wallets", TOKEN),
    (("ride", "balance"), "ride", "balance", "Wallet balance", TOKEN),
    (("ride", "track"), "ride", "track", "Active ride snapshot",
     [{"name": "follow", "kind": "int", "default": 0},
      {"name": "timeout", "kind": "int", "default": 600}] + TOKEN),
    (("ride", "history"), "ride", "history", "Past rides",
     [{"name": "page", "kind": "int"}, {"name": "limit", "kind": "int", "default": 10}]
     + TOKEN),
    (("ride", "headsup"), "ride", "headsup", "Cancellation heads-up", RIDE_ID + TOKEN),
    (("ride", "profile"), "ride", "profile", "Passenger profile", TOKEN, True),
    (("ride", "profile", "show"), "ride", "profile", "Show profile", TOKEN),
    (("ride", "profile", "set"), "ride", "profile_set", "Edit profile (dry-run)",
     [{"name": "name", "kind": "str", "required": True},
      {"name": "gender", "kind": "str"}, {"name": "birthdate", "kind": "str"},
      {"name": "address", "kind": "str"}] + TOKEN + CONFIRM),
    (("ride", "place"), "ride", "places", "Saved places", TOKEN, True),
    (("ride", "place", "list"), "ride", "places", "List saved places", TOKEN),
    (("ride", "place", "add"), "ride", "place_add", "Save a place (dry-run)",
     [{"name": "name", "kind": "str", "required": True},
      {"name": "address", "kind": "str", "default": ""},
      {"name": "lat", "kind": "float", "required": True},
      {"name": "lng", "kind": "float", "required": True}] + TOKEN + CONFIRM),
    (("ride", "login", "send"), "login", "ride_send", "Send ride OTP",
     [{"name": "phone", "kind": "str", "required": True},
      {"name": "captcha-client", "kind": "str"}, {"name": "captcha-ref", "kind": "str"},
      {"name": "captcha-solution", "kind": "str"},
      {"name": "captcha-out", "kind": "str",
       "default": "/tmp/opencode/ride_captcha.jpg"}]),
    (("ride", "login", "verify"), "login", "ride_verify", "Verify ride OTP",
     [{"name": "phone", "kind": "str", "required": True},
      {"name": "code", "kind": "str", "required": True},
      {"name": "method", "kind": "str", "default": "voice"}]),
    (("ride", "login", "import"), "login", "ride_import", "Import tokens from browser",
     [{"name": "access", "kind": "str"}, {"name": "refresh", "kind": "str"},
      {"name": "device", "kind": "str"}]),
    (("ride", "login", "refresh"), "login", "ride_refresh", "Refresh ride token",
     [{"name": "refresh", "kind": "str"}]),
    (("ride", "login", "guided"), "login", "ride_guided", "Browser-guided login",
     [{"name": "timeout", "kind": "int", "default": 300}]),
    (("ride", "voucher", "apply"), "ride", "voucher", "Apply voucher (dry-run)",
     [{"name": "code", "kind": "str", "required": True}] + TOKEN + CONFIRM),
    (("ride", "debt", "pay"), "ride", "debt", "PAY DEBT (dry-run)",
     [{"name": "wallet", "kind": "int", "default": 0}] + TOKEN + CONFIRM),
    (("ride", "options", "quote"), "ride", "options", "Ride-options quote (dry-run)",
     FROM_TO + [{"name": "service", "kind": "int", "default": 1}] + TOKEN + CONFIRM),
    (("ride", "options", "set"), "ride", "options_set", "Edit ride options (dry-run)",
     [{"name": "disabilities", "kind": "str", "default": ""}] + TOKEN + CONFIRM),
    (("ride", "flexi"), "ride", "flexi", "Flexi quote (dry-run)",
     FROM_TO + [{"name": "service", "kind": "int", "default": 1}] + TOKEN + CONFIRM),
    (("ride", "clone"), "ride", "clone", "Re-request cancelled ride (dry-run)",
     RIDE_ID + [{"name": "reason-id", "kind": "int", "default": 0}] + TOKEN + CONFIRM),
    (("ride", "block"), "ride", "block", "Block driver (dry-run)", RIDE_ID + TOKEN + CONFIRM),
    (("ride", "boarded"), "ride", "boarded", "Confirm boarding (dry-run)",
     RIDE_ID + TOKEN + CONFIRM),
    (("ride", "carpool", "accept"), "ride", "carpool", "Accept carpool offer (dry-run)",
     [{"name": "offer_id", "kind": "pos"}] + TOKEN + CONFIRM),
    (("ride", "carpool", "reject"), "ride", "carpool", "Reject carpool offer (dry-run)",
     [{"name": "offer_id", "kind": "pos"}] + TOKEN + CONFIRM),
    (("ride", "carpool", "dismiss"), "ride", "carpool", "Dismiss carpool offer (dry-run)",
     [{"name": "offer_id", "kind": "pos"}] + TOKEN + CONFIRM),
]


def spec_default(field):
    if "default" in field:
        return field["default"]
    return True if field["kind"] == "noflag" else None


def run(core, route, values):
    found = next((o for o in OPS if o[0] == tuple(route)), None)
    if not found:
        raise ValueError(f"unknown op: {' '.join(route)}")
    _, target, method, _, fields = found[:5]
    box = {}
    for f in fields:
        key = f["name"].replace("-", "_")
        if isinstance(values, dict):
            box[key] = values.get(key, spec_default(f))
        else:
            box[key] = getattr(values, key, spec_default(f))
    if "token" not in box:
        box["token"] = None
    return getattr(core[target], method)(types.SimpleNamespace(**box))


def apply_fields(parser, fields):
    for f in fields:
        name, kind = f["name"], f["kind"]
        attr = name.replace("-", "_")
        if kind == "pos":
            parser.add_argument(attr)
        elif kind == "flag":
            parser.add_argument(f"--{name}", action="store_true")
        elif kind == "noflag":
            parser.add_argument(f"--no-{name}", dest=attr, action="store_false")
            parser.set_defaults(**{attr: True})
        else:
            kw = {"type": {"int": int, "float": float}.get(kind, str)}
            if "default" in f:
                kw["default"] = f["default"]
            if f.get("required"):
                kw["required"] = True
            parser.add_argument(f"--{name}", **kw)


def build():
    core = hub()
    _groups.clear()
    parser = argparse.ArgumentParser(prog="boogh")
    top = parser.add_subparsers(dest="cmd", required=True)
    children = {o[0][:2] for o in OPS if len(o[0]) == 3}
    for op in OPS:
        route, desc, fields = op[0], op[3], op[4]
        if len(route) == 1:
            leaf = top.add_parser(route[0], help=desc)
            apply_fields(leaf, fields)
            leaf.set_defaults(_route=route)
        elif len(route) == 2:
            _ensure_group(top, route[0])
            if route in children:
                _ensure_second(route[0], route[1])
            else:
                leaf = _groups[route[0]][1].add_parser(route[1], help=desc)
                apply_fields(leaf, fields)
                leaf.set_defaults(_route=route)
        else:
            _ensure_group(top, route[0])
            second = _ensure_second(route[0], route[1])
            leaf = second.add_parser(route[2], help=desc)
            apply_fields(leaf, fields)
            leaf.set_defaults(_route=route)
    return parser, core


_groups = {}


def _ensure_group(top, name):
    if name not in _groups:
        group = top.add_parser(name)
        _groups[name] = (group, group.add_subparsers(dest="op", required=True))
    return _groups[name]


def _ensure_second(group_name, op_name):
    key = (group_name, op_name)
    if key not in _groups:
        default = next((o for o in OPS if o[0] == (group_name, op_name) and len(o) > 5),
                       None)
        _, branch = _groups[group_name]
        leaf = branch.add_parser(op_name, help=(default[3] if default else None))
        if default:
            apply_fields(leaf, default[4])
            leaf.set_defaults(_route=(group_name, op_name))
        _groups[key] = leaf.add_subparsers(dest="act", required=default is None)
    return _groups[key]
