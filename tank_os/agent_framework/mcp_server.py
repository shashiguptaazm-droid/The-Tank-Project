#!/usr/bin/env python3
"""TankOS MCP Server — exposes TankOS tools via Model Context Protocol.

This server wraps the TankOS Agent Framework and exposes all 1,166+ tools
as MCP tools, making them available to OpenCode and other MCP-compatible clients.

Usage:
    python3 tank_os/agent_framework/mcp_server.py
    
    Or configure in opencode.json:
    {
      "mcp": {
        "tankos": {
          "type": "local",
          "command": ["python3", "tank_os/agent_framework/mcp_server.py"],
          "enabled": true
        }
      }
    }
"""

from __future__ import annotations

import os
import sys
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

# Load .env.keys if present
_env_file = _PROJECT_ROOT / ".env.keys"
if _env_file.exists():
    for line in _env_file.read_text().splitlines():
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            if k not in os.environ:
                os.environ[k] = v

logger = logging.getLogger("tankos.mcp")

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print("ERROR: mcp package not installed. Run: pip install mcp", file=sys.stderr)
    sys.exit(1)

from tank_os.agent_framework.registry import ToolRegistry
from tank_os.agent_framework.invoker import ToolInvoker
from tank_os.agent_framework.schemas import ToolCallRequest

# ═══════════════════════════════════════════════════════════════════════════
#  MCP Server Setup
# ═══════════════════════════════════════════════════════════════════════════

mcp = FastMCP(
    "TankOS Agent",
    version="1.0.0",
    description="TankOS robot tools — 1,166+ callable modules for autonomous robotics"
)

# ═══════════════════════════════════════════════════════════════════════════
#  Registry & Invoker
# ═══════════════════════════════════════════════════════════════════════════

_SCRIPTS_DIR = _PROJECT_ROOT / "scripts"
_registry: Optional[ToolRegistry] = None
_invoker: Optional[ToolInvoker] = None


def _get_registry() -> ToolRegistry:
    global _registry
    if _registry is None:
        _registry = ToolRegistry(scripts_dir=_SCRIPTS_DIR)
        _registry.discover()
    return _registry


def _get_invoker() -> ToolInvoker:
    global _invoker
    if _invoker is None:
        _invoker = ToolInvoker(_get_registry())
    return _invoker


# ═══════════════════════════════════════════════════════════════════════════
#  Tool Discovery
# ═══════════════════════════════════════════════════════════════════════════

def _discover_tools() -> List[Dict[str, Any]]:
    """Discover all tools and return MCP-compatible tool definitions."""
    registry = _get_registry()
    tools = registry.list()
    
    mcp_tools = []
    for tool in tools:
        # Convert TankOS tool to MCP tool format
        parameters = {
            "type": "object",
            "properties": {},
            "required": []
        }
        
        # Add parameters from tool definition if available
        if hasattr(tool, 'parameters') and tool.parameters:
            for param_name, param_info in tool.parameters.items():
                parameters["properties"][param_name] = {
                    "type": param_info.get("type", "string"),
                    "description": param_info.get("description", "")
                }
                if param_info.get("required", False):
                    parameters["required"].append(param_name)
        
        mcp_tools.append({
            "name": tool.name,
            "description": tool.description or f"TankOS tool: {tool.name}",
            "inputSchema": parameters
        })
    
    return mcp_tools


# ═══════════════════════════════════════════════════════════════════════════
#  Core MCP Tools
# ═══════════════════════════════════════════════════════════════════════════

@mcp.tool()
def tankos_list_tools(category: Optional[str] = None) -> str:
    """List all available TankOS tools, optionally filtered by category.
    
    Args:
        category: Optional category filter (e.g., 'perception', 'navigation', 'voice')
    
    Returns:
        JSON string with tool list
    """
    registry = _get_registry()
    tools = registry.list()
    
    if category:
        tools = [t for t in tools if t.category.lower() == category.lower()]
    
    result = []
    for tool in tools[:100]:  # Limit to 100 for readability
        result.append({
            "name": tool.name,
            "category": tool.category,
            "description": (tool.description or "")[:100]
        })
    
    return json.dumps({
        "total": len(tools),
        "shown": len(result),
        "tools": result
    }, indent=2)


@mcp.tool()
def tankos_invoke_tool(tool_name: str, args: Optional[Dict[str, Any]] = None) -> str:
    """Invoke a TankOS tool by name with arguments.
    
    Args:
        tool_name: Name of the tool to invoke (e.g., 'perception.capture', 'navigation.go_to')
        args: Optional arguments dictionary for the tool
    
    Returns:
        Tool execution result
    """
    if args is None:
        args = {}
    
    try:
        invoker = _get_invoker()
        request = ToolCallRequest(
            tool_name=tool_name,
            args=args,
            timeout_s=30
        )
        response = invoker.invoke(request)
        
        result = {
            "tool": tool_name,
            "status": response.status,
            "exit_code": response.exit_code,
            "duration_ms": response.duration_ms
        }
        
        if response.stdout:
            result["stdout"] = response.stdout.strip()
        if response.stderr:
            result["stderr"] = response.stderr.strip()
        
        return json.dumps(result, indent=2)
    
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


@mcp.tool()
def tankos_search_tools(query: str) -> str:
    """Search TankOS tools by keyword or description.
    
    Args:
        query: Search query to find matching tools
    
    Returns:
        JSON string with matching tools
    """
    registry = _get_registry()
    tools = registry.list()
    
    query_lower = query.lower()
    matches = []
    
    for tool in tools:
        if (query_lower in tool.name.lower() or 
            query_lower in (tool.description or "").lower() or
            query_lower in tool.category.lower()):
            matches.append({
                "name": tool.name,
                "category": tool.category,
                "description": (tool.description or "")[:100]
            })
    
    return json.dumps({
        "query": query,
        "matches": len(matches),
        "tools": matches[:20]
    }, indent=2)


@mcp.tool()
def tankos_get_tool_info(tool_name: str) -> str:
    """Get detailed information about a specific TankOS tool.
    
    Args:
        tool_name: Name of the tool to inspect
    
    Returns:
        JSON string with tool details
    """
    registry = _get_registry()
    tool = registry.get(tool_name)
    
    if tool is None:
        return json.dumps({"error": f"Tool '{tool_name}' not found"}, indent=2)
    
    info = {
        "name": tool.name,
        "category": tool.category,
        "description": tool.description,
        "risk_level": getattr(tool, 'risk_level', 'unknown'),
        "parameters": getattr(tool, 'parameters', {})
    }
    
    return json.dumps(info, indent=2)


@mcp.tool()
def tankos_camera_vision() -> str:
    """Capture from DFRobot USB camera and run YOLO object detection.
    
    Returns:
        Description of detected objects in the camera frame
    """
    try:
        from tank_os.shell.terminal.agent_chat import _camera_vision
        result = _camera_vision()
        return result
    except Exception as e:
        return f"Camera error: {e}"


@mcp.tool()
def tankos_system_status() -> str:
    """Get TankOS system status including hardware, network, and AI providers.
    
    Returns:
        JSON string with system status
    """
    try:
        # Get basic system info
        import subprocess
        uptime = subprocess.run(["uptime", "-p"], capture_output=True, text=True, timeout=5)
        memory = subprocess.run(["free", "-h"], capture_output=True, text=True, timeout=5)
        disk = subprocess.run(["df", "-h", "/"], capture_output=True, text=True, timeout=5)
        
        status = {
            "uptime": uptime.stdout.strip() if uptime.returncode == 0 else "unknown",
            "memory": memory.stdout.strip() if memory.returncode == 0 else "unknown",
            "disk": disk.stdout.strip() if disk.returncode == 0 else "unknown",
            "tools_available": len(_get_registry().list())
        }
        
        return json.dumps(status, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


@mcp.tool()
def tankos_shell_command(command: str) -> str:
    """Execute a shell command on the TankOS system.
    
    Args:
        command: Shell command to execute
    
    Returns:
        Command output
    """
    import subprocess
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        output = {
            "command": command,
            "exit_code": result.returncode,
            "stdout": result.stdout.strip()[:2000] if result.stdout else "",
            "stderr": result.stderr.strip()[:1000] if result.stderr else ""
        }
        
        return json.dumps(output, indent=2)
    except subprocess.TimeoutExpired:
        return json.dumps({"error": "Command timed out after 30 seconds"}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


# ═══════════════════════════════════════════════════════════════════════════
#  AI Provider Management
# ═══════════════════════════════════════════════════════════════════════════

# All 10 AI providers with their API key env vars and endpoints
AI_PROVIDERS = {
    "groq": {
        "name": "Groq",
        "env_key": "GROQ_API_KEY",
        "base_url": "https://api.groq.com/openai/v1",
        "models": ["llama-3.1-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"],
        "speed": "fastest",
        "free_tier": "Unlimited Llama/Mixtral requests"
    },
    "openrouter": {
        "name": "OpenRouter",
        "env_key": "OPENROUTER_API_KEY",
        "base_url": "https://openrouter.ai/api/v1",
        "models": ["openai/gpt-4o-mini", "anthropic/claude-3.5-sonnet", "google/gemini-2.0-flash"],
        "speed": "fast",
        "free_tier": "$5 credit on signup"
    },
    "gemini": {
        "name": "Google Gemini",
        "env_key": "GEMINI_API_KEY",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "models": ["gemini-2.0-flash", "gemini-1.5-pro"],
        "speed": "fast",
        "free_tier": "15 RPM Gemini Flash"
    },
    "mistral": {
        "name": "Mistral AI",
        "env_key": "MISTRAL_API_KEY",
        "base_url": "https://api.mistral.ai/v1",
        "models": ["mistral-small-latest", "mistral-medium-latest"],
        "speed": "fast",
        "free_tier": "1 RPM Mistral Small"
    },
    "cerebras": {
        "name": "Cerebras",
        "env_key": "CEREBRAS_API_KEY",
        "base_url": "https://api.cerebras.ai/v1",
        "models": ["llama-3.1-8b", "llama-3.1-70b"],
        "speed": "fastest",
        "free_tier": "30 RPM Llama 3.1 8B"
    },
    "cohere": {
        "name": "Cohere",
        "env_key": "COHERE_API_KEY",
        "base_url": "https://api.cohere.ai/v1",
        "models": ["command-r-plus", "command-r"],
        "speed": "medium",
        "free_tier": "1000 RPM Command R"
    },
    "replicate": {
        "name": "Replicate",
        "env_key": "REPLICATE_API_KEY",
        "base_url": "https://api.replicate.com/v1",
        "models": ["meta/llama-3.1-70b-instruct", "mistralai/mixtral-8x7b-instruct-v0.1"],
        "speed": "medium",
        "free_tier": "$5 credit"
    },
    "huggingface": {
        "name": "Hugging Face",
        "env_key": "HUGGINGFACE_API_KEY",
        "base_url": "https://api-inference.huggingface.co/models",
        "models": ["meta-llama/Meta-Llama-3.1-8B-Instruct", "mistralai/Mixtral-8x7B-Instruct-v0.1"],
        "speed": "medium",
        "free_tier": "30K chars/month inference"
    },
    "cloudflare": {
        "name": "Cloudflare Workers AI",
        "env_key": "CLOUDFLARE_WORKER_API_KEY",
        "base_url": "https://api.cloudflare.com/client/v4/accounts",
        "models": ["@cf/meta/llama-3.1-8b-instruct", "@cf/mistral/mistral-7b-instruct-v0.2"],
        "speed": "fast",
        "free_tier": "10K requests/day"
    },
    "openai": {
        "name": "OpenAI",
        "env_key": "OPENAI_API_KEY",
        "base_url": "https://api.openai.com/v1",
        "models": ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"],
        "speed": "fast",
        "free_tier": "$5 credit on signup"
    },
    "nvidia": {
        "name": "NVIDIA (Nemotron Ultra 550B + Vision + Qwen3 Coder 480B)",
        "env_key": "NVIDIA_API_KEY",
        "base_url": "https://integrate.api.nvidia.com/v1",
        "models": ["nvidia/nemotron-3-ultra-550b-a55b", "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning", "deepseek-ai/deepseek-v4-flash-0731", "qwen/qwen3-coder-480b-a35b-instruct"],
        "speed": "medium",
        "free_tier": "1000 credits/day",
        "description": "Fallback model — Nemotron Ultra 550B (text), Vision Omni (images), Qwen3 Coder 480B (code)"
    }
}


@mcp.tool()
def tankos_list_providers() -> str:
    """List all configured AI providers and their status.
    
    Returns:
        JSON string with provider status
    """
    result = {}
    for provider_id, config in AI_PROVIDERS.items():
        api_key = os.environ.get(config["env_key"], "")
        result[provider_id] = {
            "name": config["name"],
            "configured": bool(api_key),
            "speed": config["speed"],
            "free_tier": config["free_tier"],
            "models": config["models"][:2],
            "base_url": config["base_url"]
        }
    
    configured_count = sum(1 for p in result.values() if p["configured"])
    
    return json.dumps({
        "total_providers": len(result),
        "configured": configured_count,
        "providers": result
    }, indent=2)


def _extract_nvidia_answer(text: str) -> str:
    """Extract final answer from NVIDIA thinking models."""
    lines = text.strip().split("\n")
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        if line.startswith("Let me") or line.startswith("I'll") or line.startswith("Actually"):
            continue
        if line.startswith("-") and "output" in line.lower():
            continue
        if "--" in line and len(line) < 50:
            continue
        return line
    return lines[-1].strip() if lines else text


@mcp.tool()
def tankos_call_llm(provider: str, prompt: str, system_prompt: Optional[str] = None) -> str:
    """Call an AI provider with a prompt.
    
    Args:
        provider: Provider ID (groq, openrouter, gemini, mistral, cerebras, cohere, replicate, huggingface, cloudflare, openai, nvidia)
        prompt: The prompt to send to the LLM
        system_prompt: Optional system prompt
    
    Returns:
        LLM response
    """
    if provider not in AI_PROVIDERS:
        return json.dumps({"error": f"Unknown provider: {provider}. Available: {list(AI_PROVIDERS.keys())}"})
    
    config = AI_PROVIDERS[provider]
    api_key = os.environ.get(config["env_key"], "")
    
    if not api_key:
        return json.dumps({"error": f"No API key for {provider}. Set {config['env_key']} in .env.keys"})
    
    try:
        import httpx
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # Use OpenAI-compatible endpoint for most providers
        if provider in ["groq", "openrouter", "mistral", "cerebras", "openai", "nvidia"]:
            # For NVIDIA, try the second API key if first fails
            nvidia_key = api_key
            if provider == "nvidia":
                key2 = os.environ.get("NVIDIA_API_KEY_2", "")
                if key2:
                    nvidia_key = key2  # Use the second key for Nemotron Ultra
            resp = httpx.post(
                f"{config['base_url']}/chat/completions",
                headers={"Authorization": f"Bearer {nvidia_key}", "Content-Type": "application/json"},
                json={"model": config["models"][0], "messages": messages, "max_tokens": 1024, "temperature": 0.7},
                timeout=30.0
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"].strip()
            # NVIDIA models return thinking + answer, extract just the final answer
            if provider == "nvidia":
                content = _extract_nvidia_answer(content)
            return content
        
        # Gemini
        elif provider == "gemini":
            body = {
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"maxOutputTokens": 1024, "temperature": 0.7}
            }
            if system_prompt:
                body["systemInstruction"] = {"parts": [{"text": system_prompt}]}
            resp = httpx.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{config['models'][0]}:generateContent?key={api_key}",
                headers={"Content-Type": "application/json"},
                json=body, timeout=30.0
            )
            resp.raise_for_status()
            return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        
        # Cohere
        elif provider == "cohere":
            body = {"model": config["models"][0], "message": prompt, "max_tokens": 1024}
            if system_prompt:
                body["preamble"] = system_prompt
            resp = httpx.post(
                "https://api.cohere.ai/v1/chat",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=body, timeout=30.0
            )
            resp.raise_for_status()
            return resp.json()["text"].strip()
        
        else:
            return json.dumps({"error": f"Provider {provider} not yet implemented"})
    
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def tankos_call_llm_fallback(prompt: str, system_prompt: Optional[str] = None) -> str:
    """Call AI providers with automatic fallback — tries all configured providers.
    
    Args:
        prompt: The prompt to send
        system_prompt: Optional system prompt
    
    Returns:
        LLM response from the first successful provider
    """
    # Priority order: fastest to slowest, NVIDIA last as coding fallback
    priority_order = ["groq", "cerebras", "openrouter", "gemini", "mistral", "openai", "cohere", "cloudflare", "replicate", "huggingface", "nvidia"]
    
    last_error = None
    for provider_id in priority_order:
        config = AI_PROVIDERS.get(provider_id)
        if not config:
            continue
        
        api_key = os.environ.get(config["env_key"], "")
        if not api_key:
            continue
        
        try:
            result = tankos_call_llm(provider_id, prompt, system_prompt)
            if not result.startswith("{\"error\":"):
                return result
        except Exception as e:
            last_error = str(e)
            continue
    
    return json.dumps({"error": f"All providers failed. Last error: {last_error}"})


@mcp.tool()
def tankos_get_provider_info(provider: str) -> str:
    """Get detailed information about a specific AI provider.
    
    Args:
        provider: Provider ID
    
    Returns:
        Provider details
    """
    if provider not in AI_PROVIDERS:
        return json.dumps({"error": f"Unknown provider: {provider}"})
    
    config = AI_PROVIDERS[provider]
    api_key = os.environ.get(config["env_key"], "")
    
    return json.dumps({
        "id": provider,
        "name": config["name"],
        "configured": bool(api_key),
        "base_url": config["base_url"],
        "models": config["models"],
        "speed": config["speed"],
        "free_tier": config["free_tier"],
        "setup_url": _get_setup_url(provider)
    }, indent=2)


def _get_setup_url(provider: str) -> str:
    """Get setup URL for a provider."""
    urls = {
        "groq": "https://console.groq.com/keys",
        "openrouter": "https://openrouter.ai/keys",
        "gemini": "https://aistudio.google.com/apikey",
        "mistral": "https://console.mistral.ai/api-keys",
        "cerebras": "https://cloud.cerebras.ai/api-keys",
        "cohere": "https://dashboard.cohere.com/api-keys",
        "replicate": "https://replicate.com/account/api-tokens",
        "huggingface": "https://huggingface.co/settings/tokens",
        "cloudflare": "https://dash.cloudflare.com/profile/api-tokens",
        "openai": "https://platform.openai.com/api-keys",
        "nvidia": "https://build.nvidia.com/"
    }
    return urls.get(provider, "")


# ═══════════════════════════════════════════════════════════════════════════
#  Dynamic Tool Registration
# ═══════════════════════════════════════════════════════════════════════════

def _register_dynamic_tools():
    """Register top TankOS tools as individual MCP tools for better discoverability."""
    registry = _get_registry()
    tools = registry.list()
    
    # Group tools by category and register key ones
    categories = {}
    for tool in tools:
        cat = tool.category
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(tool)
    
    # Register a wrapper function for each major category
    for cat_name, cat_tools in categories.items():
        if len(cat_tools) > 0:
            # Create a category-specific tool
            tool_names = [t.name for t in cat_tools[:10]]  # Top 10 per category
            
            @mcp.tool()
            def category_tool(tool_name: str, args: Optional[Dict[str, Any]] = None) -> str:
                """Invoke a TankOS tool from this category."""
                return tankos_invoke_tool(tool_name, args)
            
            # Set the function name dynamically
            safe_name = cat_name.replace(" ", "_").replace("-", "_").lower()
            category_tool.__name__ = f"tankos_{safe_name}"
            category_tool.__doc__ = f"Invoke TankOS tools in the {cat_name} category. Tools: {', '.join(tool_names[:5])}..."


# ═══════════════════════════════════════════════════════════════════════════
#  Main Entry Point
# ═══════════════════════════════════════════════════════════════════════════

def main():
    """Start the TankOS MCP server."""
    print("🛡️  TankOS MCP Server starting...", file=sys.stderr)
    print(f"   Project root: {_PROJECT_ROOT}", file=sys.stderr)
    print(f"   Scripts dir: {_SCRIPTS_DIR}", file=sys.stderr)
    
    # Initialize registry
    registry = _get_registry()
    print(f"   Tools discovered: {len(registry.list())}", file=sys.stderr)
    
    # Register dynamic tools
    _register_dynamic_tools()
    
    print("   Ready to accept connections", file=sys.stderr)
    
    # Run the MCP server
    mcp.run()


if __name__ == "__main__":
    main()
