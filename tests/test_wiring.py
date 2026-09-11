"""Wiring coverage: every op parses in cli and resolves in mcp."""
import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout

from boogh import mcp, ops


def argv(route, fields):
    out = []
    for part in route[1:]:
        out.append(part)
    for f in fields:
        if f["kind"] == "pos":
            out.append("x")
        elif f["kind"] == "flag":
            pass
        elif f["kind"] == "noflag":
            pass
        elif f.get("required"):
            out.append(f"--{f['name']}")
            out.append({"int": "1", "float": "1.5"}.get(f["kind"], "x"))
    return out


class Wiring(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parser, cls.core = ops.build()

    def test_targets_exist(self):
        for op in ops.OPS:
            route, target, method = op[0], op[1], op[2]
            self.assertTrue(hasattr(self.core[target], method),
                            f"{' '.join(route)} -> {target}.{method}")

    def test_cli_parses_every_route(self):
        for op in ops.OPS:
            route, fields = op[0], op[4]
            with self.subTest(route=route):
                args = self.parser.parse_args([route[0], *argv(route, fields)])
                self.assertEqual(tuple(args._route), tuple(route))

    def test_cli_defaults(self):
        args = self.parser.parse_args(["ride", "price", "--origin", "35.8,51.0",
                                       "--dest", "35.7,51.4"])
        self.assertTrue(args.compact)
        args = self.parser.parse_args(["ride", "profile"])
        self.assertEqual(tuple(args._route), ("ride", "profile"))
        args = self.parser.parse_args(["ride", "place"])
        self.assertEqual(tuple(args._route), ("ride", "place"))

    def test_help_renders(self):
        for cmd in (["--help"], ["food", "--help"], ["ride", "--help"],
                    ["geo", "--help"], ["ride", "login", "--help"]):
            with self.subTest(cmd=cmd):
                box = io.StringIO()
                with redirect_stdout(box):
                    try:
                        self.parser.parse_args(cmd)
                    except SystemExit as e:
                        self.assertEqual(e.code, 0)
                self.assertTrue(box.getvalue().strip())

    def test_mcp_tools_match_ops(self):
        routes = {o[0] for o in ops.OPS}
        for name, route in mcp.TOOLS:
            with self.subTest(tool=name):
                self.assertIn(tuple(route), routes, f"{name} -> {route}")

    def test_mcp_list(self):
        res = mcp.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
                         self.core)
        names = [t["name"] for t in res["result"]["tools"]]
        self.assertEqual(names, [n for n, _ in mcp.TOOLS])
        for tool in res["result"]["tools"]:
            self.assertIn("inputSchema", tool)

    def test_mcp_dry_run_no_network(self):
        res = mcp.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                          "params": {"name": "ride_request",
                                     "arguments": {"origin": "35.83,51.01",
                                                   "dest": "35.75,51.40"}}},
                         self.core)
        body = json.loads(res["result"]["content"][0]["text"])
        self.assertTrue(body["output"]["dry_run"])
        self.assertFalse(res["result"]["isError"])

    def test_mcp_unknown_tool(self):
        res = mcp.handle({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                          "params": {"name": "nope", "arguments": {}}},
                         self.core)
        self.assertTrue(res["result"]["isError"])

    def test_ops_run_unknown(self):
        with self.assertRaises(ValueError):
            ops.run(self.core, ("ride", "nope"), {})


if __name__ == "__main__":
    unittest.main()
