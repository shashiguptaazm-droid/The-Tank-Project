"""LLM node — local Llama-3 inference via llama.cpp with tool-calling.

Subscribes
    /intent_text  std_msgs/String   the spoken intent after STT

Publishes
    /assistant_text     std_msgs/String   the assistant's response
    /assistant/hallucinations  std_msgs/Float32  simple confidence proxy
    /assistant/uncertain  std_msgs/String  JSON — fired when the local
                                           model is unsure, so
                                           ``tank_assistant.external_llm_client``
                                           can call out to Freebuff /
                                           OpenAI / Anthropic.
    /assistant/confirmation_request  std_msgs/String  JSON — fired when
                                           a write-class tool is awaiting
                                           user yes/no.

Parameters
    model_path       str   default ""
    n_ctx            int   default 4096
    temperature      float default 0.7
    max_tokens       int   default 256
    system_prompt    str   default "You are The Tank — a friendly home robot."
    fallback_echo    bool  default True   (if True and no model, echo /intent_text)
    uncertainty_min_response_chars  int   default 12
    bridge_url       str   default "http://localhost:8082"   (command bridge)
    api_key          str   default ""   (TANK_API_KEY; Bearer token for bridge)
    confirm_timeout_s float default 15.0  (max wait for user yes/no)
    tools_enabled    bool  default True   (master switch for tool-calling)

Tool-calling format
-------------------
The local model emits a markdown-fenced block:

    I'll move forward.
    ```tool_call
    {"name": "move", "params": {"vx": 0.2, "wz": 0.0, "duration_s": 2.0}}
    ```

A bare JSON object with ``"name"`` and ``"params"`` keys is also accepted
as a fallback. The state machine handles confirmation for write-class
tools (estop/move/patrol/dock) by publishing a confirmation request and
waiting for the next ``/intent_text`` matching yes/no.

Read-class tools (capture/telemetry/query/chat) execute immediately
and trigger a 2nd LLM call to verbalize the JSON result for TTS.
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
import uuid
from typing import Any, Dict, List, Optional

try:
    import requests                       # noqa: F401
    _REQUESTS_AVAILABLE = True
except ImportError:                                       # pragma: no cover
    _REQUESTS_AVAILABLE = False

    class _StubRequests:                                  # type: ignore[no-redef]
        @staticmethod
        def post(*_a, **_k):
            raise RuntimeError("requests not installed; tool exec disabled")

    requests = _StubRequests                              # type: ignore[assignment]

try:
    import rclpy                                       # noqa: F401
    from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
    from rclpy.node import Node
    from std_msgs.msg import Float32, String
    _RCLPY_AVAILABLE = True
except ImportError:
    _RCLPY_AVAILABLE = False

    class _NoopPublisher:                              # type: ignore[no-redef]
        def publish(self, *_a, **_k): return None

    class _NoopLogger:                                 # type: ignore[no-redef]
        def info(self, *_a, **_k): pass
        def warn(self, *_a, **_k): pass
        def error(self, *_a, **_k): pass
        def debug(self, *_a, **_k): pass

    class _StubString:                                 # type: ignore[no-redef]
        """Stub std_msgs/String — accepts ``String(data=...)``."""
        def __init__(self, *args, **kwargs):
            if args and not isinstance(args[0], str):
                # positional Float32-style call: ignore, default to ""
                self.data = ""
            elif args:
                self.data = args[0]
            else:
                self.data = kwargs.get("data", "")

    class _StubFloat32:                                # type: ignore[no-redef]
        """Stub std_msgs/Float32 — accepts ``Float32(data=0.5)``."""
        def __init__(self, *args, **kwargs):
            if args:
                self.data = args[0]
            else:
                self.data = float(kwargs.get("data", 0.0))

    class _StubNode:                                   # type: ignore[no-redef]
        def __init__(self, *_a, **_k): pass
        def create_subscription(self, *_a, **_k): return None
        def create_publisher(self, *_a, **_k): return _NoopPublisher()
        def create_timer(self, *_a, **_k): return None
        def get_logger(self): return _NoopLogger()
        def get_clock(self): return type("C", (), {
            "now": lambda self: type("N", (), {"nanoseconds": 0})()})()
        def declare_parameter(self, *_a, **_k): return None
        def get_parameter(self, name): return type(
            "P", (), {"value": _PARAM_DEFAULTS.get(name, "")})()

    Node = _StubNode                                   # type: ignore[assignment]
    String = _StubString                               # type: ignore[assignment]
    Float32 = _StubFloat32                             # type: ignore[assignment]
    MutuallyExclusiveCallbackGroup = object             # type: ignore[assignment]

# Defaults for the _StubNode above — kept at module scope so they don't
# shadow the real ROS params.
_PARAM_DEFAULTS = {
    "model_path": "",
    "n_ctx": 4096,
    "temperature": 0.7,
    "max_tokens": 256,
    "system_prompt": "You are The Tank — a friendly home robot.",
    "fallback_echo": True,
    "uncertainty_min_response_chars": 12,
    "bridge_url": "http://localhost:8082",
    "api_key": "",
    "confirm_timeout_s": 15.0,
    "tools_enabled": True,
}

LLM_QOS = 10
UNCERTAINTY_MIN_RESPONSE_CHARS = 12
CONFIRM_TIMEOUT_S_DEFAULT = 15.0

# ── Tool-calling parsing ──────────────────────────────────────────────────
# Regex-based parser — kept ONLY for the bare-JSON fallback. The fenced
# body extraction uses an explicit scan (see :func:`parse_tool_calls`
# below) because DOTALL non-greedy regex can span across malformed +
# valid fence pairs.
TOOL_CALL_BARE_RE = re.compile(
    r"\{[^{}]*?\"name\"\s*:\s*\"[^\"]+\"[^{}]*?\"params\"\s*:\s*\{.*?\}[^{}]*?\}",
    re.DOTALL,
)

# Confirmation regexes — case-insensitive, anchored at the start.
YES_RE = re.compile(r"^\s*(yes|yeah|yep|sure|do it|go|confirm|ok|okay)\s*$",
                    re.IGNORECASE)
NO_RE = re.compile(r"^\s*(no|nope|cancel|stop|never\s*mind|abort)\s*$",
                    re.IGNORECASE)


# Anchor strings for the scan-based parser — keeps the regex out of
# the body-extraction path so DOTALL non-greedy can't span across
# malformed + valid fence pairs.
_TOOL_FENCE_OPEN = "```tool_call"
_TOOL_FENCE_CLOSE = "```"


def _strip_tool_fences(text: str) -> str:
    """Remove every `````tool_call ... ``` ``` block from ``text``.

    Same scan logic as :func:`parse_tool_calls` but returns the input
    with fence blocks excised (used to clean prose before a confirmation
    request). Replaces the old ``TOOL_CALL_RE.sub('', text)`` regex.
    """
    if not text:
        return ""
    out: List[str] = []
    i = 0
    n = len(text)
    while i < n:
        open_pos = text.find(_TOOL_FENCE_OPEN, i)
        if open_pos == -1:
            out.append(text[i:])
            break
        out.append(text[i:open_pos])
        content_start = open_pos + len(_TOOL_FENCE_OPEN)
        while content_start < n and text[content_start] in " \t\r\n":
            content_start += 1
        close_pos = text.find(_TOOL_FENCE_CLOSE, content_start)
        if close_pos == -1:
            # Unclosed fence — keep the rest verbatim.
            out.append(text[open_pos:])
            break
        i = close_pos + len(_TOOL_FENCE_CLOSE)
    return "".join(out)


def parse_tool_calls(text: str) -> List[Dict[str, Any]]:
    """Extract tool-call JSON blocks from LLM output.

    Each ``\`\`\`tool_call ... \`\`\``` fence contributes one body.
    Bodies that fail ``json.loads`` are silently skipped (malformed
    blocks are expected during development). Falls back to a single
    bare-JSON match when no fences are present at all.

    Returns a list of dicts with ``name`` (str) and ``params`` (dict).
    """
    if not text:
        return []
    blocks: List[str] = []
    i = 0
    n = len(text)
    while i < n:
        open_pos = text.find(_TOOL_FENCE_OPEN, i)
        if open_pos == -1:
            break
        # Skip whitespace after the opening fence marker.
        content_start = open_pos + len(_TOOL_FENCE_OPEN)
        while content_start < n and text[content_start] in " \t\r\n":
            content_start += 1
        # Find the next closing fence.
        close_pos = text.find(_TOOL_FENCE_CLOSE, content_start)
        if close_pos == -1:
            break
        # Strip trailing whitespace from the body but keep internal structure.
        body_end = close_pos
        while body_end > content_start and text[body_end - 1] in " \t\r":
            body_end -= 1
        blocks.append(text[content_start:body_end])
        i = close_pos + len(_TOOL_FENCE_CLOSE)

    # Fallback: single bare JSON if no fenced blocks were found.
    if not blocks:
        bare = TOOL_CALL_BARE_RE.search(text)
        if bare:
            blocks = [bare.group(0)]

    out: List[Dict[str, Any]] = []
    for raw in blocks:
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):
            continue
        name = obj.get("name")
        params = obj.get("params", {})
        if isinstance(name, str) and isinstance(params, dict):
            out.append({"name": name, "params": params})
    return out


def _format_tool_block(tool: Dict[str, Any]) -> str:
    """One tool's worth of description for the system prompt."""
    desc = tool.get("description", "").strip()
    rate = tool.get("rate_class", "read")
    params_schema = tool.get("parameters", {})
    # Compact JSON Schema dump keeps the prompt small.
    params_str = json.dumps(params_schema, separators=(",", ":"))
    return (
        f"- **{tool['name']}** [{rate}]\n"
        f"  {desc}\n"
        f"  Parameters schema: `{params_str}`"
    )


def build_system_prompt(manifest_dict: Dict[str, Any], *,
                        identity: str,
                        confirm: bool = True) -> str:
    """Assemble the full system prompt including tool manifest.

    The prompt tells the LLM to emit a single ```tool_call ...``` block
    when it wants to invoke a tool, and (when ``confirm`` is True) that
    write-class tools will gate on user confirmation.
    """
    tools = manifest_dict.get("tools", []) if manifest_dict else []
    if not tools:
        return identity
    tools_str = "\n".join(_format_tool_block(t) for t in tools)
    confirm_note = (
        "Write-class tools (estop, move, patrol, dock) require explicit "
        "user confirmation before they execute. Read-class tools "
        "(capture, telemetry, query, chat) execute immediately.\n"
        if confirm else ""
    )
    return (
        f"{identity}\n\n"
        f"You have access to the following tools via the command bridge:\n\n"
        f"{tools_str}\n\n"
        f"{confirm_note}"
        f"To use a tool, output exactly ONE markdown code block:\n\n"
        f"```tool_call\n"
        f'{{"name": "<tool_name>", "params": {{<params matching the schema>}}}}\n'
        f"```\n\n"
        f"Rules:\n"
        f"- Match the parameter schema exactly. The bridge rejects malformed "
        f"requests.\n"
        f"- For dangerous actions, ask the user first in plain prose, then "
        f"emit the tool_call block.\n"
        f"- Do NOT wrap the tool_call in conversational filler. Surrounding "
        f"prose is fine but the block must be a single fenced JSON object.\n"
        f"- If no tool is needed, reply naturally without the fence."
    )


# ── Manifest loader ────────────────────────────────────────────────────────

def _load_manifest() -> Dict[str, Any]:
    """Best-effort fetch of the tool manifest.

    Tries (in order):
      1. The bridge package — direct import (offline, deterministic).
      2. HTTP GET to ``{bridge_url}/api/cmd/manifest`` (online).
      3. Empty dict — node falls back to plain text replies.
    """
    try:
        from tank_command_bridge.manifest import manifest_json  # type: ignore
        return manifest_json()
    except Exception:
        pass
    url = os.environ.get("TANK_BRIDGE_URL", "http://localhost:8082")
    try:
        if _REQUESTS_AVAILABLE:
            r = requests.get(f"{url}/api/cmd/manifest", timeout=2.0)
            r.raise_for_status()
            return r.json()
    except Exception:
        pass
    return {}


# ── Engines (unchanged) ────────────────────────────────────────────────────

class LlamaCppEngine:
    """Lazy wrapper around llama-cpp-python."""

    def __init__(self, model_path: str, n_ctx: int, temperature: float,
                 max_tokens: int) -> None:
        from llama_cpp import Llama
        self._llm = Llama(
            model_path=model_path,
            n_ctx=n_ctx,
            temperature=temperature,
            verbose=False,
        )

    def prompt(self, system: str, user: str, max_tokens: int) -> str:
        out = self._llm.create_chat_completion(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=max_tokens,
        )
        return out["choices"][0]["message"]["content"].strip()


class StubEngine:
    """Fallback that echoes the input back wrapped in a response template."""
    def prompt(self, system: str, user: str, max_tokens: int) -> str:
        return f"[stub echo] I heard you say: {user!r}. (No LLM available.)"


# ── ROS node ───────────────────────────────────────────────────────────────

# State machine values
ST_IDLE = "idle"
ST_AWAIT_CONFIRM = "await_confirm"
ST_EXECUTING = "executing"


class LlmNode(Node):
    def __init__(self, engine: Optional[object] = None) -> None:
        super().__init__("llm_node")
        self._declare_params()
        mp = str(self.get_parameter("model_path").value)
        if mp and engine is None:
            try:
                self._engine = LlamaCppEngine(
                    model_path=mp,
                    n_ctx=int(self.get_parameter("n_ctx").value),
                    temperature=float(self.get_parameter("temperature").value),
                    max_tokens=int(self.get_parameter("max_tokens").value),
                )
                self.get_logger().info(f"LLM loaded from {mp}")
            except Exception as exc:
                self.get_logger().warn(
                    f"failed to load LLM ({exc}); using stub"
                )
                self._engine = StubEngine()
        else:
            self._engine = engine or StubEngine()

        # ── Tool-calling state ──
        self._base_system_prompt = str(
            self.get_parameter("system_prompt").value)
        self._max_tokens = int(self.get_parameter("max_tokens").value)
        self._uncertainty_threshold = int(
            self.get_parameter("uncertainty_min_response_chars").value)
        self._bridge_url = str(self.get_parameter("bridge_url").value)
        self._api_key = str(self.get_parameter("api_key").value)
        self._confirm_timeout_s = float(
            self.get_parameter("confirm_timeout_s").value)
        self._tools_enabled = bool(self.get_parameter("tools_enabled").value)

        self._manifest: Dict[str, Any] = {}
        self._tool_rates: Dict[str, str] = {}
        if self._tools_enabled:
            self._manifest = _load_manifest()
            for t in self._manifest.get("tools", []):
                self._tool_rates[t.get("name", "")] = t.get(
                    "rate_class", "read")
            if self._manifest:
                self.get_logger().info(
                    f"loaded {len(self._tool_rates)} tools from manifest"
                )

        self._lock = threading.Lock()
        # State-machine fields
        self._state = ST_IDLE
        self._pending_cmd: Optional[Dict[str, Any]] = None  # full tool dict
        self._pending_intent: str = ""                     # for synthesis
        self._pending_ts: float = 0.0

        cbg = MutuallyExclusiveCallbackGroup()
        self.create_subscription(String, "/intent_text",
                                  self._on_intent, LLM_QOS,
                                  callback_group=cbg)
        self._reply_pub = self.create_publisher(String, "/assistant_text",
                                                  LLM_QOS)
        self._conf_pub = self.create_publisher(Float32,
                                                 "/assistant/hallucination",
                                                 LLM_QOS)
        self._uncertain_pub = self.create_publisher(
            String, "/assistant/uncertain", LLM_QOS)
        self._confirm_req_pub = self.create_publisher(
            String, "/assistant/confirmation_request", LLM_QOS)
        self.get_logger().info("llm_node initialised")

    def _declare_params(self) -> None:
        self.declare_parameter("model_path", "")
        self.declare_parameter("n_ctx", 4096)
        self.declare_parameter("temperature", 0.7)
        self.declare_parameter("max_tokens", 256)
        self.declare_parameter("system_prompt",
                               "You are The Tank — a friendly home robot.")
        self.declare_parameter("fallback_echo", True)
        self.declare_parameter("uncertainty_min_response_chars",
                               UNCERTAINTY_MIN_RESPONSE_CHARS)
        self.declare_parameter("bridge_url", "http://localhost:8082")
        self.declare_parameter("api_key", "")
        self.declare_parameter("confirm_timeout_s", CONFIRM_TIMEOUT_S_DEFAULT)
        self.declare_parameter("tools_enabled", True)

    # ── Active system prompt: base identity + tool manifest ──
    def _active_system_prompt(self) -> str:
        if not self._tools_enabled or not self._manifest:
            return self._base_system_prompt
        return build_system_prompt(
            self._manifest, identity=self._base_system_prompt, confirm=True,
        )

    # ── Main callback: state-machine dispatch ──
    def _on_intent(self, msg: String) -> None:
        intent = (msg.data or "").strip()
        if not intent:
            return
        with self._lock:
            state = self._state

        # Confirmation branch — only fires when awaiting user yes/no
        if state == ST_AWAIT_CONFIRM:
            self._handle_confirmation(intent)
            return

        # Default IDLE path: do a full LLM inference.
        try:
            response = self._engine.prompt(
                self._active_system_prompt(), intent, self._max_tokens,
            )
        except Exception as exc:
            self.get_logger().warn(f"LLM failed: {exc}")
            return

        self._conf_pub.publish(Float32(data=float(bool(response))))

        # Confidence proxy — short / null replies fire /assistant/uncertain
        if len(response.strip()) < self._uncertainty_threshold:
            self._fire_uncertain(intent, response)
            return

        # Try to extract a tool call.
        calls = parse_tool_calls(response) if self._tools_enabled else []
        if calls:
            self._handle_tool_call(intent, response, calls)
            return

        # Plain text reply.
        self._reply_pub.publish(String(data=response))

    # ── Tool-call dispatcher ──
    def _handle_tool_call(self, intent: str, raw_response: str,
                          calls: List[Dict[str, Any]]) -> None:
        # Execute first call only — chained side-effects need separate turns.
        call = calls[0]
        name = str(call.get("name", "")).strip()
        params = dict(call.get("params") or {})
        rate = self._tool_rates.get(name, "read")
        self.get_logger().info(
            f"tool call: {name} rate={rate} params={params}"
        )

        if not self._tools_enabled or not self._manifest:
            self._reply_pub.publish(String(
                data="Tools are disabled. I can't run that command."))
            return

        if rate == "write":
            # Park in AWAIT_CONFIRM. Strip the tool_call block from the
            # prose so the user sees a clean confirmation request.
            prose = _strip_tool_fences(raw_response).strip()
            confirm_text = (
                f"{prose}\n\nShould I run `{name}` with these parameters? "
                f"Say yes to confirm." if prose else
                f"Should I run `{name}` with these parameters? "
                f"Say yes to confirm."
            )
            with self._lock:
                self._state = ST_AWAIT_CONFIRM
                self._pending_cmd = {"name": name, "params": params}
                self._pending_intent = intent
                self._pending_ts = time.monotonic()
            self._reply_pub.publish(String(data=confirm_text))
            self._confirm_req_pub.publish(String(data=json.dumps({
                "tool": name,
                "params": params,
                "ts": time.time(),
                "timeout_s": self._confirm_timeout_s,
            })))
            return

        # Read-class tool — execute immediately.
        self._execute_and_publish(intent, name, params)

    # ── Confirmation handler ──
    def _handle_confirmation(self, intent: str) -> None:
        with self._lock:
            cmd = self._pending_cmd
            ts = self._pending_ts
            self._pending_cmd = None
            self._state = ST_IDLE
        if not cmd:
            return
        age = time.monotonic() - ts
        if age > self._confirm_timeout_s:
            self._reply_pub.publish(String(
                data="Confirmation timed out. Cancelling."))
            return
        if YES_RE.match(intent):
            self._execute_and_publish(
                self._pending_intent, cmd["name"], cmd["params"])
            return
        if NO_RE.match(intent):
            self._reply_pub.publish(String(data="Cancelled."))
            return
        # Anything else — treat as new intent (don't lose the user's words).
        self.get_logger().warn(
            f"unexpected reply during confirmation: {intent!r}; re-engaging"
        )
        # Re-enter IDLE inference path with the same intent.
        self._on_intent(String(data=intent))

    # ── HTTP execution + synthesis ──
    def _execute_and_publish(self, intent: str, name: str,
                             params: Dict[str, Any]) -> None:
        try:
            result = self._execute_tool(name, params)
        except Exception as exc:
            self.get_logger().warn(
                f"tool exec failed ({name}): {exc}",
                throttle_duration_sec=10.0,
            )
            self._reply_pub.publish(String(
                data=f"I couldn't run {name}: {exc}"))
            return

        # Verbalize read-class results via 2nd LLM call so TTS sounds
        # natural. Write-class results are terse "Done." announcements.
        rate = self._tool_rates.get(name, "read")
        if rate == "read":
            self._synthesize_and_publish(intent, name, result)
        else:
            ok = bool(result) and not (
                isinstance(result, dict) and result.get("rejected"))
            text = "Done." if ok else f"Not done: {result}"
            self._reply_pub.publish(String(data=text))

    def _execute_tool(self, name: str,
                      params: Dict[str, Any]) -> Dict[str, Any]:
        """POST to the command bridge and return the parsed JSON body."""
        if not _REQUESTS_AVAILABLE:
            raise RuntimeError("requests not installed")
        url = f"{self._bridge_url}/api/cmd/{name}"
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        body = {
            "audit_id": str(uuid.uuid4()),
            "params": params,
        }
        resp = requests.post(url, headers=headers, json=body, timeout=5.0)
        resp.raise_for_status()
        try:
            return resp.json()
        except Exception as exc:
            raise RuntimeError(
                f"bridge returned non-JSON ({resp.status_code}): "
                f"{resp.text[:120]}"
            ) from exc

    def _synthesize_and_publish(self, intent: str, tool_name: str,
                                result: Dict[str, Any]) -> None:
        """2nd LLM pass: verbalize the JSON result for TTS."""
        synth_system = (
            f"{self._base_system_prompt}\n\n"
            f"You just executed the `{tool_name}` tool and got this JSON "
            f"result:\n{json.dumps(result, indent=2)[:1200]}\n\n"
            f"Reply in ONE sentence (under 30 words) describing the result "
            f"for a voice assistant. Be specific with numbers."
        )
        try:
            text = self._engine.prompt(
                synth_system, intent, max_tokens=80,
            ).strip()
            if not text:
                text = json.dumps(result)[:200]
        except Exception as exc:
            self.get_logger().warn(
                f"synthesis failed ({tool_name}): {exc}",
                throttle_duration_sec=10.0,
            )
            text = json.dumps(result)[:200]
        self._reply_pub.publish(String(data=text))

    # ── Uncertainty trigger ──
    def _fire_uncertain(self, intent: str, response: str) -> None:
        try:
            self._uncertain_pub.publish(String(data=json.dumps({
                "text": intent,
                "local_reply": response[:200],
                "ts": self.get_clock().now().nanoseconds,
            })))
            self.get_logger().info(
                "low-confidence reply — /assistant/uncertain fired"
            )
        except Exception as exc:
            self.get_logger().warn(
                f"uncertainty publish failed: {exc}",
                throttle_duration_sec=10.0,
            )


def main(args=None) -> None:
    rclpy.init(args=args)
    node = LlmNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
