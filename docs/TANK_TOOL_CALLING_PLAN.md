# 🧠 THE TANK — Proper AI Tool-Calling Architecture (20 parts)

> The fundamental rule, enforced by code:

```
Human → AI/LLM → Tool Selection → Tool Validator → Permission + Safety
     → Tool Executor → UNO Q / Jetson / ESP32 / STM32 → Tool Result → AI
```

**Never:** `LLM → arbitrary shell command → motor`.

**Status legend:** `✅` implemented & tested · `🔶` partially · `⬜` not yet ·
`🧭` consolidation target.

**Core module:** `tank_os/core/tool_engine.py` (typed, permissioned pipeline) ·
GUI: `tank_os/windows/tool_graph_screen.py` (live tool graph + composer).
The repo's existing `tank_os/agent_framework/` (ToolRegistry over 146 scripts /
1,966 discovered tools) is adopted via `bind_script_registry()`.

---

| # | Feature | Status | Where |
|---|---|---|---|
| 1 | **Tool Registry** — central registry with `{name, description, risk, requires_confirmation}` | ✅ | `ToolEngine.register()` + `ToolSpec`; script registry bound via `bind_script_registry()` (1,966 tools discovered) |
| 2 | **Read-only tools** — auto-executable, no confirmation | ✅ | `robot.get_battery/temperature/position/heading/speed/health/…` → `RiskTier.READ_ONLY` |
| 3 | **Low-risk action tools** — display/mission.pause/audio/notification/lights | ✅ | `RiskTier.LOW` — AI executes automatically |
| 4 | **Controlled robot tools** — validate then check battery/motors/E-stop/obstacle | ✅ | `robot.move/rotate/goto/follow/stop` → `RiskTier.CONTROLLED` + `_safety_check()` interlocks |
| 5 | **High-risk tools** — explicit authorization | ✅ | `system.reboot/shutdown`, `firmware.update`, `motor/servo.calibration` → `RiskTier.HIGH` → `NEEDS_APPROVAL` gate |
| 6 | **Emergency tools** — deterministic, never LLM-gated | ✅ | `safety.emergency_stop/disable_motors` → `RiskTier.EMERGENCY`; result shows the deterministic path `physical button + safety service → MCU → MOTOR OFF` |
| 7 | **Tool permissions** — agent profiles | ✅ | `AgentRole` Observer/Assistant/Navigator/Maintenance/Admin; role → risk allowance + tool-prefix allowlist; **even Admin cannot bypass the safety controller** |
| 8 | **Hierarchical ownership** — distributed brain | ✅ | `OWNERSHIP`: vision/navigation/world→jetson · robot/mission/network/hardware→unoq · sensor/device→esp32 · motor/servo/safety→stm32 |
| 9 | **Tool chaining** | ✅ | `run_chain()` — readiness workflow: get_health → get_battery → sensor → jetson → network → mission |
| 10 | **AI autonomous tool loop** — THINK→SELECT→VALIDATE→EXECUTE→OBSERVE→DECIDE | ✅ | `execute()` pipeline + `run_chain()` + `recover()` |
| 11 | **Standardized results** | ✅ | `ToolResult{success, tool, timestamp, data, warnings, error, latency_ms}` |
| 12 | **Tool failure recovery** | ✅ | `recover()` — `OBSTACLE_DETECTED → navigation.replan`, else `ask_human` |
| 13 | **Tool audit log** | ✅ | `AuditEntry{ts, agent, tool, args, validation, safety, execution, latency_ms}` — every call recorded with per-stage PASS/BLOCK/SUCCESS |
| 14 | **Tool-call visualization** | ✅ | `tool_graph_screen.py` — USER REQUEST → AI → tool nodes, each ✓ with risk/latency + audit panel |
| 15 | **Human approval layer** | ✅ | risk classification: READ_ONLY/LOW → EXECUTE · CONTROLLED → checks · HIGH → EXPLICIT APPROVAL (`NEEDS_APPROVAL`) |
| 16 | **Tool simulation mode** | ✅ | `dry_run=True` — simulated results, no side effects (also the default for script tools in tests) |
| 17 | **Tool sandbox** | ✅ | `SANDBOX` bounds: `max_speed_mps ≤ 0.5`, `distance_m ≤ 5`, PWM ±255, servo 500–2500 µs — validator rejects invented values (`speed=100 → VALIDATION_FAILED`) |
| 18 | **Tool discovery** | ✅ | `capabilities()` + `list_tools()` — AI adapts to available hardware |
| 19 | **Tool versioning** | 🔶 | `ToolSpec.version/schema_version/minimum_firmware/supported_hardware` fields present |
| 20 | **AI Tool Composer** (the killer feature) | ✅ | `compose(goal)` — dynamically builds a workflow from available tools and reports readiness % |

---

## 🎬 The AI Tool Composer (§20) — live demo

```
User: "Prepare the robot for autonomous patrol."
AI dynamically constructs:
  robot.get_health → robot.get_battery → sensor.check → jetson.check
  → navigation.localize → mission.validate → network status
  → "PATROL READINESS: 94%"
```

## ⛔ Sandbox rejection (§17) — the AI cannot invent values

```
robot.move({direction: "forward", max_speed_mps: 100})
  → VALIDATION_FAILED: arg 'max_speed_mps'=100 outside sandbox [0.0, 0.5]
```

## ⚠ High-risk approval (§5)

```
system.reboot → risk HIGH → requires_confirmation
  → NEEDS_APPROVAL: requires explicit human approval
GUI: ⚠ AI REQUEST — "REBOOT UNO Q — Apply firmware update." [APPROVE] [CANCEL]
```

## 🛡 Emergency tools (§6) — deterministic, never LLM-gated

```
safety.emergency_stop → E-STOP → physical button + safety service → MCU → MOTOR OFF
The AI can REQUEST an e-stop, but the mechanism stays deterministic.
```

## Proof

- **363 tests passing** (345 + 18 new tool-engine tests: registry, risk tiers,
  role permissions, sandbox rejections, high-risk approval, emergency path,
  standardized results, chaining, recovery, audit, discovery, composer,
  ownership map, script-registry binding + 1 GUI smoke test).
- `65_ai_tool_graph.png` + updated 27-screen contact sheet.
- Verified on the UNO Q and the VPS.

## Prioritized next

1. #19 full tool versioning semantics (schema_version + minimum_firmware checks).
2. #10 AI autonomous loop agent that drives the loop with the LLM (assistant.py).
3. #16 wire the simulator/digital-twin to the tool sandbox (simulate before execute).
