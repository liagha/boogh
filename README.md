# boogh

Snapp ride + SnappFood CLI. Stdlib only.

Reads old tokens from `~/.config/snapppp/tokens.json` on first run,
writes to `~/.config/boogh/tokens.json`.

```bash
uv sync
uv run boogh food cities
uv run boogh food vendors
uv run boogh food menu 3kv8mn
uv run boogh geo "میدان ونک"
uv run boogh ride price --origin "میدان ونک" --dest "تجریش"
uv run boogh ride profile
uv run boogh ride place
uv run boogh ride history --limit 5
```

Reads default to home location, no flags needed.
`--origin`/`--dest` take `lat,lng`, a saved name (`Home`, `دفتر`), or Persian text.
Writes never fire without `--confirm`. Default prints dry-run.

## MCP

Stdio server, same ops, no extra deps:

```bash
uv run boogh-mcp
```

Point any MCP client at it (command `uv`, args `["run", "--project", "/path/to/boogh", "boogh-mcp"]`).
Every op is a tool (`food_vendors`, `ride_price`, `ride_login_send`, ...),
generated from the same registry, so CLI and MCP never drift.
Writes need `"confirm": true` in args, otherwise they return dry-run.
