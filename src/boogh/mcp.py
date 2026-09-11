"""boogh mcp is a stdio MCP server over the cli ops."""
import contextlib
import io
import json
import sys
import types
import urllib.error

from boogh.cli import hub

VERSION = "2024-11-05"

BASE = {"token": None, "confirm": False, "follow": 0, "timeout": 30,
        "page": 0, "limit": 10, "compact": True, "supertype": None,
        "code": None, "place": None, "lat": None, "long": None,
        "from_lat": None, "from_lng": None, "to_lat": None, "to_lng": None,
        "origin": None, "dest": None, "service": 1, "ride_id": None,
        "state": "passenger", "reason": None, "voucher": None}


def tools(food, ride, geo):
    return [
        ("ride_price", "Fare quote between two points", ride.price,
         {"origin": "saved place or address", "dest": "saved place or address"}),
        ("ride_track", "Active ride snapshot", ride.track, {}),
        ("ride_status", "Raw active-ride status", ride.status, {}),
        ("ride_history", "Past rides", ride.history, {}),
        ("ride_profile", "Passenger profile", ride.profile, {}),
        ("ride_places", "Saved places", ride.places, {}),
        ("ride_request", "REQUEST A REAL RIDE (confirm=true)", ride.request,
         {"origin": "", "dest": "", "service": 1}),
        ("ride_cancel", "Cancel a live ride (confirm=true)", ride.cancel,
         {"ride_id": ""}),
        ("food_vendors", "Nearby restaurants", food.vendors,
         {"supertype": "e.g. restaurant"}),
        ("food_vendor", "Vendor details", food.vendor, {"code": ""}),
        ("food_menu", "Vendor menu", food.menu, {"code": ""}),
        ("food_reviews", "Vendor reviews", food.reviews,
         {"code": ""}),
        ("food_area", "Marketing area for point", food.area, {}),
        ("food_place", "Address search", food.place, {"place": ""}),
        ("food_reverse", "Reverse geocode", food.reverse, {}),
        ("food_pending", "Pending food orders (needs login)", food.pending, {}),
        ("geo", "Resolve place to coords", None, {"query": ""}),
    ]


def schema(extra):
    props = {"token": {"type": "string"}}
    for key, hint in extra.items():
        props[key] = {"type": ["string", "number"]}
        if hint:
            props[key]["description"] = str(hint)
    return {"type": "object", "properties": props}


def run(fn, geo, args):
    if fn is None:
        return geo.resolve(args.query)
    box = io.StringIO()
    params = dict(BASE)
    params.update({k: v for k, v in (args or {}).items() if v is not None})
    try:
        with contextlib.redirect_stdout(box):
            fn(types.SimpleNamespace(**params))
    except SystemExit as e:
        return {"error": f"exit: {e.code}", "output": box.getvalue()}
    except urllib.error.HTTPError as e:
        return {"error": f"http {e.code}: {e.read().decode()[:500]}"}
    texts = []
    for chunk in box.getvalue().split("\n}\n"):
        chunk = chunk.strip()
        if chunk:
            texts.append(chunk if chunk.endswith("}") else chunk + "}")
    return {"output": texts}


def handle(msg, table, geo):
    mid = msg.get("id")
    method = msg.get("method", "")
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": mid,
                "result": {"protocolVersion": VERSION,
                           "capabilities": {"tools": {}},
                           "serverInfo": {"name": "boogh", "version": "0.1.0"}}}
    if method == "ping":
        return {"jsonrpc": "2.0", "id": mid, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": mid,
                "result": {"tools": [
                    {"name": n, "description": d, "inputSchema": schema(e)}
                    for n, d, _, e in table]}}
    if method == "tools/call":
        params = msg.get("params", {})
        name = params.get("name")
        found = next((f for n, _, f, _ in table if n == name), None)
        if found is None and name != "geo":
            return {"jsonrpc": "2.0", "id": mid,
                    "result": {"content": [{"type": "text",
                                            "text": json.dumps({"error": "unknown tool"}) }],
                               "isError": True}}
        if name == "geo" and (not params.get("arguments") or not params["arguments"].get("query")):
            return {"jsonrpc": "2.0", "id": mid,
                    "result": {"content": [{"type": "text",
                                            "text": json.dumps({"error": "query required"}) }],
                               "isError": True}}
        out = run(found, geo, params.get("arguments", {}))
        bad = isinstance(out, dict) and "error" in out
        return {"jsonrpc": "2.0", "id": mid,
                "result": {"content": [{"type": "text",
                                        "text": json.dumps(out, ensure_ascii=False)}],
                           "isError": bad}}
    if mid is not None:
        return {"jsonrpc": "2.0", "id": mid,
                "error": {"code": -32601, "message": f"unknown: {method}"}}
    return None


def main():
    food, ride, _, geo = hub()
    table = tools(food, ride, geo)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            res = handle(json.loads(line), table, geo)
        except Exception as e:
            res = {"jsonrpc": "2.0", "id": None,
                   "error": {"code": -32603, "message": str(e)}}
        if res is not None:
            print(json.dumps(res, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
