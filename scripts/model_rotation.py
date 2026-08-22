#!/usr/bin/env python3
"""🔄 Model Rotation — cycle through healthy providers and test each one.

Usage
-----
    python3 scripts/model_rotation.py
    python3 scripts/model_rotation.py --prompt "Explain quantum computing briefly"
    python3 scripts/model_rotation.py --max-attempts 12
    python3 scripts/model_rotation.py --mode single --provider groq
    python3 scripts/model_rotation.py --discover-first  # auto-discover models first

The script:
1. Optionally runs the auto-finder to discover current models
2. Walks the provider priority list (cheap/fast first)
3. Tests each provider with a simple prompt
4. Tracks circuit breaker state (healthy → degraded → dead → cooldown)
5. Reports which provider "won" and why
6. Logs the full rotation state at the end
"""
from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(os.environ.get(
    "TANK_PROJECT_ROOT",
    "/root/the tank project",
))
TANK_WS_SRC = PROJECT_ROOT / "tank_ws" / "src"
if str(TANK_WS_SRC) not in sys.path:
    sys.path.insert(0, str(TANK_WS_SRC))

try:
    import httpx  # type: ignore
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False
    print("❌ httpx is required. Run: pip install httpx --break-system-packages")
    sys.exit(1)


# ── ANSI colours ─────────────────────────────────────────────────────────────

class C:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"


# ── Data types ───────────────────────────────────────────────────────────────

@dataclass
class CircuitBreaker:
    """Per-provider circuit breaker state machine."""
    name: str
    state: str = "HEALTHY"          # HEALTHY | DEGRADED | DEAD
    failures: int = 0
    successes: int = 0
    last_failure_at: float = 0.0
    last_state_change_at: float = field(default_factory=time.monotonic)
    degraded_cooldown_s: float = 30.0
    dead_cooldown_s: float = 300.0
    failure_threshold: int = 3

    def can_attempt(self) -> bool:
        now = time.monotonic()
        if self.state == "HEALTHY":
            return True
        elapsed = now - self.last_state_change_at
        return elapsed >= (self.dead_cooldown_s if self.state == "DEAD"
                           else self.degraded_cooldown_s)

    def record_success(self) -> None:
        self.successes += 1
        if self.state in ("DEGRADED", "DEAD"):
            if self.state == "DEAD" or self.successes >= 2:
                self.state = "HEALTHY"
                self.failures = 0
                self.last_state_change_at = time.monotonic()

    def record_failure(self) -> None:
        self.failures += 1
        self.successes = 0
        self.last_failure_at = time.monotonic()
        if self.state == "HEALTHY":
            self.state = "DEGRADED"
            self.last_state_change_at = time.monotonic()
        elif self.state == "DEGRADED" and self.failures >= self.failure_threshold:
            self.state = "DEAD"
            self.last_state_change_at = time.monotonic()
        elif self.state == "DEAD":
            self.last_state_change_at = time.monotonic() - self.dead_cooldown_s + 1

    @property
    def status_icon(self) -> str:
        return {"HEALTHY": "🟢", "DEGRADED": "🟡", "DEAD": "🔴"}.get(self.state, "⚪")


@dataclass
class RotationResult:
    """Result of a single rotation cycle."""
    provider: str
    model: str
    status: str                    # SUCCESS | FAILED | SKIPPED
    response: str = ""
    error: str = ""
    duration_s: float = 0.0
    latency_p95_ms: float = 0.0


# ── Provider config registry ────────────────────────────────────────────────

PROVIDER_PRIORITY = [
    "groq", "cerebras", "openrouter", "deepseek", "mistral",
    "cohere", "cloudflare", "gemini", "replicate", "huggingface",
    "endpointai",
]

PROVIDER_CONFIGS: Dict[str, Dict[str, Any]] = {
    "groq": {
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "env_key": "GROQ_API_KEY",
        "auth_type": "Bearer",
        "format": "openai",
    },
    "cerebras": {
        "url": "https://api.cerebras.ai/v1/chat/completions",
        "env_key": "CEREBRAS_API_KEY",
        "auth_type": "Bearer",
        "format": "openai",
    },
    "openrouter": {
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "env_key": "OPENROUTER_API_KEY",
        "auth_type": "Bearer",
        "format": "openai",
    },
    "deepseek": {
        "url": "https://api.deepseek.com/v1/chat/completions",
        "env_key": "DEEPSEEK_API_KEY",
        "auth_type": "Bearer",
        "format": "openai",
    },
    "mistral": {
        "url": "https://api.mistral.ai/v1/chat/completions",
        "env_key": "MISTRAL_API_KEY",
        "auth_type": "Bearer",
        "format": "openai",
    },
    "cohere": {
        "url": "https://api.cohere.ai/v1/chat",
        "env_key": "COHERE_API_KEY",
        "auth_type": "Bearer",
        "format": "cohere",
    },
    "cloudflare": {
        "url": "",
        "env_key": "CLOUDFLARE_WORKER_API_KEY",
        "auth_type": "Bearer",
        "format": "cloudflare",
    },
    "gemini": {
        "url": "https://generativelanguage.googleapis.com/v1beta",
        "env_key": "GEMINI_API_KEY",
        "auth_type": "Key",
        "format": "gemini",
    },
    "replicate": {
        "url": "https://api.replicate.com/v1/chat/completions",
        "env_key": "REPLICATE_API_KEY",
        "auth_type": "Token",
        "format": "openai",
    },
    "huggingface": {
        "url": "https://api-inference.huggingface.co/models",
        "env_key": "HUGGINGFACE_API_KEY",
        "auth_type": "Bearer",
        "format": "huggingface",
    },
    "endpointai": {
        "url": "",
        "env_key": "ENDPOINT_AI_API_KEY",
        "auth_type": "Bearer",
        "format": "endpointai",
    },
}

# Known working models per provider (can be overridden by --models)
DEFAULT_MODELS: Dict[str, List[str]] = {
    "groq": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "qwen/qwen3.6-27b"],
    "cerebras": ["gpt-oss-120b", "gemma-4-31b", "zai-glm-4.7"],
    "openrouter": ["openai/gpt-4o-mini", "google/gemini-3.6-flash", "deepseek/deepseek-chat"],
    "deepseek": ["deepseek-chat", "deepseek-reasoner"],
    "mistral": ["mistral-large-latest", "mistral-small-latest", "mistral-medium-2505"],
    "cohere": ["command-r-plus-08-2024", "command-r-08-2024", "command-r7b-12-2024"],
    "cloudflare": ["@cf/meta/llama-3.1-8b-instruct", "@cf/meta/llama-3.3-70b-instruct-fp8-fast"],
    "gemini": ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-1.5-flash"],
    "replicate": ["meta/meta-llama-3.3-70b-instruct"],
    "huggingface": ["Qwen/Qwen2.5-Coder-0.5B-Instruct", "microsoft/Phi-3-mini-4k-instruct"],
    "endpointai": ["deepseek-r1:70b"],
}


# ── Key loader ──────────────────────────────────────────────────────────────

def load_api_keys() -> None:
    """Load API keys from worker.env into os.environ."""
    env_paths = [
        Path("/etc/edulabs-thesis-worker/worker.env"),
        PROJECT_ROOT / ".env",
    ]
    for env_file in env_paths:
        if not env_file.exists():
            continue
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, _, v = line.partition("=")
                k = k.strip()
                v = v.strip().strip("'\"").strip("\"")
                if k and v:
                    os.environ.setdefault(k, v)


def get_key(name: str) -> str:
    """Get an API key from env (already loaded)."""
    return os.environ.get(name, "")


# ── Provider callers ────────────────────────────────────────────────────────

def call_openai_style(provider: str, cfg: Dict[str, Any], model: str, prompt: str,
                      client: httpx.Client, timeout: float) -> Tuple[int, str]:
    """Call an OpenAI-shaped chat completions endpoint."""
    headers = _auth_headers(cfg)
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 60,
        "temperature": 0.1,
    }
    if provider == "openrouter":
        headers["HTTP-Referer"] = "https://tank.local"
    r = client.post(cfg["url"], json=body, headers=headers, timeout=timeout)
    if r.status_code == 200:
        text = r.json().get("choices", [{}])[0].get("message", {}).get("content", "")
        return 200, text.strip()
    return r.status_code, r.text[:200]


def call_cohere(provider: str, cfg: Dict[str, Any], model: str, prompt: str,
                client: httpx.Client, timeout: float) -> Tuple[int, str]:
    """Call Cohere chat API."""
    headers = _auth_headers(cfg)
    body = {"model": model, "message": prompt, "max_tokens": 60}
    r = client.post(cfg["url"], json=body, headers=headers, timeout=timeout)
    if r.status_code == 200:
        return 200, r.json().get("text", "").strip()
    return r.status_code, r.text[:200]


def call_gemini(provider: str, cfg: Dict[str, Any], model: str, prompt: str,
                client: httpx.Client, timeout: float) -> Tuple[int, str]:
    """Call Gemini generateContent API."""
    key = get_key("GEMINI_API_KEY")
    url = f"{cfg['url']}/models/{model}:generateContent?key={key}"
    body = {"contents": [{"parts": [{"text": prompt}]}]}
    r = client.post(url, json=body, headers={"Content-Type": "application/json"},
                    timeout=timeout)
    if r.status_code == 200:
        data = r.json()
        text = ""
        for cand in data.get("candidates", []):
            for part in cand.get("content", {}).get("parts", []):
                text += part.get("text", "")
        return 200, text.strip()
    return r.status_code, r.text[:200]


def call_cloudflare(provider: str, cfg: Dict[str, Any], model: str, prompt: str,
                    client: httpx.Client, timeout: float) -> Tuple[int, str]:
    """Call Cloudflare Workers AI."""
    account_id = get_key("CLOUDFLARE_ACCOUNT_ID")
    if not account_id:
        return 0, "No CLOUDFLARE_ACCOUNT_ID set"
    url = (f"https://api.cloudflare.com/client/v4/accounts/"
           f"{account_id}/ai/run/{model}")
    headers = {"Authorization": f"Bearer {get_key('CLOUDFLARE_WORKER_API_KEY')}",
               "Content-Type": "application/json"}
    body = {"messages": [{"role": "user", "content": prompt}], "max_tokens": 60}
    r = client.post(url, json=body, headers=headers, timeout=timeout)
    if r.status_code == 200:
        return 200, r.json().get("result", {}).get("response", "").strip()
    return r.status_code, r.text[:200]


def call_huggingface(provider: str, cfg: Dict[str, Any], model: str, prompt: str,
                     client: httpx.Client, timeout: float) -> Tuple[int, str]:
    """Call HuggingFace Inference API."""
    headers = {"Authorization": f"Bearer {get_key('HUGGINGFACE_API_KEY')}",
               "Content-Type": "application/json"}
    url = f"{cfg['url']}/{model}/v1/chat/completions"
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 60,
    }
    r = client.post(url, json=body, headers=headers, timeout=timeout)
    if r.status_code == 200:
        text = r.json().get("choices", [{}])[0].get("message", {}).get("content", "")
        return 200, text.strip()
    return r.status_code, r.text[:200]


def call_endpoint_ai(provider: str, cfg: Dict[str, Any], model: str, prompt: str,
                     client: httpx.Client, timeout: float) -> Tuple[int, str]:
    """Call EndpointAI (arbitrary OpenAI-shaped endpoint)."""
    base = get_key("ENDPOINT_AI_BASE_URL") or "https://endpointai-backend-production.up.railway.app/"
    headers = {"Authorization": f"Bearer {get_key('ENDPOINT_AI_API_KEY')}",
               "Content-Type": "application/json"}
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 60,
    }
    cfg["url"] = f"{base.rstrip('/')}/v1/chat/completions"
    r = client.post(cfg["url"], json=body, headers=headers, timeout=timeout)
    if r.status_code == 200:
        text = r.json().get("choices", [{}])[0].get("message", {}).get("content", "")
        return 200, text.strip()
    return r.status_code, r.text[:200]


CALLBACKS = {
    "openai": call_openai_style,
    "cohere": call_cohere,
    "gemini": call_gemini,
    "cloudflare": call_cloudflare,
    "huggingface": call_huggingface,
    "endpointai": call_endpoint_ai,
}


def _auth_headers(cfg: Dict[str, Any]) -> Dict[str, str]:
    key = get_key(cfg["env_key"])
    if cfg["auth_type"] == "Token":
        return {"Authorization": f"Token {key}", "Content-Type": "application/json"}
    return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}


# ── Rotation engine ─────────────────────────────────────────────────────────

class RotationEngine:
    """Cycles through providers testing each one."""

    def __init__(self, prompt: str = "Reply with just the word: hello",
                 max_attempts: int = 20,
                 providers: Optional[List[str]] = None,
                 timeout: float = 15.0) -> None:
        self.prompt = prompt
        self.max_attempts = max_attempts
        self.providers = providers or PROVIDER_PRIORITY
        self.timeout = timeout
        self.breakers: Dict[str, CircuitBreaker] = {}
        self.client = httpx.Client(timeout=timeout)
        self.results: List[RotationResult] = []

    def run(self) -> Dict[str, Any]:
        """Run a full rotation cycle.

        Returns a summary dict with the winning provider and all attempts.
        """
        print(f"\n  {C.BOLD}🔄 Rotation Cycle — {len(self.providers)} providers{ C.RESET}")
        print(f"  {C.DIM}Prompt: \"{self.prompt}\"{ C.RESET}")
        print(f"  {C.DIM}{'─' * 60}{C.RESET}\n")

        attempts = 0
        winner = None

        for provider in self.providers:
            if attempts >= self.max_attempts:
                break

            cfg = PROVIDER_CONFIGS.get(provider)
            if not cfg:
                continue

            key = get_key(cfg["env_key"])
            if not key:
                self._log_skip(provider, "no API key configured")
                continue
            if provider == "cloudflare" and not get_key("CLOUDFLARE_ACCOUNT_ID"):
                self._log_skip(provider, "no CLOUDFLARE_ACCOUNT_ID")
                continue

            breaker = self._get_breaker(provider)
            if not breaker.can_attempt():
                self._log_skip(provider, f"circuit breaker {breaker.state} "
                               f"(cooldown {breaker.last_state_change_at + self._cooldown_remaining(breaker):.0f}s)")
                continue

            models = DEFAULT_MODELS.get(provider, [])
            if not models:
                self._log_skip(provider, "no models configured")
                continue

            for model in models:
                if attempts >= self.max_attempts:
                    break

                result = self._test_provider(provider, model, cfg)
                self.results.append(result)
                attempts += 1

                if result.status == "SUCCESS":
                    breaker.record_success()
                    winner = result
                    self._log_result(result)
                    print(f"\n  {C.GREEN}{C.BOLD}✅ WINNER: {result.provider}/{result.model}{C.RESET}")
                    print(f"  {C.DIM}Response ({result.duration_s:.1f}s): "
                          f"{result.response[:60]}{C.RESET}")
                    self.client.close()
                    return self._summary(winner)

                elif result.status == "FAILED":
                    breaker.record_failure()
                    self._log_result(result)
                    # Continue to next model/provider

        self.client.close()

        if winner:
            return self._summary(winner)

        print(f"\n  {C.RED}{C.BOLD}✘ No working provider found{C.RESET}")
        return self._summary(None)

    def _test_provider(self, provider: str, model: str,
                       cfg: Dict[str, Any]) -> RotationResult:
        """Test a single provider + model combination."""
        start = time.monotonic()
        result = RotationResult(provider=provider, model=model, status="FAILED")

        try:
            callback = CALLBACKS.get(cfg.get("format", "openai"), call_openai_style)
            status_code, text = callback(provider, cfg, model, self.prompt,
                                         self.client, self.timeout)
            result.duration_s = time.monotonic() - start

            if status_code == 200 and text.strip():
                result.status = "SUCCESS"
                result.response = text.strip()
                result.latency_p95_ms = round(result.duration_s * 1000, 1)
            elif status_code == 429:
                result.error = "Rate limited (HTTP 429)"
            elif status_code == 401:
                result.error = "Unauthorized (HTTP 401)"
            elif status_code == 402:
                result.error = "Payment required (HTTP 402)"
            elif status_code == 404:
                result.error = f"Not found (HTTP 404): {text[:80]}"
            elif status_code == 422:
                result.error = f"Payload error (HTTP 422): {text[:80]}"
            elif status_code >= 500:
                result.error = f"Server error (HTTP {status_code})"
            elif status_code == 0:
                result.error = text  # custom error message
            else:
                result.error = f"HTTP {status_code}: {text[:80]}"
        except httpx.ConnectError as e:
            result.error = f"Connection failed: {e}"
            result.duration_s = time.monotonic() - start
        except httpx.TimeoutException:
            result.error = f"Timeout ({self.timeout}s)"
            result.duration_s = self.timeout
        except Exception as e:
            result.error = f"{type(e).__name__}: {str(e)[:100]}"
            result.duration_s = time.monotonic() - start

        return result

    def _get_breaker(self, name: str) -> CircuitBreaker:
        if name not in self.breakers:
            self.breakers[name] = CircuitBreaker(name=name)
        return self.breakers[name]

    def _cooldown_remaining(self, breaker: CircuitBreaker) -> float:
        now = time.monotonic()
        if breaker.state == "DEGRADED":
            return max(0, breaker.degraded_cooldown_s - (now - breaker.last_state_change_at))
        if breaker.state == "DEAD":
            return max(0, breaker.dead_cooldown_s - (now - breaker.last_state_change_at))
        return 0

    def _log_result(self, result: RotationResult) -> None:
        breaker = self._get_breaker(result.provider)
        icon = "✅" if result.status == "SUCCESS" else "❌"
        elapsed = f"{result.duration_s:.1f}s"
        detail = result.response[:50] if result.status == "SUCCESS" else result.error
        print(f"  {icon} {result.provider:12s}/{result.model:30s} "
              f"{elapsed:6s}  {C.DIM}{detail}{C.RESET}")

    def _log_skip(self, provider: str, reason: str) -> None:
        print(f"  ⏭  {provider:12s}  {C.DIM}{reason}{C.RESET}")

    def _summary(self, winner: Optional[RotationResult]) -> Dict[str, Any]:
        """Build the final rotation summary."""
        summary: Dict[str, Any] = {
            "winner": {
                "provider": winner.provider,
                "model": winner.model,
                "response": winner.response[:100],
                "latency_s": round(winner.duration_s, 2),
            } if winner else None,
            "total_attempts": len(self.results),
            "successes": sum(1 for r in self.results if r.status == "SUCCESS"),
            "failures": sum(1 for r in self.results if r.status == "FAILED"),
            "skips": sum(1 for r in self.results if r.status == "SKIPPED"),
            "circuit_breakers": {
                name: {
                    "state": b.state,
                    "failures": b.failures,
                    "successes": b.successes,
                }
                for name, b in sorted(self.breakers.items())
            },
        }
        return summary


# ── CLI ──────────────────────────────────────────────────────────────────────

def parse_args(argv: List[str]) -> Dict[str, Any]:
    args: Dict[str, Any] = {
        "prompt": "Reply with just the word: hello",
        "max_attempts": 20,
        "providers": None,
        "mode": "auto",
        "timeout": 15.0,
        "discover_first": False,
    }
    i = 0
    while i < len(argv):
        if argv[i] == "--prompt" and i + 1 < len(argv):
            args["prompt"] = argv[i + 1]
            i += 1
        elif argv[i] == "--max-attempts" and i + 1 < len(argv):
            args["max_attempts"] = int(argv[i + 1])
            i += 1
        elif argv[i] == "--providers" and i + 1 < len(argv):
            args["providers"] = [p.strip() for p in argv[i + 1].split(",")]
            i += 1
        elif argv[i] == "--mode" and i + 1 < len(argv):
            args["mode"] = argv[i + 1]
            i += 1
        elif argv[i] == "--timeout" and i + 1 < len(argv):
            args["timeout"] = float(argv[i + 1])
            i += 1
        elif argv[i] == "--discover-first":
            args["discover_first"] = True
        elif argv[i] in ("-h", "--help"):
            print(__doc__)
            sys.exit(0)
        i += 1
    return args


def main(argv: List[str]) -> int:
    args = parse_args(argv[1:] if argv else [])

    print()
    print(f"{C.BOLD}{'=' * 72}{C.RESET}")
    print(f"{C.CYAN}{C.BOLD}  🔄 Model Rotation Tester{C.RESET}")
    print(f"{C.BOLD}{'=' * 72}{C.RESET}")

    # Load API keys
    load_api_keys()

    # Check configured providers
    available = []
    for p in (args["providers"] or PROVIDER_PRIORITY):
        cfg = PROVIDER_CONFIGS.get(p)
        if cfg:
            key = get_key(cfg["env_key"])
            if key:
                available.append(p)
    print(f"\n  {C.BOLD}Configured providers:{C.RESET} {', '.join(available) or C.RED + 'none' + C.RESET}")
    print(f"  {C.BOLD}Total:{C.RESET} {len(available)}")
    print()

    # Run rotation
    engine = RotationEngine(
        prompt=args["prompt"],
        max_attempts=args["max_attempts"],
        providers=args["providers"],
        timeout=args["timeout"],
    )

    # Optionally run auto-finder first
    if args["discover_first"]:
        print(f"  {C.DIM}Running auto-finder to discover current models...{C.RESET}")
        try:
            from tank_assistant.evolution.model_discovery import model_discoverer
            catalog = model_discoverer.discover_all(force=True)
            for name, result in catalog.items():
                if result.models:
                    DEFAULT_MODELS[name] = result.models[:6]
                    print(f"  {C.GREEN}✔{C.RESET} {name}: {len(result.models)} models discovered")
        except Exception as e:
            print(f"  {C.YELLOW}⚠  Auto-finder failed: {e}{C.RESET}")

    summary = engine.run()

    # Print summary
    print()
    print(f"{C.BOLD}{'=' * 72}{C.RESET}")
    print(f"{C.BOLD}  📊 ROTATION SUMMARY{C.RESET}")
    print(f"{C.BOLD}{'=' * 72}{C.RESET}")
    print()

    if summary.get("winner"):
        w = summary["winner"]
        print(f"  {C.GREEN}🏆 Winner:{C.RESET}       {w['provider']}/{w['model']}")
        print(f"  {C.GREEN}Response:{C.RESET}       {w['response'][:60]}...")
        print(f"  {C.GREEN}Latency:{C.RESET}         {w['latency_s']:.2f}s")
    else:
        print(f"  {C.RED}🏆 Winner:{C.RESET}       {C.RED}NONE{C.RESET}")

    print(f"  {'Attempts:':19s} {summary['total_attempts']}")
    print(f"  {C.GREEN}  Successes:{C.RESET}       {summary['successes']}")
    print(f"  {C.RED}  Failures:{C.RESET}         {summary['failures']}")
    print(f"  {'Skips:':19s} {summary['skips']}")
    print()

    # Circuit breaker state
    print(f"  {C.BOLD}Circuit Breaker State:{C.RESET}")
    for name, cb in sorted(summary.get("circuit_breakers", {}).items()):
        icon = {"HEALTHY": "🟢", "DEGRADED": "🟡", "DEAD": "🔴"}.get(cb["state"], "⚪")
        print(f"  {icon} {name:15s} {cb['state']:10s} "
              f"(fails: {cb['failures']}, successes: {cb['successes']})")
    print()
    print(f"{C.DIM}{'=' * 72}{C.RESET}")
    print()

    return 0 if summary.get("winner") else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
