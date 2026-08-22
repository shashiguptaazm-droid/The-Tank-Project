# TankOS Agent Framework — Design Doc

> **Audience:** any AI coding agent or operator picking up The Tank Project
> and wanting to drive every feature end-to-end through a single,
> discoverable surface.

---

## 1. Why

The Tank Project has **40 host-level CLI scripts totaling 1,166 subcommands**
(plus 20 ROS 2 packages exposing ~21 system topics, a `tank_command_bridge`
on :8082 with 9 robot commands, a `tank_meta` HTTP shim on :8083, a
`tank_personalize` dashboard on :8084). Each subsystem has its own
calling convention:

- The 40 CLIs use `python3 scripts/<name>.py <sub>` with argparse.
- `tank_command_bridge` uses `POST /api/cmd/{name}` with bearer auth.
- `tank_meta` uses `GET /api/meta/{code,hardware,decisions,knowledge,status}`.
- `tank_personalize` uses `GET/PUT /api/persona`, `GET/PUT /api/prefs`, etc.
- The ROS 2 topics are JSON-over-std_msgs.

An AI LLM that wants to use all of these has to learn 5+ conventions
and 1166+ subcommand names. The framework collapses them into **one
manifest + one dispatch endpoint + one audit chain**.

## 2. Goal

A single, durable surface for any LLM (OpenAI, Anthropic, raw HTTP) that
exposes:

1. **All 1,166 CLI subcommands** as structured tools with name + description + JSON schema.
2. **Every subsystem** (ROS 2 nodes, FastAPI services) discoverable through the same `GET /manifest`.
3. **A single dispatch** (`POST /invoke`) so the LLM's `tools=[…]` calls land uniformly.
4. **Identity, audit, rate-limit** as a first-class concern — no leaky subprocess to debug.
5. **Plugin slots** so future features self-register without rewriting the framework.

## 3. Architecture

```
   LLM provider (OpenAI / Anthropic / Generic)
                  │  tools=[…] or raw JSON
                  ▼
   ┌─────────────────────────────────────────────────────┐
   │ AGENT FRAMEWORK  (tank_os/agent_framework, :8085)   │
   │                                                     │
   │   registry.py     → walks scripts/*.py, AST → tools │
   │   manifest.py     → OpenAI / Anthropic / raw JSON   │
   │   server.py       → FastAPI on :8085                │
   │   audit.py        → SQLite WAL                      │
   │   invoker.py      → subprocess for each dispatch    │
   │   cli.py          → top-level dispatcher            │
   └────────────────────────────┬────────────────────────┘
                                │ python3 scripts/<n>.py <sub>
                                ▼
   ┌─────────────────────────────────────────────────────┐
   │ 40 HOST-LEVEL CLI SCRIPTS (~10,000 LoC)             │
   │ + tank_command_bridge (:8082)                       │
   │ + tank_meta (:8083)                                 │
   │ + tank_personalize (:8084)                          │
   │ + tank_os/internet (REST :8900)                     │
   └─────────────────────────────────────────────────────┘
```

The framework sits at Layer 5 of the existing 5-layer architecture,
alongside (but orthogonal to) Simple Internet. It does NOT modify
any host-level CLI script — it only discovers them.

## 4. Manifest formats

Three canonical formats emitted by `Manifest`:

| Format | Endpoint | Use case |
|--------|----------|----------|
| `raw`           | `/manifest`            | Provider-neutral; full metadata (category, risk_tier, script_path) |
| `openai`        | `/manifest/openai`     | OpenAI function-calling: `[{type:"function", function:{name,description,parameters}}]` |
| `anthropic`     | `/manifest/anthropic`  | Anthropic tool use: `[{name, description, input_schema}]` |
| `summary`       | `/manifest/summary`    | Just counts: `{total, categories, risk_distribution}` |

**OpenAI form** (per tool):
```json
{
  "type": "function",
  "function": {
    "name": "download_music.album_bandcamp",
    "description": "F717 - download full album from Bandcamp (auth required for paid)",
    "parameters": {
      "type": "object",
      "properties": {
        "dry_run": {"type": "boolean", "default": false},
        "out": {"type": "string"}
      }
    }
  }
}
```

**Anthropic form**:
```json
{
  "name": "download_music.album_bandcamp",
  "description": "F717 - download full album from Bandcamp (auth required for paid)",
  "input_schema": {
    "type": "object",
    "properties": {
      "dry_run": {"type": "boolean", "default": false},
      "out": {"type": "string"}
    }
  }
}
```

## 5. Discovery protocol

`ToolRegistry.discover()` is **AST-based** — it parses `scripts/*.py` for
top-level `cmd_<sub>(args)` functions, extracts:

- tool name (`script_basename.sub`)
- description (docstring's first line, ≤ 240 chars)
- F-IDs (regex on the full docstring, e.g. "F717 — …")
- risk_tier (keyword-driven from name + description)
- category (looked up in `_CATEGORIES` map by script basename; default "general")

No subprocess is invoked at discovery time — that's much faster than
spawning `--help` for each script.

## 6. Dispatch protocol

`POST /invoke` body:
```json
{
  "tool_name": "download_music.album_bandcamp",
  "args": {"dry_run": true, "out": "/tmp/test"},
  "request_id": "req-abc123",
  "timeout_s": 30
}
```

Server logic:
1. Look up `tool` via `ToolRegistry.get(tool_name)`.
2. Build `python3 scripts/<n>.py <sub> --dry-run --out /tmp/test`.
3. `subprocess.run(..., timeout=30, capture_output=True)`.
4. Cap stdout at 8 KiB, stderr at 4 KiB.
5. Return `ToolCallResponse` JSON.
6. Write audit record.

Failure modes:
- Unknown tool: `status="unknown"`, exit_code=2.
- Timeout: `status="timeout"`, exit_code=124.
- Non-zero exit: `status="err"`, exit_code=echoed.
- Auth/rate-limit: HTTP 401 or 429.

## 7. Auth model

Reuses `tank_command_bridge`'s env-var convention:

```bash
TANK_API_KEY="single-admin-token"
# OR
TANK_API_KEYS='{"admin": "admin-token", "agent": "agent-token", "readonly": "readonly-token"}'
```

A single shared `TANK_API_KEY` covers both the agent framework AND the
robot command bridge — operators only mint one token.

Per-token token-bucket rate-limit:
- 60 reads/min by default (`GET /manifest/*`, `GET /audit`)
- 10 writes/min by default (`POST /invoke`, `POST /audit/clear`)

Token hash (SHA-256 prefix) is what gets stored in the audit log.
Raw tokens are never logged.

## 8. Audit log

SQLite WAL append-only log under `tank_ws/data/agent_audit.db`:

```sql
CREATE TABLE audit (
    audit_id TEXT PRIMARY KEY,   -- "aud-<12 hex chars>"
    request_id TEXT,
    tool_name TEXT,
    args_json TEXT,
    actor_token_hash TEXT,       -- SHA-256[:16] of the bearer
    status TEXT,                 -- "ok" | "err" | "timeout" | "unknown"
    exit_code INTEGER,
    duration_ms INTEGER,
    ts REAL                      -- unix epoch
);
```

Operators can `GET /audit?limit=N&tool_name=X` to inspect history.
Admins can `POST /audit/clear` to wipe.

## 9. Plugin slots

Any `python3 scripts/<new>.py` with `cmd_<sub>` functions self-registers
on next `discover()`. The registry rules:

- Script basename → namespace prefix (e.g. `download_podcasts.py` →
  `download_podcasts.<sub>`).
- Docstring first line → tool description.
- F-IDs in docstring → metadata.
- Name/description keywords → risk_tier.
- Script basename → category (registered in `_CATEGORIES`).

To add a new category for a fresh script, edit
`tank_os/agent_framework/registry.py:_CATEGORIES[<basename>] = "<category>"`
and restart the server. (Default is "general" if absent.)

## 10. Risks & known limits

- **Stub handlers**: most of the 1,166 features are currently stub
  JSON-record-and-exit handlers. Real download/invocation pipelines
  live in `tank_os/internet/` and need to be wired in front of these
  stubs before they're useful for end-to-end automation.
- **Single-process subprocess**: each `/invoke` blocks Python until
  the child exits. With 30s timeout that's a 30s worst-case latency.
  Pool / async queue is a future improvement.
- **No streaming**: responses are full-RTT. Streaming progress events
  via WebSocket is a follow-up.
- **Args schema is generic**: every tool exposes `{dry_run, out}`. The
  actual per-tool args are not introspected (argparse introspection
  via `--help` is a follow-up).
- **Risk tier is heuristic**: name/description keyword matching is not
  precise. A human operator should review `manifest/summary` before
  exposing a high-risk token to a remote agent.

## 11. Extension points

- **Per-tool ACL**: add a `TANK_ROLE_TOOLS = {"admin": [...], "readonly": [...]}` mapping.
- **Streaming**: add WebSocket `/invoke/stream` that emits progress events.
- **Real download integration**: wrap each `cmd_<sub>` to forward to `tank_os.internet.downloader.DownloadManager.add_task(...)`.
- **Pydantic schemas**: replace the dict `args_schema` with `pydantic.BaseModel` subclasses for runtime validation.

## 12. How to add a new plugin (one-liner)

```bash
# Write the plugin
cat > /root/the\ tank\ project/scripts/my_plugin.py <<'EOF'
#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
PREFIX = "[my_plugin]"
def _ok(m): print(f"{PREFIX} OK   {m}", flush=True); return 0
def cmd_do_thing(args):
    """F1234 — do a thing for the LLM."""
    return _ok(json.dumps({"thing": "done"}))
HANDLERS = {"do-thing": cmd_do_thing}
def build_parser():
    p = argparse.ArgumentParser(); sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("do-thing", help="F1234 — do a thing for the LLM")
    return p
def main(argv=None):
    args = build_parser().parse_args(argv)
    return HANDLERS[args.cmd](args)
if __name__ == "__main__":
    sys.exit(main())
EOF

# Restart the server — the new tool is auto-discovered on next request
python3 -m tank_os.agent_framework.cli server
```

That's it. Read this doc, then `python3 -m tank_os.agent_framework.cli list`.
