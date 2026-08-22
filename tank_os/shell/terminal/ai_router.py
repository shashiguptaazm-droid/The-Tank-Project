"""AIRouter — natural-language to shell mapping via :class:`AIManager`.

We force a JSON-shaped response so the engine can parse it
deterministically. When the AI is offline (returns the LocalStubProvider
echo or any non-JSON prose), we fall back to ``None`` so the engine
treats the user's input as the raw command — and the safety gate still
protects against accidents.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Optional

from tank_os.core.ai_manager import AIManager, AIResponse

logger = logging.getLogger("tank_os.terminal.ai")


@dataclass
class AIReply:
    command: str
    explanation: str = ""


_KNOWN_SHELL_VERBS = {
    "ls", "cat", "head", "tail", "grep", "egrep", "fgrep", "find",
    "awk", "sed", "sort", "wc", "tr", "cut", "diff", "xargs", "tee",
    "echo", "pwd", "whoami", "date", "df", "du", "ps", "top", "htop",
    "which", "whereis", "stat", "file", "man", "curl", "wget",
    "tar", "zip", "unzip", "git", "python", "python3", "bash", "sh",
    "zsh", "make", "cmake", "gcc", "clang", "docker", "podman",
    "mkdir", "touch", "cp", "mv", "ln", "rm", "chmod", "chown",
    "kill", "systemctl", "sudo", "su", "apt", "pip", "pip3", "yarn",
    "npm", "npx", "ssh", "scp", "rsync", "less", "more", "vim",
    "nano", "env", "export", "set", "unset",
}


class AIRouter:
    """Thin wrapper around :class:`AIManager` for terminal conversations."""

    DEFAULT_SYSTEM_PROMPT = (
        "You translate a one-line natural-language goal into a single "
        "POSIX shell command. Respond with strict JSON of the shape "
        '`{"command": "<shell cmd>", "explanation": "<one-line why>"}`. '
        "Do not wrap the JSON in code fences. Do not add commentary. "
        "If the goal cannot be expressed as a single shell command "
        '(e.g. interactive REPL), return {"command": "", '
        '"explanation": "<reason>"} and nothing else.'
    )

    def __init__(self, ai: Optional[AIManager] = None,
                 *, system_prompt: Optional[str] = None) -> None:
        self._ai = ai                           # lazy — None means AIManager()
        self._system_prompt = (system_prompt
                              if system_prompt is not None
                              else self.DEFAULT_SYSTEM_PROMPT)

    # ------------------------------------------------------------------
    def _get_ai(self) -> AIManager:
        return self._ai if self._ai is not None else AIManager()

    # ------------------------------------------------------------------
    def natural_to_shell(self, text: str) -> Optional[AIReply]:
        """Best-effort NL → shell. Returns ``None`` if AI is unhelpful."""
        prompt = (
            "Goal: " + (text or "").strip() + "\n"
            "Return only the JSON object — no markdown fences, no prose."
        )
        try:
            resp = self._get_ai().chat(
                prompt, system_prompt=self._system_prompt,
                temperature=0.2, max_tokens=256,
            )
        except Exception as exc:                                # noqa: BLE001
            logger.debug("AIManager.chat failed: %s", exc)
            return None
        body = resp.text if isinstance(resp, AIResponse) else str(resp)
        return _decode_reply(body)

    # ------------------------------------------------------------------
    def explain_error(self, command: str, stderr: str, *,
                      max_chars: int = 1500) -> str:
        """Ask AI to explain a failed command in 1–2 sentences + fix it."""
        prompt = (
            "Command:\n" + (command or "")[:500] + "\n\n"
            "stderr:\n" + (stderr or "")[:max_chars] + "\n\n"
            "Reply in 1–3 sentences: why did this fail and what command "
            "would likely succeed next? No markdown."
        )
        try:
            resp = self._get_ai().chat(prompt, temperature=0.3)
        except Exception as exc:                                # noqa: BLE001
            logger.debug("AIManager.chat failed: %s", exc)
            return ""
        return (resp.text if isinstance(resp, AIResponse)
                else str(resp)).strip()


# ───────────────────────────────────────────────────────────────────────────
# Reply decoding
# ───────────────────────────────────────────────────────────────────────────

def _decode_reply(text: str) -> Optional[AIReply]:
    """Try JSON decode → fall back to first shell-like line → ``None``."""
    text = (text or "").strip()
    if not text:
        return None
    stripped = _strip_fences(text)
    parsed = _try_json(stripped)
    if parsed is not None:
        cmd = str(parsed.get("command", "") or "").strip()
        explanation = str(parsed.get("explanation", "") or "").strip()
        if cmd:
            return AIReply(command=cmd, explanation=explanation)
        return None
    line = _first_plausible_command(stripped)
    if line:
        return AIReply(command=line, explanation=stripped[:400])
    return None


def _strip_fences(text: str) -> str:
    # Drop ```json ... ``` or ``` ... ``` blocks.
    text = re.sub(r"```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"```", "", text)
    return text.strip()


def _try_json(text: str) -> Optional[dict]:
    try:
        return json.loads(text)
    except Exception:                                           # noqa: BLE001
        pass
    # Fall back to extracting the first {...} block.
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except Exception:                                       # noqa: BLE001
            return None
    return None


BACKTICK_RE = re.compile(r"`([^`]+)`")
CODE_FENCE_RE = re.compile(r"`{1,3}([^`]+)`{1,3}")


def _first_plausible_command(text: str) -> str:
    # First, look for ``cmd`` / `cmd` Markdown code spans — common in
    # AI explanations like "I think you want: `ls -la /etc`".
    for match in BACKTICK_RE.finditer(text):
        candidate = match.group(1).strip().rstrip(".,;")
        if not candidate:
            continue
        first = candidate.split(maxsplit=1)[0].split("/")[-1]
        if first in _KNOWN_SHELL_VERBS:
            return candidate
    # Otherwise fall back to scanning each line for a known-verb prefix.
    for raw in text.splitlines():
        s = raw.strip().rstrip(".,;")
        if not s or s.startswith("#"):
            continue
        first = s.split(maxsplit=1)[0].split("/")[-1]
        if first in _KNOWN_SHELL_VERBS:
            return s
    return ""
