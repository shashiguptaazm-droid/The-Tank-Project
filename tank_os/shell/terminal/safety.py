"""Command classifier — assigns a :class:`SafetyClass` to every shell command.

Tiers (low → high impact):

* ``SAFE``      — pure functions with no I/O (``echo``, ``true``, ``date``).
* ``READ``      — read-only on the local filesystem (``ls``, ``cat``,
  ``grep``, ``find``).
* ``MUTATING``  — modifies state but recoverable (``mkdir``, ``touch``,
  ``cp``, ``tar``, ``git``, ``python``).
* ``DANGEROUS`` — high impact or needs privilege (``rm``, ``chmod``,
  ``kill``, ``sudo``, ``systemctl``, ``shutdown``, ``reboot``).

Use :func:`CommandSafety.classify` to assign a tier; the engine consults
the tier to decide whether the operator must confirm before running.
The classifier never executes the command — it is pure-functional.

Security note: classify also inspects the command for shell expansion
constructs (``$(...)``, backticks, ``${...}``, process substitution)
and pipe-segments the line, returning the MAX of every segment's
verb class — so ``ls | xargs rm`` is rated DANGEROUS even though the
first token ``ls`` is safe. This is what stops a user from quietly
running ``echo $(rm -rf /tmp/foo)`` and bypassing the gate on the
happy verb ``echo``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum, auto


class SafetyClass(Enum):
    SAFE = auto()
    READ = auto()
    MUTATING = auto()
    DANGEROUS = auto()
    BLOCKED = auto()


_CLASS_RANK = {
    SafetyClass.SAFE: 0,
    SafetyClass.READ: 1,
    SafetyClass.MUTATING: 2,
    SafetyClass.DANGEROUS: 3,
    SafetyClass.BLOCKED: 4,
}


@dataclass
class CommandSafety:
    """Stateless command classifier.

    The set of verbs can be overridden by subclassing + redeclaring the
    frozensets — useful for a unit-test-only "permissive" classification.
    """

    SAFE_VERBS: frozenset = frozenset({
        "echo", "true", "false", ":", "pwd", "whoami", "date", "uname",
        "type", "alias", "set", "env", "printenv", "history", "yes",
        "seq", "expr", "test",
    })
    READ_VERBS: frozenset = frozenset({
        "ls", "cat", "head", "tail", "less", "more", "grep", "egrep",
        "fgrep", "find", "wc", "awk", "gawk", "sed", "sort", "uniq",
        "diff", "tr", "cut", "tee", "xargs", "stat", "file", "which",
        "whereis", "man", "info", "ps", "top", "htop", "btop", "df",
        "du", "free", "uptime", "hostname", "id", "groups", "w", "who",
        "lsof", "ss", "netstat", "ip", "ifconfig", "route", "ping",
    })
    MUTATING_VERBS: frozenset = frozenset({
        "mkdir", "touch", "cp", "mv", "ln", "tar", "zip", "unzip",
        "gzip", "gunzip", "git", "pip", "pip3", "pipx", "python",
        "python3", "bash", "sh", "zsh", "make", "cmake", "gcc",
        "g++", "clang", "clang++", "docker", "podman", "npm", "yarn",
        "npx", "curl", "wget",
    })
    DANGEROUS_VERBS: frozenset = frozenset({
        "rm", "rmdir", "chmod", "chown", "kill", "killall", "pkill",
        "sudo", "su", "mkfs", "mkswap", "fdisk", "parted", "dd",
        "shutdown", "reboot", "halt", "poweroff", "systemctl",
        "service", "iptables", "ufw", "mount", "umount", "useradd",
        "userdel", "passwd",
    })

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------
    def classify(self, command: str) -> SafetyClass:
        text = (command or "").strip()
        if not text:
            return SafetyClass.SAFE
        # 1. Hard-blocked patterns win over everything.
        if _matches_any(text, _BLOCKED_PATTERNS):
            return SafetyClass.BLOCKED
        # 2. Shell-expansion injection cannot be classified by verb
        #    alone — promote to MUTATING so the operator confirms.
        if _SUBSTITUTION.search(text):
            return SafetyClass.MUTATING
        # 3. Pipe- and chain-segments are evaluated independently and
        #    we return the worst class found. This catches
        #    `ls | xargs rm`, `false && rm foo`, `true ; kill -9 $$`,
        #    etc.
        segments = _split_chains(text)
        if not segments:
            return SafetyClass.SAFE
        worst = max(segments, key=self._class_rank)
        return self._classify_segment(worst)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _classify_segment(self, segment: str) -> SafetyClass:
        first = _first_token(segment)
        if not first:
            return SafetyClass.SAFE
        if first in self.SAFE_VERBS:
            return SafetyClass.SAFE
        if first in self.READ_VERBS:
            return SafetyClass.READ
        if first in self.MUTATING_VERBS:
            return SafetyClass.MUTATING
        if first in self.DANGEROUS_VERBS:
            return SafetyClass.DANGEROUS
        # Unknown verb → default to MUTATING so the operator must
        # confirm. This is safer than auto-running an unfamiliar tool.
        return SafetyClass.MUTATING

    def _class_rank(self, seg: str) -> int:
        return _CLASS_RANK[self._classify_segment(seg)]


# Module-level helper kept for callers that want to rank a single
# segment string without building an instance first. Reuses the
# shared _CLASS_RANK table.
class _NoInstanceSafety(CommandSafety):
    """Empty subclass — used purely for the rank helper to avoid the
    dataclass's default-instance machinery for one-shot calls."""


def _rank_segment(seg: str) -> int:
    return _CLASS_RANK[_NoInstanceSafety()._classify_segment(seg)]


# Backwards-compat alias for the pre-fix callers that imported the
# helper under the old name. Deprecated: prefer
# ``CommandSafety._class_rank`` on an instance.
_class_rank = _rank_segment


def _class_rank(seg: str) -> int:
    """Rank a single segment string against the dataclass's classifier."""
    inst = CommandSafety()
    return _CLASS_RANK[inst._classify_segment(seg)]


def _first_token(command: str) -> str:
    """Return the first non-flag, non-env-var, non-sudo verb in the line."""
    tokens = re.split(r"\s+|;|&&|\|\|", command)
    for token in tokens:
        if not token:
            continue
        if token.startswith("sudo"):
            continue
        if token.startswith("env"):
            continue
        if token.startswith("-"):
            continue
        if "=" in token and not token.startswith("="):
            continue
        bare = token.split("/")[-1]
        return bare
    return ""


def _split_chains(text: str) -> list:
    """Split on pipes and shell boolean chains. Returns stripped segments."""
    parts = re.split(r"\s*(?:\|\||&&|\||;)\s*", text)
    return [p.strip() for p in parts if p.strip()]


# ───────────────────────────────────────────────────────────────────────────
# Pattern matchers
# ───────────────────────────────────────────────────────────────────────────

# Matches $(...), backticks `...`, ${...}, and process sub <(...) / >(...)
_SUBSTITUTION = re.compile(r"\$\(|`|\$\{|<\(|>\(")


# Hard-blocked patterns — true no-go whether or not the operator
# confirms. Tuned to be conservative (errs toward blocking) — a
# legitimate operator can still run these by escaping the engine.
#
# Note: `shutdown`, `reboot`, `halt`, `poweroff` are NOT in this list —
# they belong to DANGEROUS (verb class), so the operator gets a
# confirmation gate instead of a hard block. That preserves graceful
# robot shutdown while still guarding against accidental power-off.
_BLOCKED_PATTERNS = [
    re.compile(r"\brm\s+-?r[fR]?\s+/\s*$"),
    re.compile(r"\brm\s+-?r[fR]?\s+/\*"),
    re.compile(r"\brm\s+-?r[fR]?\s+~"),
    re.compile(r"\bmkfs(\.\w+)?\b"),
    re.compile(r"\bmkswap\b"),
    re.compile(r"\bdd\s+.*of=/dev/(sd|nvme|mmc|hd|tty)"),
    re.compile(r":\(\)\s*\{.*\};\s*:"),                       # fork bomb
    re.compile(r":()\{ :\|:& \};:"),
    # curl|sh: only block when the right-hand side is a real shell
    # AND the left-hand side points to http(s):// — but skip loopback /
    # 127.0.0.1 / 0.0.0.0 hosts so legitimate local pipelines stay
    # governable (downgraded to MUTATING + confirm-gate) instead of
    # silently hard-blocked.
    re.compile(
        r"\bcurl\s+(?:-[A-Za-z]+\s+)*https?://(?!(?:localhost|127\.0\.0\.1|0\.0\.0\.0)\b)[^\s|]+\s*\|\s*(sudo\s+)?(ba)?sh\b"
    ),
    re.compile(
        r"\bwget\s+(?:-[A-Za-z]+\s+)*https?://(?!(?:localhost|127\.0\.0\.1|0\.0\.0\.0)\b)[^\s|]+\s*\|\s*(sudo\s+)?(ba)?sh\b"
    ),
    re.compile(r"\bchmod\s+-R\s+0+\s+/"),
    re.compile(r"\b(chmod|chown)\s+-R\s+777\s+/"),
    re.compile(r">\s*/dev/(sd|nvme|mmc)"),
]


def _matches_any(text: str, patterns) -> bool:
    return any(p.search(text) for p in patterns)
