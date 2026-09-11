"""boogh mcp is a stdio MCP server over the op registry."""
import json
import sys
import urllib.error

from boogh import ops

VERSION = "2024-11-05"

TOOLS = {"_".join(route): route for route, *_ in ops.OPS}

NOISY = {(("food", "login", "send"), " (sends a real SMS)"),
         (("ride", "login", "send"), " (sends a real SMS/call)")}


def entry(route):
    return next(o for o in ops.OPS if o[0] == tuple(route))


def desc(route):
    found = next(o for o in ops.OPS if o[0] == tuple(route))
    return found[3] + dict(NOISY).get(tuple(route), "")


def schema(fields):
    props = {"token": {"type": "string"}}
    for f in fields:
        kind = {"str": "string", "int": "number", "float": "number",
                "flag": "boolean", "noflag": "boolean"}.get(f["kind"], "string")
        if f["kind"] == "pos":
            props[f["name"]] = {"type": "string"}
        else:
            props[f["name"]] = {"type": kind}
    return {"type": "object", "properties": props}


def run(core, route, args):
    try:
        return {"output": ops.run(core, route, args or {})}
    except ValueError as e:
        return {"error": str(e)}
    except urllib.error.HTTPError as e:
        return {"error": f"http {e.code}: {e.read().decode()[:500]}"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


def handle(msg, core):
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
                    {"name": n, "description": desc(r),
                     "inputSchema": schema(entry(r)[4])}
                    for n, r in TOOLS.items()]}}
    if method == "tools/call":
        params = msg.get("params", {})
        name = params.get("name")
        if name not in TOOLS:
            return {"jsonrpc": "2.0", "id": mid,
                    "result": {"content": [{"type": "text",
                                            "text": json.dumps({"error": "unknown tool"})}],
                               "isError": True}}
        out = run(core, TOOLS[name], params.get("arguments", {}))
        bad = "error" in out
        return {"jsonrpc": "2.0", "id": mid,
                "result": {"content": [{"type": "text",
                                        "text": json.dumps(out, ensure_ascii=False)}],
                           "isError": bad}}
    if mid is not None:
        return {"jsonrpc": "2.0", "id": mid,
                "error": {"code": -32601, "message": f"unknown: {method}"}}
    return None


def main():
    core = ops.hub()
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            res = handle(json.loads(line), core)
        except Exception as e:
            res = {"jsonrpc": "2.0", "id": None,
                   "error": {"code": -32603, "message": str(e)}}
        if res is not None:
            print(json.dumps(res, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
