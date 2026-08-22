#!/usr/bin/env python3
"""The Tank Project — crypto CLI.

Hosts 3 features (F137-F139):

* ``secrets-rotate``   — write a new random secret to the env file
* ``jwt-issue``        — generate a short-lived JWT (HS256)
* ``hash-bench``       — benchmark sha256 / sha512 / blake2b
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import secrets
import sys
import time
from base64 import urlsafe_b64encode
from pathlib import Path



LOG_PREFIX = "[crypto]"


def _log(msg: str) -> None:
    print(f"{LOG_PREFIX} {msg}", flush=True)


def _ok(msg: str) -> None:
    print(f"{LOG_PREFIX} OK   {msg}", flush=True)


def _err(msg: str) -> None:
    print(f"{LOG_PREFIX} FAIL {msg}", file=sys.stderr, flush=True)


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# F137 — secrets-rotate
# ---------------------------------------------------------------------------
def cmd_secrets_rotate(args: argparse.Namespace) -> int:
    """F137 — secrets rotate."""
    n_bytes = max(16, args.length // 2)
    secret = secrets.token_urlsafe(n_bytes)
    target = _repo_root() / "secrets" / f"{args.key}"
    target.parent.mkdir(parents=True, exist_ok=True)
    if args.apply:
        target.write_text(secret)
        target.chmod(0o600)
        _ok(f"wrote {target} ({args.length} bits)")
    else:
        _log(f"DRY: candidate for {args.key}: {secret[:8]}...")
    return 0


# ---------------------------------------------------------------------------
# F138 — jwt-issue
# ---------------------------------------------------------------------------
def _b64(b: bytes) -> str:
    return urlsafe_b64encode(b).rstrip(b"=").decode("ascii")


def cmd_jwt_issue(args: argparse.Namespace) -> int:
    """F138 — JWT issue."""
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    payload = {"sub": args.sub, "iat": now,
               "exp": now + args.ttl, "scope": args.scope}
    signing_input = (_b64(json.dumps(header, separators=(",", ":")).encode())
                     + "."
                     + _b64(json.dumps(payload, separators=(",", ":")).encode()))
    sig = hmac.new(args.secret.encode(),
                   signing_input.encode(),
                   hashlib.sha256).digest()
    token = signing_input + "." + _b64(sig)
    _ok(token)
    return 0


# ---------------------------------------------------------------------------
# F139 — hash-bench
# ---------------------------------------------------------------------------
def cmd_hash_bench(args: argparse.Namespace) -> int:
    """F139 — hash benchmark."""
    blob = secrets.token_bytes(8 * 1024)
    algos = [a.strip() for a in args.algo.split(",")]
    out = []
    for alg in algos:
        try:
            h = hashlib.new(alg)
        except ValueError as exc:
            out.append({"algo": alg, "error": str(exc)})
            continue
        t0 = time.perf_counter()
        for _ in range(args.iters):
            h.update(blob)
            h.hexdigest()
        elapsed = time.perf_counter() - t0
        rate = args.iters * len(blob) / max(elapsed, 1e-9)
        out.append({
            "algo":     alg,
            "iters":    args.iters,
            "elapsed_s": round(elapsed, 4),
            "rate_B_s":  int(rate),
        })
    _ok(json.dumps(out, indent=2))
    return 0


# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Crypto CLI (F137-F139).")
    sub = p.add_subparsers(dest="cmd", required=True)
    pr = sub.add_parser("secrets-rotate", help="F137 — secrets rotate")
    pr.add_argument("--key", default="tank_api_key")
    pr.add_argument("--length", type=int, default=32)
    pr.add_argument("--apply", action="store_true")
    pj = sub.add_parser("jwt-issue", help="F138 — JWT issue")
    pj.add_argument("--sub", required=True)
    pj.add_argument("--ttl", type=int, default=3600)
    pj.add_argument("--scope", default="read")
    pj.add_argument("--secret", default="dev-secret-please-change")
    ph = sub.add_parser("hash-bench", help="F139 — hash benchmark")
    ph.add_argument("--algo", default="sha256,sha512,blake2b,md5")
    ph.add_argument("--iters", type=int, default=200)
    return p


HANDLERS = {
    "secrets-rotate": cmd_secrets_rotate,
    "jwt-issue":      cmd_jwt_issue,
    "hash-bench":     cmd_hash_bench,
}


def main(argv: Optional[list] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return HANDLERS[args.cmd](args)
    except KeyboardInterrupt:
        _err("interrupted")
        return 130


if __name__ == "__main__":
    sys.exit(main())
