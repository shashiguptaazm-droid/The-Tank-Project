# AI Commands Cheat-Sheet — The Tank Project

Cheat-sheet for any AI coding-assistant (Freebuff, Claude Code, GPT Codex,
Cody, etc.) that wants to drive The Tank over HTTP.

The Pi exposes a JSON command bridge on **port 8082**. Every request
**must** include `Authorization: Bearer <TANK_API_KEY>` (the key lives
in `/root/the tank project/secrets/tank_api_key` on the Jetson) and a
server-generated `audit_id` (uuidv4).

---

## Live manifest

```bash
curl -s http://tank.lan:8082/api/cmd/manifest | jq .
```

Returns the full machine-readable tool list (JSON Schema Draft 2020-12
parameters + OpenAI `tools=[...]` shape). Fetch it every session so
parameter drift doesn't surprise you.

---

## Auth

```bash
-H "Authorization: Bearer $TANK_API_KEY"     # required
-H "Content-Type: application/json"           # for POST
```

If you don't see `200 OK`, the most likely reasons are:

| status | meaning |
|--------|---------|
| `401`  | missing / wrong `TANK_API_KEY` |
| `429`  | rate-limit exhausted (60 read/min, 10 write/min per token) |
| `500`  | the bridge couldn't publish to ROS — check `motor_controller` is up |
| `503`  | Pi hasn't loaded any API keys yet — bad boot config |

---

## Commands

### `estop`

Latched or release the hardware e-stop. **Wins over every other write.**

```bash
curl -X POST http://tank.lan:8082/api/cmd/estop \
  -H "Authorization: Bearer $TANK_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"audit_id":"'$(uuidgen)'","params":{"state":true}}'
```

Response: `{"latched":true,"ts":1700000000.0}`

### `move`

Drive the base for a bounded duration. `safety_watchdog` will stop the
motors when `duration_s` elapses if you don't issue another `move`.

| param       | unit           | clamps       |
|-------------|----------------|--------------|
| `vx`        | m/s            | [-0.5, 0.5]  |
| `wz`        | rad/s          | [-1.5, 1.5]  |
| `duration_s`| seconds        | [0.1, 5.0]   |

Anything outside the clamp is rounded safely — the robot won't go past
the limits even if you ask.

```bash
curl -X POST http://tank.lan:8082/api/cmd/move \
  -H "Authorization: Bearer $TANK_API_KEY" \
  -d '{"audit_id":"'$(uuidgen)'","params":{"vx":0.2,"wz":0.1,"duration_s":2.0}}'
```

### `patrol`

Start / pause autonomous patrolling. `mode ∈ {waypoint, random, pause, stop}`.

```bash
curl -X POST http://tank.lan:8082/api/cmd/patrol \
  -H "Authorization: Bearer $TANK_API_KEY" \
  -d '{"audit_id":"'$(uuidgen)'","params":{"mode":"waypoint"}}'
```

### `dock`

Arm the AprilTag auto-dock (`enable=true`) so `tank_dock` will start
chasing the dock tag.

```bash
curl -X POST http://tank.lan:8082/api/cmd/dock \
  -H "Authorization: Bearer $TANK_API_KEY" \
  -d '{"audit_id":"'$(uuidgen)'","params":{"enable":true}}'
```

### `capture`

One-shot camera snapshot. Returns a base64-JPEG data URL, downsampled
to `max_px` (default 640) on the long edge.

```bash
curl -X POST http://tank.lan:8082/api/cmd/capture \
  -H "Authorization: Bearer $TANK_API_KEY" \
  -d '{"audit_id":"'$(uuidgen)'","params":{"max_px":640}}'
```

### `telemetry`

Aggregate health snapshot — battery, CPU, estop state, latest emotion,
`/cmd_vel` age.

```bash
curl -X POST http://tank.lan:8082/api/cmd/telemetry \
  -H "Authorization: Bearer $TANK_API_KEY" \
  -d '{"audit_id":"'$(uuidgen)'","params":{}}'
```

### `query`

Forward a structured query into `tank_meta`'s memory.

| `kind`     | what you get                                       |
|------------|----------------------------------------------------|
| `code`     | top-k Python file descriptions + functions        |
| `hardware` | hardware component reference by name              |
| `decisions`| past DEC-NNN entries (problem + solution + result)|
| `knowledge`| docs markdown excerpts                             |

```bash
curl -X POST http://tank.lan:8082/api/cmd/query \
  -H "Authorization: Bearer $TANK_API_KEY" \
  -d '{"audit_id":"'$(uuidgen)'",
       "params":{"kind":"decisions","text":"pwm frequency","k":3}}'
```

### `chat`

Free-form message to The Tank's assistant. `use_external_llm=true`
flips the routing so the bridge asks Freebuff / OpenAI / Anthropic
when local `llama.cpp` is unsure (publishes `/assistant/uncertain`).

```bash
curl -X POST http://tank.lan:8082/api/cmd/chat \
  -H "Authorization: Bearer $TANK_API_KEY" \
  -d '{"audit_id":"'$(uuidgen)'",
       "params":{"text":"what is your current battery?",
                 "use_external_llm":true}}'
```

---

## Audit log

Every successful command (and every failure) is recorded.

```bash
curl http://tank.lan:8082/api/cmd/audit?limit=20 \
  -H "Authorization: Bearer $TANK_API_KEY"
```

Returns up to N last audit records: `{ts, audit_id, token_hash, role,
command, params_summary, status}`.

---

## Live status check (no auth required)

```bash
curl http://tank.lan:8082/api/health   # -> {"ok":true}
```

---

## Reverse direction — Pi calls the AI

Set one of `FREEBUFF_API_KEY` / `OPENAI_API_KEY` / `ANTHROPIC_API_KEY`
on the Pi, then optionally set `TANK_API_PROVIDER=freebuff|openai|anthropic`.
The `tank_assistant/external_llm_client.py` node subscribes
`/assistant/uncertain` (fired by `llm_node` on low-confidence replies)
and publishes the merged answer on `/assistant/from_external`. The
`audit_id` round-trip preserves continuity.

---

## Recipes for coding assistants

### Freebuff

```
# inside a /task command:

Use the tank bridge at http://tank.lan:8082.
Authorise with $TANK_API_KEY in the Authorization header.
First call GET /api/cmd/manifest to learn the tool surface.
Then iterate with POST /api/cmd/<name> using the JSON schema
from the manifest.

For each invocation:
1. GET /api/cmd/manifest
2. Pick a tool name from `tools[].name`
3. Validate parameters against that tool's `parameters` schema
4. POST /api/cmd/<name> with `{"audit_id":"<uuid4>","params":{...}}`
5. If response says "rejected":"estop_latched" → call /api/cmd/estop
   with state=false first.
```

### Claude Code

```
When the user asks to drive the tank, fetch
http://tank.lan:8082/api/cmd/manifest and use the OpenAI `tools=[...]
shape to expose them as `actions` in your response. Each action maps
to POST /api/cmd/<name> with the JSON parameters from the manifest.
The bridge is local; assume the user has set $TANK_API_KEY in env.
```

### GPT Codex / Cursor

```
Add a custom HTTP tool to your agent pointing at
http://tank.lan:8082/api/cmd/manifest. Use the Bearer token
$TANK_API_KEY. The naming + schema are OpenAI-compatible so you can
treat each tool entry as one callable function.
```

## Recent host-level CLI expansion (post F206)

The host-level CLI surface has expanded from **15 commands** (the original `tank_os/internet/cli.py`) to **1,166 subcommands across 40 host-level Python CLI scripts** in `scripts/`. The AI ↔ Pi bridge on :8082 can drive any of these from Freebuff/Claude/Codex just like the original `--help`, `estop`, `move`, `patrol`, `dock`, `capture`, `telemetry`, `query`, `chat` flow.

The new scripts fall into the following domains (full mapping in README.md):
- AI & Vision: `ai_vision.py`, `ai_voice.py`, `vision_ar.py`, `personality.py`, `security_bio.py`
- Mobility & Environment: `mobility_nav.py`, `environment.py`, `health.py`, `outdoor_security.py`
- Media & Home: `media_hub.py`, `home_automation.py`, `creativity.py`, `kitchen.py`, `productivity_social.py`
- Productivity: `comm_networking.py`, `maintenance.py`, `education.py`, `gaming.py`, `energy_home.py`, `maker_misc.py`
- Simple Internet (F717-F1166): `download_*.py`, `download_*_2.py`, `download_*_3.py`

For a complete dependency manifest (apt + brew + pip + Jetson add-ons), see [`docs/DEPENDENCIES.md`](DEPENDENCIES.md).
