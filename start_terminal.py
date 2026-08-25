#!/usr/bin/env python3
"""Start TankOS Terminal with local LLM provider registered.

Usage:
    python3 start_terminal.py                  # local-llama only
    python3 start_terminal.py --with-cloud     # also register cloud providers from env
"""
import os
import sys
from pathlib import Path

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

# Point local LLM provider to the actual models directory
os.environ["TANK_LOCAL_MODELS_DIR"] = str(PROJECT_ROOT / "models" / "llm")


def register_local_llama():
    """Register the local GGUF LLM provider."""
    from tank_os.core.ai_manager import AIManager
    from tank_os.core.local_llm_provider import LocalLlamaProvider

    ai = AIManager()
    provider = LocalLlamaProvider(
        models_dir=PROJECT_ROOT / "models" / "llm",
        n_ctx=2048,
        n_gpu_layers=0,  # CPU-only for now
        verbose=False,
    )
    # Pre-load the model
    print("🦙 Loading TinyLlama 1.1B GGUF model...")
    loaded = provider.ensure_loaded()
    if loaded:
        info = provider.model_info
        print(f"   ✅ Loaded: {info.name} ({info.size_mb:.0f} MB)")
    else:
        print(f"   ⚠️ Load failed: {provider._load_error}")
        print("   Falling back to local-stub provider")

    ai.register_provider("local-llama", provider, set_default=True)
    return loaded


def register_cloud_providers():
    """Register cloud LLM providers from environment variables."""
    from tank_os.core.ai_manager import AIManager
    import httpx

    ai = AIManager()
    registered = 0

    # OpenRouter (OpenAI-compatible)
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if key:
        try:
            from tank_ws.src.tank_assistant.tank_assistant.external_llm_client import OpenAIProvider
        except ImportError:
            # Fallback: create a simple OpenAI-compatible provider inline
            class OpenRouterProvider:
                name = "openrouter"
                def __init__(self, api_key):
                    self.api_key = api_key
                def chat(self, text, *, system_prompt=None, temperature=0.7, max_tokens=512, **kw):
                    r = httpx.Client(timeout=15).post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                        json={"model": "mistralai/mistral-7b-instruct", "messages": [
                            {"role": "system", "content": system_prompt or "You are TankOS AI assistant."},
                            {"role": "user", "content": text}
                        ], "max_tokens": max_tokens, "temperature": temperature}
                    )
                    r.raise_for_status()
                    return r.json()["choices"][0]["message"]["content"]
                def get_status(self):
                    return {"name": self.name, "available": True, "type": "openrouter", "model": "mistral-7b-instruct"}
            provider = OpenRouterProvider(key)
            ai.register_provider("openrouter", provider)
            registered += 1
            print("   🟢 openrouter (mistral-7b-instruct)")

    # Groq
    key = os.environ.get("GROQ_API_KEY", "")
    if key:
        class GroqProvider:
            name = "groq"
            def __init__(self, api_key):
                self.api_key = api_key
            def chat(self, text, *, system_prompt=None, temperature=0.7, max_tokens=512, **kw):
                r = httpx.Client(timeout=15).post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    json={"model": "llama-3.1-8b-instant", "messages": [
                        {"role": "system", "content": system_prompt or "You are TankOS AI assistant."},
                        {"role": "user", "content": text}
                    ], "max_tokens": max_tokens, "temperature": temperature}
                )
                r.raise_for_status()
                return r.json()["choices"][0]["message"]["content"]
            def get_status(self):
                return {"name": self.name, "available": True, "type": "groq", "model": "llama-3.1-8b-instant"}
        provider = GroqProvider(key)
        ai.register_provider("groq", provider)
        registered += 1
        print("   🟢 groq (llama-3.1-8b-instant)")

    # Gemini
    key = os.environ.get("GEMINI_API_KEY", "") or os.environ.get("GOOGLE_API_KEY", "")
    if key:
        class GeminiProvider:
            name = "gemini"
            def __init__(self, api_key):
                self.api_key = api_key
            def chat(self, text, *, system_prompt=None, temperature=0.7, max_tokens=512, **kw):
                body = {"contents": [{"parts": [{"text": text}]}]}
                if system_prompt:
                    body["systemInstruction"] = {"parts": [{"text": system_prompt}]}
                body["generationConfig"] = {"temperature": temperature, "maxOutputTokens": max_tokens}
                r = httpx.Client(timeout=15).post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={self.api_key}",
                    headers={"Content-Type": "application/json"}, json=body
                )
                r.raise_for_status()
                return r.json()["candidates"][0]["content"]["parts"][0]["text"]
            def get_status(self):
                return {"name": self.name, "available": True, "type": "gemini", "model": "gemini-2.0-flash"}
        provider = GeminiProvider(key)
        ai.register_provider("gemini", provider)
        registered += 1
        print("   🟢 gemini (gemini-2.0-flash)")

    return registered


def main():
    print()
    print("  ╔══════════════════════════════════════════════════════╗")
    print("  ║          🤖  TankOS AI Terminal v2.1              ║")
    print("  ║         Starting with LLM providers...            ║")
    print("  ╚══════════════════════════════════════════════════════╝")
    print()

    # Register local LLM
    local_ok = register_local_llama()

    # Optionally register cloud providers
    if "--with-cloud" in sys.argv:
        print("\n☁️  Registering cloud providers from env vars...")
        cloud_count = register_cloud_providers()
        if cloud_count == 0:
            print("   (no API keys found — set OPENROUTER_API_KEY, GROQ_API_KEY, or GEMINI_API_KEY)")
    else:
        print("\n💡 Tip: Use --with-cloud to also register cloud LLM providers")
        print("   Set env vars: OPENROUTER_API_KEY, GROQ_API_KEY, GEMINI_API_KEY")

    # Show provider summary
    from tank_os.core.ai_manager import AIManager
    ai = AIManager()
    providers = ai.list_providers()
    online = sum(1 for p in providers if p.get("available"))
    print(f"\n📊 Providers: {online}/{len(providers)} online (default: {ai.default_provider})")

    # Initialize evolution bridge
    try:
        from tank_os.core.evolution_bridge import init_evolution_providers
        n = init_evolution_providers(
            discover_models=True,
            register_local=True,
            register_rotation=True,
            set_rotation_default=True,
        )
        print(f"🧬 Evolution: {n} providers registered")
    except (ImportError, Exception) as e:
        print(f"🧬 Evolution: not available ({e})")

    print()

    # Launch the REPL
    from tank_os.shell.terminal.engine import SubprocessExecutor, TerminalEngine
    from tank_os.shell.terminal.cli import TerminalREPL

    engine = TerminalEngine(
        executor_factory=SubprocessExecutor,
        default_timeout_s=15.0,
    )
    repl = TerminalREPL(engine=engine)

    # Pre-load tool registry
    try:
        reg = repl._get_registry()
        if reg:
            tools = reg.list()
            cats = reg.categories()
            print(f"📦 Tools: {len(tools)} tools in {len(cats)} categories")
    except Exception:
        pass

    print()
    repl.cmdloop()


if __name__ == "__main__":
    main()
