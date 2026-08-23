"""
evolution_key_manager.py - API Key Discovery & Evolution System
During each evolution cycle, discovers missing API keys and prompts user to add them.
Sends SMS/Telegram notifications with setup links.
"""
import os
import json
import time
import logging
import subprocess
import urllib.request
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("tank.evolution.keys")

# All supported providers with setup URLs and free tier info
PROVIDER_REGISTRY = [
    {
        "id": "openrouter",
        "name": "OpenRouter",
        "env_key": "OPENROUTER_API_KEY",
        "setup_url": "https://openrouter.ai/keys",
        "free_tier": "$5 credit, multi-model gateway",
        "models": ["gpt-4o", "claude-3.5-sonnet", "llama-3.1-70b", "mistral-large"],
        "priority": 1,
        "speed_ms": 500,
        "test_prompt": "Say hello in 5 words",
    },
    {
        "id": "groq",
        "name": "Groq",
        "env_key": "GROQ_API_KEY",
        "setup_url": "https://console.groq.com/keys",
        "free_tier": "Unlimited Llama/Mixtral, 30 RPM",
        "models": ["llama-3.1-8b", "mixtral-8x7b", "gemma2-9b"],
        "priority": 2,
        "speed_ms": 200,
        "test_prompt": "Say hello in 5 words",
    },
    {
        "id": "gemini",
        "name": "Google Gemini",
        "env_key": "GEMINI_API_KEY",
        "setup_url": "https://aistudio.google.com/apikey",
        "free_tier": "15 RPM Gemini Flash",
        "models": ["gemini-1.5-flash", "gemini-1.5-pro"],
        "priority": 3,
        "speed_ms": 300,
        "test_prompt": "Say hello in 5 words",
    },
    {
        "id": "mistral",
        "name": "Mistral AI",
        "env_key": "MISTRAL_API_KEY",
        "setup_url": "https://console.mistral.ai/api-keys",
        "free_tier": "1 RPM Mistral Small",
        "models": ["mistral-small", "mistral-medium"],
        "priority": 4,
        "speed_ms": 400,
        "test_prompt": "Say hello in 5 words",
    },
    {
        "id": "cerebras",
        "name": "Cerebras",
        "env_key": "CEREBRAS_API_KEY",
        "setup_url": "https://cloud.cerebras.ai/api-keys",
        "free_tier": "30 RPM Llama 3.1 8B, fastest inference",
        "models": ["llama-3.1-8b"],
        "priority": 5,
        "speed_ms": 100,
        "test_prompt": "Say hello in 5 words",
    },
    {
        "id": "cohere",
        "name": "Cohere",
        "env_key": "COHERE_API_KEY",
        "setup_url": "https://dashboard.cohere.com/api-keys",
        "free_tier": "1000 RPM Command R",
        "models": ["command-r", "command-r-plus"],
        "priority": 6,
        "speed_ms": 350,
        "test_prompt": "Say hello in 5 words",
    },
    {
        "id": "replicate",
        "name": "Replicate",
        "env_key": "REPLICATE_API_KEY",
        "setup_url": "https://replicate.com/account/api-tokens",
        "free_tier": "$5 credit, open-source models",
        "models": ["llama-3.1-8b", "stable-diffusion"],
        "priority": 7,
        "speed_ms": 800,
        "test_prompt": "Say hello in 5 words",
    },
    {
        "id": "huggingface",
        "name": "Hugging Face",
        "env_key": "HUGGINGFACE_API_KEY",
        "setup_url": "https://huggingface.co/settings/tokens",
        "free_tier": "30K chars/month inference API",
        "models": ["llama-3.1-8b", "falcon-7b"],
        "priority": 8,
        "speed_ms": 600,
        "test_prompt": "Say hello in 5 words",
    },
    {
        "id": "cloudflare",
        "name": "Cloudflare Workers AI",
        "env_key": "CLOUDFLARE_WORKER_API_KEY",
        "setup_url": "https://dash.cloudflare.com/profile/api-tokens",
        "free_tier": "10K requests/day, edge AI",
        "models": ["llama-3.1-8b", "stable-diffusion"],
        "priority": 9,
        "speed_ms": 250,
        "test_prompt": "Say hello in 5 words",
    },
    # Optional advanced providers
    {
        "id": "openai",
        "name": "OpenAI",
        "env_key": "OPENAI_API_KEY",
        "setup_url": "https://platform.openai.com/api-keys",
        "free_tier": "$5 credit",
        "models": ["gpt-4o", "gpt-4o-mini", "dall-e-3"],
        "priority": 10,
        "speed_ms": 400,
        "optional": True,
        "test_prompt": "Say hello in 5 words",
    },
    {
        "id": "anthropic",
        "name": "Anthropic",
        "env_key": "ANTHROPIC_API_KEY",
        "setup_url": "https://console.anthropic.com/api-keys",
        "free_tier": "$5 credit",
        "models": ["claude-3.5-sonnet", "claude-3-haiku"],
        "priority": 11,
        "speed_ms": 450,
        "optional": True,
        "test_prompt": "Say hello in 5 words",
    },
    {
        "id": "together",
        "name": "Together AI",
        "env_key": "TOGETHER_API_KEY",
        "setup_url": "https://api.together.xyz/settings/api-keys",
        "free_tier": "$5 credit",
        "models": ["llama-3.1-70b", "mixtral-8x22b"],
        "priority": 12,
        "speed_ms": 500,
        "optional": True,
        "test_prompt": "Say hello in 5 words",
    },
    {
        "id": "deepinfra",
        "name": "DeepInfra",
        "env_key": "DEEPINFRA_API_KEY",
        "setup_url": "https://deepinfra.com/dash/api_keys",
        "free_tier": "$5 credit",
        "models": ["llama-3.1-70b", "mistral-7b"],
        "priority": 13,
        "speed_ms": 550,
        "optional": True,
        "test_prompt": "Say hello in 5 words",
    },
    {
        "id": "sambanova",
        "name": "SambaNova",
        "env_key": "SAMBANOVA_API_KEY",
        "setup_url": "https://cloud.sambanova.ai/apis",
        "free_tier": "Unlimited Llama 3 8B",
        "models": ["llama-3.1-8b", "llama-3.1-70b"],
        "priority": 14,
        "speed_ms": 300,
        "optional": True,
        "test_prompt": "Say hello in 5 words",
    },
]

# Notification providers
TELEGRAM_TOKEN = os.environ.get("TANK_TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TANK_TELEGRAM_CHAT_ID", "")
SMS_NUMBER = os.environ.get("TANK_EVOLUTION_SMS_NUMBER", "+917860245819")


class EvolutionKeyManager:
    """Discovers missing API keys and prompts user to add them"""

    def __init__(self, env_file=".env", keys_file=".env.keys"):
        self.env_file = Path(env_file)
        self.keys_file = Path(keys_file)
        self.loaded_keys = {}
        self.missing_keys = []
        self.tested_providers = []
        self.evolution_log = []
        self._load_keys()

    def _load_keys(self):
        """Load all keys from .env and .env.keys"""
        for f in [self.keys_file, self.env_file]:
            if f.exists():
                for line in f.read_text().splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, _, val = line.partition("=")
                        key = key.strip()
                        val = val.strip()
                        if val and val != "your-api-key-here" and val != "your-vps-api-key":
                            self.loaded_keys[key] = val

    def scan_missing(self):
        """Scan all providers and find missing keys"""
        self.missing_keys = []
        for provider in PROVIDER_REGISTRY:
            key = os.environ.get(provider["env_key"], "")
            if not key:
                key = self.loaded_keys.get(provider["env_key"], "")
            if not key:
                self.missing_keys.append(provider)
        return self.missing_keys

    def get_status_report(self):
        """Full status of all providers"""
        configured = []
        missing = []
        for provider in PROVIDER_REGISTRY:
            key = os.environ.get(provider["env_key"], "") or self.loaded_keys.get(provider["env_key"], "")
            if key:
                configured.append({
                    "id": provider["id"],
                    "name": provider["name"],
                    "models": provider["models"],
                    "priority": provider["priority"],
                })
            else:
                missing.append({
                    "id": provider["id"],
                    "name": provider["name"],
                    "setup_url": provider["setup_url"],
                    "free_tier": provider["free_tier"],
                    "optional": provider.get("optional", False),
                })
        return {
            "total_providers": len(PROVIDER_REGISTRY),
            "configured": len(configured),
            "missing": len(missing),
            "configured_list": configured,
            "missing_list": missing,
        }

    def prompt_missing_keys(self):
        """Print missing keys with setup URLs — called during evolution cycle"""
        self.scan_missing()
        if not self.missing_keys:
            logger.info("All API keys configured!")
            return True

        print("\n" + "=" * 60)
        print("  TANKOS EVOLUTION — API KEY DISCOVERY")
        print("=" * 60)
        print(f"\n  Found {len(self.missing_keys)} missing API keys.\n")
        print("  The evolution system needs these to discover the best AI provider.\n")

        for i, provider in enumerate(self.missing_keys, 1):
            optional_tag = " (optional)" if provider.get("optional") else ""
            print(f"  {i}. {provider['name']}{optional_tag}")
            print(f"     Free tier: {provider['free_tier']}")
            print(f"     Get key:   {provider['setup_url']}")
            print()

        print("  ── HOW TO ADD KEYS ──")
        print("  Option A: Edit .env file directly")
        print("    nano ~/The-Tank-Project/.env")
        print("    Add: OPENROUTER_API_KEY=sk-or-v1-...")
        print()
        print("  Option B: Set environment variable")
        print("    export OPENROUTER_API_KEY=sk-or-v1-...")
        print()
        print("  Option C: Paste key when prompted by evolution")
        print("    (the system will ask you interactively)")
        print("=" * 60)

        # Send SMS notification about missing keys
        self._notify_missing_keys()

        return False

    def interactive_setup(self):
        """Interactive setup — ask user for each missing key"""
        self.scan_missing()
        if not self.missing_keys:
            return True

        print("\n🔍 TankOS Evolution — Interactive Key Setup\n")

        for provider in self.missing_keys:
            optional = provider.get("optional", False)
            tag = "(optional, press Enter to skip)" if optional else ""

            print(f"📋 {provider['name']} — {provider['free_tier']}")
            print(f"   Get key: {provider['setup_url']}")

            try:
                key = input(f"   Paste {provider['name']} API key {tag}: ").strip()
                if key:
                    self._save_key(provider["env_key"], key)
                    self.loaded_keys[provider["env_key"]] = key
                    os.environ[provider["env_key"]] = key
                    print(f"   ✅ {provider['name']} key saved!\n")
                else:
                    print(f"   ⏭️  Skipped {provider['name']}\n")
            except (EOFError, KeyboardInterrupt):
                print(f"\n   ⏸️  Setup paused. Run 'python -m tank.ai.evolution_key_manager' to continue.")
                return False

        print("✅ All available keys configured!")
        return True

    def _save_key(self, key_name, key_value):
        """Save key to .env file"""
        env_path = Path.home() / "The-Tank-Project" / ".env"
        if env_path.exists():
            content = env_path.read_text()
            if f"{key_name}=" in content:
                # Replace existing
                lines = content.splitlines()
                for i, line in enumerate(lines):
                    if line.startswith(f"{key_name}="):
                        lines[i] = f"{key_name}={key_value}"
                env_path.write_text("\n".join(lines) + "\n")
            else:
                # Append
                with open(env_path, "a") as f:
                    f.write(f"\n{key_name}={key_value}\n")
        else:
            env_path.write_text(f"{key_name}={key_value}\n")

    def _notify_missing_keys(self):
        """Send SMS/Telegram notification about missing keys"""
        message = (
            f"TankOS Evolution: {len(self.missing_keys)} API keys missing.\n"
        )
        for p in self.missing_keys[:5]:
            message += f"- {p['name']}: {p['setup_url']}\n"
        message += "Add keys to .env file."

        # SMS
        if SMS_NUMBER:
            try:
                subprocess.run(
                    ["bash", "-c",
                     f"echo '1234' | sudo -S mmcli -m 0 "
                     f"--messaging-create-sms='number={SMS_NUMBER},text={message}'"],
                    capture_output=True, timeout=10,
                )
            except:
                pass

        # Telegram
        if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
            try:
                data = json.dumps({
                    "chat_id": TELEGRAM_CHAT_ID,
                    "text": message,
                    "parse_mode": "HTML",
                }).encode()
                req = urllib.request.Request(
                    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                    data=data,
                    headers={"Content-Type": "application/json"},
                )
                urllib.request.urlopen(req, timeout=10)
            except:
                pass

    def run_evolution_cycle(self):
        """Full evolution cycle with key discovery"""
        logger.info("Starting evolution cycle...")
        self.evolution_log.append({
            "time": datetime.now().isoformat(),
            "event": "cycle_start",
        })

        # Step 1: Check keys
        status = self.get_status_report()
        print(f"\n🤖 Evolution Cycle — {status['configured']}/{status['total_providers']} providers configured")

        if status["missing"] > 0:
            print(f"⚠️  {status['missing']} keys missing")
            self.prompt_missing_keys()
            # Try interactive if still missing
            self.scan_missing()
            if self.missing_keys:
                self.interactive_setup()

        # Step 2: Test configured providers
        print("\n🧪 Testing configured providers...")
        results = []
        for provider in PROVIDER_REGISTRY:
            key = os.environ.get(provider["env_key"], "") or self.loaded_keys.get(provider["env_key"], "")
            if key:
                result = self._test_provider(provider, key)
                results.append(result)
                status_icon = "✅" if result["success"] else "❌"
                print(f"  {status_icon} {provider['name']}: {result.get('response', 'failed')[:50]}")

        # Step 3: Rank providers
        working = [r for r in results if r["success"]]
        working.sort(key=lambda x: x["latency_ms"])

        if working:
            best = working[0]
            print(f"\n🏆 Best provider: {best['name']} ({best['latency_ms']}ms)")
            self._save_primary_provider(best["id"])

        self.evolution_log.append({
            "time": datetime.now().isoformat(),
            "event": "cycle_complete",
            "providers_tested": len(results),
            "providers_working": len(working),
            "best": working[0]["name"] if working else "none",
        })

        return working

    def _test_provider(self, provider, key):
        """Test a provider with a simple query"""
        start = time.time()
        try:
            if provider["id"] == "groq":
                return self._test_groq(provider, key, start)
            elif provider["id"] == "openrouter":
                return self._test_openrouter(provider, key, start)
            elif provider["id"] == "cerebras":
                return self._test_cerebras(provider, key, start)
            elif provider["id"] == "mistral":
                return self._test_mistral(provider, key, start)
            else:
                return self._test_generic_openai(provider, key, start)
        except Exception as e:
            return {
                "id": provider["id"],
                "name": provider["name"],
                "success": False,
                "error": str(e),
                "latency_ms": int((time.time() - start) * 1000),
            }

    def _test_groq(self, provider, key, start):
        data = json.dumps({
            "model": "llama-3.1-8b-versatile",
            "messages": [{"role": "user", "content": provider["test_prompt"]}],
            "max_tokens": 20,
        }).encode()
        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=data,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        )
        resp = urllib.request.urlopen(req, timeout=10)
        result = json.loads(resp.read())
        latency = int((time.time() - start) * 1000)
        return {
            "id": provider["id"], "name": provider["name"],
            "success": True, "latency_ms": latency,
            "response": result["choices"][0]["message"]["content"],
        }

    def _test_openrouter(self, provider, key, start):
        data = json.dumps({
            "model": "google/gemma-2-9b-it",
            "messages": [{"role": "user", "content": provider["test_prompt"]}],
            "max_tokens": 20,
        }).encode()
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions",
            data=data,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        )
        resp = urllib.request.urlopen(req, timeout=15)
        result = json.loads(resp.read())
        latency = int((time.time() - start) * 1000)
        return {
            "id": provider["id"], "name": provider["name"],
            "success": True, "latency_ms": latency,
            "response": result["choices"][0]["message"]["content"],
        }

    def _test_cerebras(self, provider, key, start):
        data = json.dumps({
            "model": "llama-3.1-8b",
            "messages": [{"role": "user", "content": provider["test_prompt"]}],
            "max_tokens": 20,
        }).encode()
        req = urllib.request.Request(
            "https://api.cerebras.ai/v1/chat/completions",
            data=data,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        )
        resp = urllib.request.urlopen(req, timeout=10)
        result = json.loads(resp.read())
        latency = int((time.time() - start) * 1000)
        return {
            "id": provider["id"], "name": provider["name"],
            "success": True, "latency_ms": latency,
            "response": result["choices"][0]["message"]["content"],
        }

    def _test_mistral(self, provider, key, start):
        data = json.dumps({
            "model": "mistral-small-latest",
            "messages": [{"role": "user", "content": provider["test_prompt"]}],
            "max_tokens": 20,
        }).encode()
        req = urllib.request.Request(
            "https://api.mistral.ai/v1/chat/completions",
            data=data,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        )
        resp = urllib.request.urlopen(req, timeout=10)
        result = json.loads(resp.read())
        latency = int((time.time() - start) * 1000)
        return {
            "id": provider["id"], "name": provider["name"],
            "success": True, "latency_ms": latency,
            "response": result["choices"][0]["message"]["content"],
        }

    def _test_generic_openai(self, provider, key, start):
        data = json.dumps({
            "model": provider["models"][0],
            "messages": [{"role": "user", "content": provider["test_prompt"]}],
            "max_tokens": 20,
        }).encode()
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=data,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        )
        resp = urllib.request.urlopen(req, timeout=10)
        result = json.loads(resp.read())
        latency = int((time.time() - start) * 1000)
        return {
            "id": provider["id"], "name": provider["name"],
            "success": True, "latency_ms": latency,
            "response": result["choices"][0]["message"]["content"],
        }

    def _save_primary_provider(self, provider_id):
        """Save the best provider to config"""
        config_path = Path.home() / "The-Tank-Project" / "config" / "evolution.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config = {}
        if config_path.exists():
            config = json.loads(config_path.read_text())
        config["primary_provider"] = provider_id
        config["last_evolution"] = datetime.now().isoformat()
        config_path.write_text(json.dumps(config, indent=2))
        logger.info(f"Primary provider set to: {provider_id}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    mgr = EvolutionKeyManager()
    mgr.prompt_missing_keys()
