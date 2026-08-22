# TankOS Agent Framework

A unified surface that lets any AI LLM discover and invoke all 1,166 host-level CLI features + plugin slots on The Tank Project.

## Why

The project has 40 host-level CLI scripts in `/root/the tank project/scripts/`, each with a stable argparse surface. Without a framework, an LLM has to discover them by hand (cloning the repo, reading READMEs, parsing `--help`).

This framework gives any LLM:

- **Discovery**: a single endpoint (`GET /manifest`) returns all 1,166 tools in OpenAI `tools=[…]`, Anthropic `tools=[…]`, or raw JSON format.
- **Dispatch**: a single endpoint (`POST /invoke`) takes `{tool, args}` and runs the right `python3 scripts/<name>.py <sub>` with bounded timeout.
- **Identity**: bearer auth shared with `tank_command_bridge` (`TANK_API_KEY`).
- **Audit**: every invocation logged to SQLite WAL with token hash (never raw token), tool, args, status, exit_code, duration.
- **Rate-limit**: per-token token bucket (60 reads/min, 10 writes/min by default).
- **Plugin slots**: future features self-register by adding a `python3 scripts/<new>.py` file with `cmd_<sub>` functions; the registry picks them up at next `discover()`.

## Modules

| File | Role |
|------|------|
| `__init__.py`   | public surface, version |
| `schemas.py`    | dataclass types (ToolDefinition, ToolCallRequest, ToolCallResponse, AuditRecord) |
| `registry.py`   | walks `scripts/*.py`, parses Python AST, builds ToolDefinition list |
| `invoker.py`    | runs subprocesses, returns bounded results |
| `manifest.py`   | emits OpenAI / Anthropic / raw JSON formats |
| `audit.py`      | SQLite WAL audit log |
| `server.py`     | FastAPI app factory on :8085 |
| `cli.py`        | top-level CLI dispatcher |

## Quick start

```bash
# List all tools (table)
python3 -m tank_os.agent_framework.cli list

# Show one tool
python3 -m tank_os.agent_framework.cli show download_music.album_bandcamp

# Emit OpenAI-style manifest to /tmp/openai.json
python3 -m tank_os.agent_framework.cli manifest --format openai --write /tmp/openai.json

# Run a tool
python3 -m tank_os.agent_framework.cli invoke download_music.album_bandcamp --dry-run

# Boot the FastAPI server
python3 -m tank_os.agent_framework.cli server --port 8085

# Then from any LLM client:
curl http://127.0.0.1:8085/manifest/openai \
  -H 'Authorization: Bearer $TANK_API_KEY' | head -c 200
```

## Adding a new plugin

1. Create `/root/the tank project/scripts/<my_plugin>.py` with `cmd_<sub>` functions and module-level docstrings that mention F-IDs.
2. The server picks it up automatically on next restart.
3. Optionally register the script category in `tank_os/agent_framework/registry.py: _CATEGORIES = {...}`.

No code change to the framework is needed.

## Limits

- Each subprocess bounded to `request.timeout_s` (default 30s).
- stdout capped at 8 KiB, stderr at 4 KiB per response.
- Audit log: append-only sqlite + WAL; cleanup is operator's responsibility.
- Plugin metadata is AST-derived; `cmd_*` docstring first line becomes the LLM-facing description.
- Currently no streaming; invoke is request-response. Streaming is a follow-up.

## Auth

Same env vars as `tank_command_bridge`:

```bash
TANK_API_KEY="single-admin-token"
# OR
TANK_API_KEYS='{"admin": "admin-token", "agent": "agent-token", "readonly": "readonly-token"}'
```

Per-token rate limits: 60 reads/min, 10 writes/min by default.

## Endpoint reference

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET    | /health | none | status + tool count |
| GET    | /manifest | read | raw JSON manifest |
| GET    | /manifest/openai | read | OpenAI tools=[…] |
| GET    | /manifest/anthropic | read | Anthropic tools=[…] |
| GET    | /manifest/summary | read | counts + categories |
| POST   | /invoke | write | run a tool |
| GET    | /audit | read | recent audit log entries |
| POST   | /audit/clear | admin | wipe audit log |
