"""Manifest emitters — format ToolDefinitions for various LLM providers.

Three canonical formats:
  - OpenAI function-calling tools=[…]
  - Anthropic tools=[…]
  - raw/JSON (provider-neutral)

The Manifest class is a thin façade over the registry.
"""
from __future__ import annotations
from typing import Optional

from .schemas import ToolDefinition


RISK_TIERS = ("low", "medium", "high")


def _to_openai_tool(t: ToolDefinition) -> dict:
    return {
        "type": "function",
        "function": {
            "name": t.name,
            "description": t.description,
            "parameters": t.args_schema,
        },
    }


def _to_anthropic_tool(t: ToolDefinition) -> dict:
    return {
        "name": t.name,
        "description": t.description,
        "input_schema": t.args_schema,
    }


def _to_raw_tool(t: ToolDefinition) -> dict:
    return {
        "id": t.name,
        "name": t.human_name,
        "description": t.description,
        "category": t.category,
        "risk_tier": t.risk_tier,
        "script_path": t.script_path,
        "subcommand": t.subcommand,
        "args_schema": t.args_schema,
        "fids": t.fids,
    }


class Manifest:
    """Container for the full registry, with format-specific accessors."""
    def __init__(self, registry):
        self.registry = registry

    def openai(self, names: Optional[list] = None) -> list:
        return [_to_openai_tool(t) for t in self.registry.list()
                if names is None or t.name in names]

    def anthropic(self, names: Optional[list] = None) -> list:
        return [_to_anthropic_tool(t) for t in self.registry.list()
                if names is None or t.name in names]

    def raw(self, names: Optional[list] = None) -> list:
        return [_to_raw_tool(t) for t in self.registry.list()
                if names is None or t.name in names]

    def per_category(self) -> dict:
        out = {}
        for t in self.registry.list():
            out.setdefault(t.category, []).append(_to_raw_tool(t))
        return out

    def summary(self) -> dict:
        return {
            "total": len(self.registry.list()),
            "categories": self.registry.categories(),
            "risk_distribution": self._risk_dist(),
        }

    def _risk_dist(self) -> dict:
        out = {"low": 0, "medium": 0, "high": 0}
        for t in self.registry.list():
            out[t.risk_tier] = out.get(t.risk_tier, 0) + 1
        return out


# Module-level conveniences.
def openai_manifest(registry) -> list:
    return Manifest(registry).openai()

def anthropic_manifest(registry) -> list:
    return Manifest(registry).anthropic()

def raw_manifest(registry) -> list:
    return Manifest(registry).raw()
