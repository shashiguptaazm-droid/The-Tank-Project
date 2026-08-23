"""
tool_caller.py - LLM Tool-Calling Bridge for TankOS
Supports ALL providers: Groq, OpenRouter, Gemini, Cerebras, Mistral,
OpenAI, Anthropic, plus local Phi-3/TinyLlama via llama.cpp.
Every LLM can call TankOS tools during conversation.
"""
import json
import time
import logging
import os
import urllib.request
from datetime import datetime
from tank.ai.tool_registry import TANK_TOOLS

logger = logging.getLogger("tank.ai.tool_caller")

# Provider configs — OpenAI-compatible endpoints
PROVIDER_ENDPOINTS = {
    "groq": {
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "model": "llama-3.1-8b-versatile",
        "env_key": "GROQ_API_KEY",
    },
    "openrouter": {
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "model": "google/gemma-2-9b-it",
        "env_key": "OPENROUTER_API_KEY",
    },
    "cerebras": {
        "url": "https://api.cerebras.ai/v1/chat/completions",
        "model": "llama-3.1-8b",
        "env_key": "CEREBRAS_API_KEY",
    },
    "mistral": {
        "url": "https://api.mistral.ai/v1/chat/completions",
        "model": "mistral-small-latest",
        "env_key": "MISTRAL_API_KEY",
    },
    "gemini": {
        "url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "model": "gemini-1.5-flash",
        "env_key": "GEMINI_API_KEY",
    },
    "cohere": {
        "url": "https://api.cohere.com/v2/chat",
        "model": "command-r",
        "env_key": "COHERE_API_KEY",
    },
    "openai": {
        "url": "https://api.openai.com/v1/chat/completions",
        "model": "gpt-4o-mini",
        "env_key": "OPENAI_API_KEY",
    },
    "anthropic": {
        "url": "https://api.anthropic.com/v1/messages",
        "model": "claude-3-haiku-20240307",
        "env_key": "ANTHROPIC_API_KEY",
        "native_tools": True,  # Anthropic has its own tool format
    },
    "together": {
        "url": "https://api.together.xyz/v1/chat/completions",
        "model": "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
        "env_key": "TOGETHER_API_KEY",
    },
    "deepinfra": {
        "url": "https://api.deepinfra.com/v1/openai/chat/completions",
        "model": "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
        "env_key": "DEEPINFRA_API_KEY",
    },
    "sambanova": {
        "url": "https://api.sambanova.ai/v1/chat/completions",
        "model": "Meta-Llama-3.1-8B-Instruct",
        "env_key": "SAMBANOVA_API_KEY",
    },
    "replicate": {
        "url": "https://api.replicate.com/v1/chat/completions",
        "model": "meta/meta-llama-3.1-8b-instruct",
        "env_key": "REPLICATE_API_KEY",
    },
    "huggingface": {
        "url": "https://api-inference.huggingface.co/models/",
        "model": "meta-llama/Meta-Llama-3.1-8B-Instruct",
        "env_key": "HUGGINGFACE_API_KEY",
    },
    "cloudflare": {
        "url": "https://api.cloudflare.com/client/v4/accounts/",
        "model": "@cf/meta/llama-3.1-8b-instruct",
        "env_key": "CLOUDFLARE_WORKER_API_KEY",
    },
}

TANK_SYSTEM_PROMPT = """You are TankOS — the AI brain of an autonomous robot called "The Tank".
You have access to tools to control the robot. Always use tools when the user asks
you to DO something (move, capture, read sensors, etc.).

You can:
- Move the robot and control motors
- Capture images and detect objects
- Read all sensors (IMU, LiDAR, battery, temperature)
- Navigate autonomously and patrol
- Send SMS messages and alerts
- Execute terminal commands
- Get system and robot status

Be helpful, concise, and always use tools when appropriate.
If unsure, ask the user. Safety first — use emergency_stop if needed."""

MAX_TOOL_ROUNDS = 5  # Max tool call iterations


class ToolCaller:
    """LLM bridge that supports tool calling across all providers"""

    def __init__(self, tool_executor=None, preferred_provider=None):
        self.executor = tool_executor
        self.preferred_provider = preferred_provider or self._find_best_provider()
        self.conversation_history = []
        self.tool_call_count = 0
        self._local_model = None

    def _find_best_provider(self):
        """Find the best available cloud provider"""
        priority = ["groq", "openrouter", "cerebras", "mistral", "gemini",
                     "openai", "together", "deepinfra", "sambanova"]
        for pid in priority:
            config = PROVIDER_ENDPOINTS.get(pid)
            if config:
                key = os.environ.get(config["env_key"], "")
                if key:
                    return pid
        return None

    def chat(self, user_message, provider=None, stream=False):
        """Chat with tool calling — works with ANY provider"""
        prov = provider or self.preferred_provider
        self.conversation_history.append({"role": "user", "content": user_message})

        # Try cloud providers with fallback
        fallback_order = [prov, "groq", "openrouter", "cerebras", "mistral", "gemini"]
        fallback_order = [p for p in fallback_order if p]
        for try_prov in fallback_order:
            result = self._cloud_chat(user_message, try_prov)
            if result:
                return result

        # Try local model with tool calling
        result = self._local_chat(user_message)
        if result:
            return result

        return "No AI provider available. Check API keys in .env file."

    def _cloud_chat(self, user_message, provider_id):
        """Cloud provider chat with OpenAI-compatible tool calling"""
        config = PROVIDER_ENDPOINTS.get(provider_id)
        if not config:
            return None

        api_key = os.environ.get(config["env_key"], "")
        if not api_key:
            return None

        tools = self._get_tools_for_provider(provider_id)

        messages = [
            {"role": "system", "content": TANK_SYSTEM_PROMPT},
        ]
        # Add recent history
        for msg in self.conversation_history[-10:]:
            messages.append(msg)
        messages.append({"role": "user", "content": user_message})

        for round_num in range(MAX_TOOL_ROUNDS):
            try:
                payload = {
                    "model": config["model"],
                    "messages": messages,
                    "tools": tools,
                    "tool_choice": "auto",
                    "max_tokens": 500,
                    "temperature": 0.7,
                }

                data = json.dumps(payload).encode()
                req = urllib.request.Request(
                    config["url"],
                    data=data,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                )
                resp = urllib.request.urlopen(req, timeout=30)
                result = json.loads(resp.read())

                choice = result["choices"][0]
                message = choice["message"]

                # Check for tool calls
                if message.get("tool_calls"):
                    # Execute each tool call
                    messages.append(message)
                    for tool_call in message["tool_calls"]:
                        func_name = tool_call["function"]["name"]
                        func_args = json.loads(tool_call["function"]["arguments"])

                        logger.info(f"Tool call: {func_name}({func_args})")
                        exec_result = self.executor.execute(func_name, func_args)
                        self.tool_call_count += 1

                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": json.dumps(exec_result),
                        })
                    # Continue to get final response
                    continue

                # No tool calls — return the text response
                content = message.get("content", "")
                self.conversation_history.append({"role": "assistant", "content": content})
                return content

            except Exception as e:
                logger.error(f"Provider {provider_id} error: {e}")
                return None

        return "Tool calling loop exceeded maximum rounds"

    def _local_chat(self, user_message):
        """Local llama.cpp model with text-based tool calling"""
        try:
            from llama_cpp import Llama

            if not self._local_model:
                model_paths = [
                    os.path.expanduser("~/models/phi-3-mini-4k-instruct-Q4_K_M.gguf"),
                    os.path.expanduser("~/models/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"),
                ]
                for path in model_paths:
                    if os.path.exists(path):
                        self._local_model = Llama(model_path=path, n_ctx=4096, n_threads=4)
                        break
                if not self._local_model:
                    return None

            # Build tool-augmented prompt
            tools_desc = self._get_tools_text()
            prompt = f"""{TANK_SYSTEM_PROMPT}

Available tools:
{tools_desc}

When you need to use a tool, respond EXACTLY in this format:
TOOL_CALL: tool_name(param1=value1, param2=value2)

User: {user_message}
Assistant:"""

            response = self._local_model.create_completion(
                prompt=prompt,
                max_tokens=300,
                temperature=0.7,
                stop=["User:", "Human:"],
            )
            text = response["choices"][0]["text"].strip()

            # Parse tool calls from text
            if "TOOL_CALL:" in text:
                return self._parse_text_tool_calls(text)

            self.conversation_history.append({"role": "assistant", "content": text})
            return text

        except ImportError:
            logger.info("llama-cpp-python not installed, skipping local model")
            return None
        except Exception as e:
            logger.error(f"Local model error: {e}")
            return None

    def _parse_text_tool_calls(self, text):
        """Parse TOOL_CALL: format from local model output"""
        results = []
        for line in text.split("\n"):
            if "TOOL_CALL:" in line:
                call_str = line.split("TOOL_CALL:")[1].strip()
                # Parse: tool_name(param1=val1, param2=val2)
                try:
                    func_name = call_str.split("(")[0]
                    params_str = call_str.split("(", 1)[1].rstrip(")")
                    func_args = {}
                    if params_str:
                        for pair in params_str.split(","):
                            key, _, val = pair.partition("=")
                            val = val.strip().strip('"').strip("'")
                            # Try to parse as number
                            try:
                                val = int(val)
                            except:
                                try:
                                    val = float(val)
                                except:
                                    pass
                            func_args[key.strip()] = val

                    result = self.executor.execute(func_name, func_args)
                    self.tool_call_count += 1
                    results.append(f"Tool {func_name}: {json.dumps(result)}")
                except Exception as e:
                    results.append(f"Tool parse error: {e}")

        if results:
            # Feed results back to LLM for final answer
            summary = "\n".join(results)
            followup = f"Tool results:\n{summary}\n\nBased on these results, respond to the user."
            return self._local_chat(followup)

        return text

    def _get_tools_for_provider(self, provider_id):
        """Get tools in the format the provider expects"""
        config = PROVIDER_ENDPOINTS.get(provider_id, {})

        if provider_id == "anthropic" and config.get("native_tools"):
            # Anthropic uses its own tool format
            tools = []
            for tool in TANK_TOOLS:
                f = tool["function"]
                tools.append({
                    "name": f["name"],
                    "description": f["description"],
                    "input_schema": f["parameters"],
                })
            return tools

        # Default: OpenAI format
        return TANK_TOOLS

    def _get_tools_text(self):
        """Get tools as text for local model"""
        lines = []
        for tool in TANK_TOOLS:
            f = tool["function"]
            params = []
            for pname, pdef in f["parameters"].get("properties", {}).items():
                params.append(f"{pname}: {pdef.get('type', 'string')}")
            lines.append(f"- {f['name']}({', '.join(params)}): {f['description']}")
        return "\n".join(lines)

    def get_status(self):
        return {
            "provider": self.preferred_provider,
            "total_providers": len([k for k, v in PROVIDER_ENDPOINTS.items()
                                    if os.environ.get(v["env_key"], "")]),
            "tool_calls": self.tool_call_count,
            "conversation_length": len(self.conversation_history),
            "local_model": "loaded" if self._local_model else "not loaded",
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from tank.ai.tool_registry import ToolExecutor
    executor = ToolExecutor()
    caller = ToolCaller(tool_executor=executor)
    print(json.dumps(caller.get_status(), indent=2))
