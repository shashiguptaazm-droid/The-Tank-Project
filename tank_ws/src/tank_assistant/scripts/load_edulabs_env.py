#!/usr/bin/env python3
"""Source /etc/edulabs-thesis-worker/worker.env into ``os.environ``.

Why this exists
---------------
The 11 edulabs API keys (``OPENAI_API_KEY``, ``GROQ_API_KEY``, etc.)
live in ``/etc/edulabs-thesis-worker/worker.env`` (a systemd
``EnvironmentFile=`` for the thesis Node.js worker). The Tank Project
must read those keys at runtime — but **must not** copy the key VALUES
into the project repo. This loader does exactly that.

Usage::

    # 1. As a pre-loader before importing tank_assistant:
    python3 -c "
    import scripts.load_edulabs_env   # noqa: F401
    import tank_assistant.external_llm_client as c
    c.main()
    "

    # 2. From a ROS2 launch file:
    from scripts import load_edulabs_env  # noqa: F401
    # ... rest of launch file

    # 3. From systemd (drop-in addition):
    #    [Service]
    #    EnvironmentFile=/etc/edulabs-thesis-worker/worker.env

The loader is idempotent: existing ``os.environ`` values take
precedence over the file (so a systemd ``Environment=`` override
still wins). Missing files are warned but not fatal.
"""
from __future__ import annotations

import logging
import os
import sys
from typing import Dict, Iterable, Optional


_LOG = logging.getLogger("tank_assistant.scripts.load_edulabs_env")


# Canonical list of paths we try, in order. The first one that exists
# and is readable wins. The first entry is overridable via the
# ``TANK_EDULABS_ENV_FILE`` env var so deployments that relocate the
# edulabs systemd unit don't have to fork this loader.
DEFAULT_ENV_FILES: tuple = (
    os.environ.get(
        "TANK_EDULABS_ENV_FILE",
        "/etc/edulabs-thesis-worker/worker.env",
    ),
    os.environ.get(
        "TANK_EDULABS_DASHBOARD_ENV_FILE",
        "/etc/edulabs-thesis-dashboard/worker.env",
    ),
    os.path.expanduser("~/.edulabs-thesis.env"),
    os.path.expanduser("~/.config/tank-os/edulabs.env"),
)

# Subset of env vars we want to surface explicitly. Loading the entire
# file is also fine (most ``.env`` files have only KEY=VALUE pairs), but
# the explicit list makes the API surface visible.
EDULABS_KEY_VARS: tuple = (
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "FREEBUFF_API_KEY",
    "OPENROUTER_API_KEY",
    "GROQ_API_KEY",
    "GEMINI_API_KEY",
    "MISTRAL_API_KEY",
    "CLOUDFLARE_API_KEY",
    "CEREBRAS_API_KEY",
    "COHERE_API_KEY",
    "REPLICATE_API_TOKEN",
    "HUGGINGFACE_API_KEY",
    "ENDPOINT_API_KEY",
    "DEEPSEEK_API_KEY",
)


def _parse_dotenv(path: str) -> Dict[str, str]:
    """Parse a ``.env`` file into ``{key: value}``.

    Handles::

        KEY=value
        KEY="quoted value"
        KEY='single quoted'
        # comment lines
        export KEY=value
        empty lines

    Quoted values have surrounding quotes stripped; escaped characters
    (``\\n``, ``\\"``) are unescaped. No shell substitution is
    performed (no ``$VAR`` expansion).
    """
    out: Dict[str, str] = {}
    with open(path, "r", encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[len("export "):].lstrip()
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            if not key:
                continue
            # Strip surrounding quotes.
            if (value.startswith('"') and value.endswith('"')) or (
                    value.startswith("'") and value.endswith("'")):
                value = value[1:-1]
            # Unescape common sequences.
            value = value.replace("\\n", "\n").replace(
                "\\\"", "\"").replace("\\'", "'")
            out[key] = value
    return out


def _merge_into_environ(parsed: Dict[str, str],
                        *,
                        only_keys: Optional[Iterable[str]] = None,
                        overwrite: bool = False) -> int:
    """Merge parsed vars into ``os.environ``. Returns count merged."""
    keys = set(only_keys) if only_keys is not None else None
    merged = 0
    for key, value in parsed.items():
        if keys is not None and key not in keys:
            continue
        if not overwrite and os.environ.get(key):
            continue  # existing wins
        os.environ[key] = value
        merged += 1
    return merged


def load_edulabs_env(*, paths: Iterable[str] = DEFAULT_ENV_FILES,
                     only_keys: Optional[Iterable[str]] = EDULABS_KEY_VARS,
                     overwrite: bool = False,
                     warn_missing: bool = True) -> int:
    """Find the first readable env file in ``paths`` and merge its vars.

    Parameters
    ----------
    paths
        Files to try, in order.
    only_keys
        Restrict to these variable names. ``None`` loads everything.
    overwrite
        If True, replace existing ``os.environ`` entries. Default
        (False) preserves any value already set in the process.
    warn_missing
        Log a warning if no env file is found.

    Returns
    -------
    int
        Number of variables merged into ``os.environ``.
    """
    for path in paths:
        if not os.path.isfile(path):
            continue
        if not os.access(path, os.R_OK):
            _LOG.debug("env file not readable: %s", path)
            continue
        try:
            parsed = _parse_dotenv(path)
        except Exception as exc:
            _LOG.warning("failed to parse %s: %s", path, exc)
            continue
        merged = _merge_into_environ(
            parsed, only_keys=only_keys, overwrite=overwrite,
        )
        _LOG.info(
            "loaded %d vars from %s (only_keys=%s, overwrite=%s)",
            merged, path,
            "all" if only_keys is None else f"{len(list(only_keys))} named",
            overwrite,
        )
        return merged
    if warn_missing:
        _LOG.warning(
            "no edulabs env file found in %s; "
            "API keys must be set another way",
            list(paths),
        )
    return 0


# Run on import so callers can simply do ``import scripts.load_edulabs_env``.
# Default is OFF — autoloading at import time pollutes pytest fixtures and
# any code that asserts on os.environ. Opt-in via:
#     TANK_AUTOLOAD_EDULABS_ENV=1 python3 -m tank_assistant.external_llm_client
# or from a ROS2 launch file:
#     import os
#     os.environ["TANK_AUTOLOAD_EDULABS_ENV"] = "1"
#     import scripts.load_edulabs_env   # noqa: F401
if os.environ.get("TANK_AUTOLOAD_EDULABS_ENV", "0") == "1":
    load_edulabs_env()


if __name__ == "__main__":
    # CLI mode — prints merged keys (names only, never values) and exits.
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    n = load_edulabs_env(overwrite=False, warn_missing=True)
    loaded_names = sorted(
        k for k in EDULABS_KEY_VARS if os.environ.get(k)
    )
    print(f"merged={n} loaded={loaded_names}")
    sys.exit(0)
