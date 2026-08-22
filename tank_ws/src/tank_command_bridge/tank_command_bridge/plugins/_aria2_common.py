"""aria2 JSON-RPC client for The Tank Project's plugin system.

Why stdlib-only (`urllib.request`)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
aria2 speaks JSON-RPC 1.0 (since 1.34) over plain HTTP POST. We *could*
slap ``requests`` on every plugin but that drags a TLS library into
rosdep and breaks the offline unit tests. Stdlib is enough.

RPC URL/token discovery
~~~~~~~~~~~~~~~~~~~~~~~
* URL: ``ARIA2_RPC_URL`` env var → default ``http://localhost:6800/jsonrpc``.
* Token: ``ARIA2_RPC_TOKEN`` env var (preferred).  Falls back to an
  empty string.  When the operator hasn't set one, we still work but
  emit a one-line warning to stderr so the operator can see why a
  hostile network could push jobs into their aria2 instance.

The token, when set, is passed as the **first** entry in the JSON-RPC
``params`` array per the aria2 protocol (positional secret), NOT as a
header or query-string parameter.

Options for addUri
~~~~~~~~~~~~~~~~~~~
`aria2.addUri` accepts ``[uri, options, position]`` positionally.  We
expose :func:`add_uri` with an optional ``options`` kwarg so callers
can pass filename / dir overrides without speaking JSON-RPC themselves.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


DEFAULT_RPC_URL = "http://localhost:6800/jsonrpc"
ENV_RPC_URL = "ARIA2_RPC_URL"
ENV_RPC_TOKEN = "ARIA2_RPC_TOKEN"

# Methods we actually use.  Centralised so downstream plugins can be
# checked against an allow-list.
_ALLOWED_METHODS = frozenset({
    "aria2.addUri",
    "aria2.tellStatus",
    "aria2.getGlobalStat",
    "aria2.removeDownloadResult",
})


@dataclass
class Aria2Result:
    success: bool
    data: Any
    error: Optional[str] = None
    elapsed_ms: float = 0.0


class Aria2Error(RuntimeError):
    """Raised when the RPC returns a JSON-RPC error or HTTP failure."""


def rpc(method: str,
        params: Optional[List[Any]] = None,
        token: Optional[str] = None,
        rpc_url: Optional[str] = None,
        timeout: float = 6.0) -> Any:
    """Call ``method`` over JSON-RPC.  Returns the ``result`` field.

    Raises :class:`Aria2Error` on HTTP / JSON-RPC error.
    """
    if method not in _ALLOWED_METHODS:
        raise Aria2Error(f"method {method!r} is not in the plugin allow-list")
    rpc_url = rpc_url or os.environ.get(ENV_RPC_URL, DEFAULT_RPC_URL)
    token = token if token is not None else os.environ.get(ENV_RPC_TOKEN, "")
    args: List[Any] = []
    if token:
        args.append(f"token:{token}")
    if params:
        args.extend(params)
    payload = json.dumps({
        "jsonrpc": "2.0",
        "id": f"tank-{int(time.time() * 1000)}",
        "method": method,
        "params": args,
    }).encode("utf-8")
    req = urllib.request.Request(
        rpc_url, data=payload,
        headers={"Content-Type": "application/json",
                 "Accept":       "application/json"},
    )
    started = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise Aria2Error(f"aria2 RPC {method!r} transport error: {exc}") from exc
    elapsed_ms = (time.time() - started) * 1000.0
    try:
        body = json.loads(raw)
    except ValueError as exc:
        raise Aria2Error(f"aria2 RPC {method!r} returned non-JSON: {exc}") from exc
    if "error" in body:
        raise Aria2Error(
            f"aria2 RPC {method!r} JSON-RPC error: {body['error']}"
        )
    return body.get("result"), elapsed_ms


def add_uri(uri: str,
            options: Optional[Dict[str, Any]] = None,
            token: Optional[str] = None,
            rpc_url: Optional[str] = None,
            timeout: float = 6.0) -> str:
    """Add a magnet / .torrent URL. Returns the aria2 gid.

    ``options`` is forwarded positionally as ``params[1]`` per the
    aria2 protocol — pass ``{"out": filename, "dir": directory}`` etc.

    Raises :class:`Aria2Error` on failure.
    """
    if not uri:
        raise Aria2Error("add_uri requires a non-empty uri")
    args: List[Any] = [uri]
    if options:
        args.append(options)
    res, _ = rpc("aria2.addUri", args,
                 token=token, rpc_url=rpc_url, timeout=timeout)
    if not isinstance(res, str) or not res:
        raise Aria2Error(f"addUri returned invalid gid: {res!r}")
    return res


def tell_status(gid: str,
                token: Optional[str] = None,
                rpc_url: Optional[str] = None,
                timeout: float = 6.0) -> Dict[str, Any]:
    """Return the most recent status dict for ``gid``."""
    if not gid:
        raise Aria2Error("tell_status requires a gid")
    # Pass an empty array for fields to get all fields.
    res, _ = rpc("aria2.tellStatus", [gid, []],
                 token=token, rpc_url=rpc_url, timeout=timeout)
    if not isinstance(res, dict):
        raise Aria2Error(f"tellStatus returned non-dict: {res!r}")
    return res


def global_stat(token: Optional[str] = None,
                rpc_url: Optional[str] = None,
                timeout: float = 4.0) -> Dict[str, Any]:
    """aira2 global stats; used as a health probe."""
    res, _ = rpc("aria2.getGlobalStat", [],
                 token=token, rpc_url=rpc_url, timeout=timeout)
    return res or {}


def warn_if_no_token() -> Optional[str]:
    """Helper for plugins — logs a one-shot warning to stderr.

    Returns the warning message if no token is configured, else ``None``.
    """
    if os.environ.get(ENV_RPC_TOKEN):
        return None
    msg = (
        f"WARNING: {ENV_RPC_TOKEN} is unset.  aria2 RPC at "
        f"{os.environ.get(ENV_RPC_URL, DEFAULT_RPC_URL)} accepts "
        f"unauthenticated calls.  Set {ENV_RPC_TOKEN} before exposing "
        "this control plane to an untrusted network."
    )
    if not getattr(warn_if_no_token, "_emitted", False):
        print(msg, file=sys.stderr)
        warn_if_no_token._emitted = True
    return msg
