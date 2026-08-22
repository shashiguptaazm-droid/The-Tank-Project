"""ToolRegistry — walks scripts/*.py and assembles a ToolDefinition list.

Discovers tools via Python AST parsing (no subprocess required).
Each top-level `cmd_<sub>(args)` function becomes one tool:
  - tool name = f"{script_basename}.{sub}"
  - description = docstring's first line (≤240 chars)
  - F-IDs extracted from the full docstring (regex)
  - risk_tier = derived from name + description keywords
  - category = looked up in _CATEGORIES by script basename
"""
from __future__ import annotations
import ast
import datetime
import re
import sys
from pathlib import Path
from typing import Optional

from .schemas import ToolDefinition


_RISK_KEYWORDS_HIGH = (
    "drop", "delete", "rm", "reset", "kill", "stop", "shutdown",
    "format", "wipe", "truncate", "drop-table", "drop-database",
    "estop", "e-stop", "emergency", "block", "ban",
    "charge", "dock", "arm", "fire",
    "throw-", "shoot-", "fireworks",
)
_RISK_KEYWORDS_MEDIUM = (
    "upload", "send", "post", "publish", "deploy",
    "install", "write", "create", "add", "update", "modify",
    "share", "broadcast",
    "download", "fetch", "grab", "rip",
    "control", "move", "rotate", "patrol",
    "tip", "donate", "send-message", "share-list",
)


def _risk_for(name: str, desc: str) -> str:
    n = (name + " " + desc).lower()
    if any(k in n for k in _RISK_KEYWORDS_HIGH):
        return "high"
    if any(k in n for k in _RISK_KEYWORDS_MEDIUM):
        return "medium"
    return "low"


_FID_RE = re.compile(r"\bF(\d{3,4})\b|\bFID\s*(\d{3,4})\b")


def _fids_in_text(s: str) -> list:
    out = set()
    for m in _FID_RE.finditer(s):
        try:
            out.add(int(m.group(1) or m.group(2)))
        except (ValueError, TypeError):
            pass
    return sorted(out)


_CATEGORIES = {
    "ai_vision": "vision",
    "ai_voice": "voice",
    "vision_ar": "vision",
    "personality": "personality",
    "security_bio": "security",
    "mobility_nav": "mobility",
    "environment": "environment",
    "media_hub": "media",
    "home_automation": "home-automation",
    "comm_networking": "comm",
    "maintenance": "maintenance",
    "gaming": "gaming",
    "health": "health",
    "kitchen": "kitchen",
    "education": "education",
    "creativity": "creativity",
    "productivity_social": "productivity",
    "energy_home": "energy",
    "outdoor_security": "outdoor-security",
    "maker_misc": "maker",
    "download_music": "download-music",
    "download_video": "download-video",
    "download_data": "download-data",
    "download_torrent": "download-torrent",
    "download_scheduled": "download-scheduled",
    "download_deepweb": "download-deepweb",
    "download_music_2": "download-music-2",
    "download_video_2": "download-video-2",
    "download_data_2": "download-data-2",
    "download_torrent_2": "download-torrent-2",
    "download_scheduled_2": "download-scheduled-2",
    "download_deepweb_2": "download-deepweb-2",
    "download_images_2": "download-images-2",
    "download_software_2": "download-software-2",
    "download_ebooks_2": "download-ebooks-2",
    "download_misc_2": "download-misc-2",
    "download_cloud_3": "download-cloud-3",
    "download_ai_3": "download-ai-3",
    "download_power_3": "download-power-3",
    "download_community_3": "download-community-3",
    "download_torrent_search": "download-torrent-search",
    "download_control": "download-control",
    "download_ai_features": "download-ai-features",
    "docker_ops": "docker-ops",
    "sysadmin_tools": "sysadmin-tools",
    "network_web": "network-web",
    "database_tools": "database-tools",
    "security_hardening": "security-hardening",
    "monitoring_health": "monitoring-health",
    "media_streaming": "media-streaming",
    "backup_restore": "backup-restore",
    "dev_tools": "dev-tools",
    "ai_ml_tools": "ai-ml-tools",
    "iot_home": "iot-home",
    "email_messaging": "email-messaging",
    "voice_audio": "voice-audio",
    "document_tools": "document-tools",
    "cloud_infra": "cloud-infra",
    "data_science": "data-science",
    "gaming_tools": "gaming-tools",
    "raspberry_pi": "raspberry-pi",
    "api_integration": "api-integration",
    "productivity": "productivity",
    "education_tools": "education-tools",
    "diagnostics": "diagnostics",
    "notify": "notify",
    "calibrate": "calibrate",
    "recorder": "recorder",
    "cold_start_audit": "diagnostics",
    "network": "networking",
    "audio_smoketest": "diagnostics",
    "vision_smoketest": "diagnostics",
    "meta_cli": "meta",
    "backup": "maintenance",
    "lint": "maintenance",
    "service": "maintenance",
    "log": "meta",
    "prefs": "prefs",
    "prom": "diagnostics",
    "topic_ops": "meta",
    "node_ops": "maintenance",
    "hardware_io": "hardware",
    "train_pipeline": "training",
    "perimeter": "security",
    "power_deep": "energy",
    "voice_ops": "voice",
    "mission": "mission",
    "bench_ci": "diagnostics",
    "gamma_lint": "diagnostics",
    "ota": "maintenance",
    "ux_polish": "ui",
    "drift": "diagnostics",
    "fleet": "maintenance",
    "mission_x": "mission",
    "package_track": "maintenance",
    "phase_runner": "diagnostics",
    "tankos_setup": "installer",
    "setup_pi5": "installer",
    "provision_pi5": "installer",
}


class ToolRegistry:
    """Aggregates ToolDefinitions discovered from scripts/."""
    def __init__(self, scripts_dir):
        self.scripts_dir = Path(scripts_dir)
        self._tools = {}

    def discover(self, scripts_filter=None) -> int:
        added = 0
        for script in sorted(self.scripts_dir.glob("*.py")):
            if scripts_filter is not None and script.name not in scripts_filter:
                continue
            before = sum(1 for n in self._tools if n.startswith(script.stem + "."))
            try:
                self._index_script(script)
            except Exception as e:
                print(f"[registry] skip {script.name}: {e}", file=sys.stderr)
                continue
            after = sum(1 for n in self._tools if n.startswith(script.stem + "."))
            added += after - before
        return added

    def _index_script(self, script) -> None:
        src = script.read_text(encoding="utf-8")
        tree = ast.parse(src, filename=str(script))
        script_basename = script.stem
        cat = _CATEGORIES.get(script_basename, "general")

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith("cmd_"):
                sub = node.name[4:].replace("_", "-")
                tool_name = f"{script_basename}.{sub}"

                desc_full = ast.get_docstring(node) or f"{script_basename} {sub}"
                desc_first = (desc_full.split("\n")[0] or f"{script_basename} {sub}").strip()[:240]

                fids = _fids_in_text(desc_full)
                risk = _risk_for(sub, desc_first)

                defn = ToolDefinition(
                    name=tool_name,
                    human_name=tool_name,
                    description=desc_first,
                    script_path=str(script),
                    subcommand=sub,
                    args_schema={
                        "type": "object",
                        "properties": {
                            "dry_run": {
                                "type": "boolean",
                                "default": False,
                                "description": "If true, return synthetic payload only (no actual side-effects).",
                            },
                            "out": {
                                "type": "string",
                                "description": "Override the default output directory for this invocation.",
                            },
                        },
                    },
                    risk_tier=risk,
                    category=cat,
                    fids=fids,
                    examples=[
                        {
                            "cli": f"python3 {script.name} {sub}",
                            "curl": f"curl -X POST http://localhost:8085/invoke -H 'Authorization: Bearer $TANK_API_KEY' -d '{{\"tool\": \"{tool_name}\"}}'",
                        }
                    ],
                )
                self._tools[tool_name] = defn

    def list(self, category=None) -> list:
        if category is None:
            return list(self._tools.values())
        return [t for t in self._tools.values() if t.category == category]

    def get(self, name) -> Optional[ToolDefinition]:
        return self._tools.get(name)

    def search(self, query: str, top_k: int = 10) -> list:
        """Naive keyword search across name + description."""
        q = query.lower().split()
        scored = []
        for t in self._tools.values():
            blob = (t.name + " " + t.description + " " + t.category).lower()
            score = sum(1 for tok in q if tok in blob)
            if score > 0:
                scored.append((score, t.name))
        scored.sort(reverse=True)
        return [self._tools[name] for _, name in scored[:top_k]]

    def categories(self) -> dict:
        out = {}
        for t in self._tools.values():
            out[t.category] = out.get(t.category, 0) + 1
        return out

    def as_dict(self) -> dict:
        return {
            "schema_version": "1.0.0",
            "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
            "total_tools": len(self._tools),
            "categories": self.categories(),
            "tools": [
                {
                    "name": t.name,
                    "human_name": t.human_name,
                    "description": t.description,
                    "category": t.category,
                    "risk_tier": t.risk_tier,
                    "subcommand": t.subcommand,
                    "script_path": t.script_path,
                    "args_schema": t.args_schema,
                    "fids": t.fids,
                    "examples": t.examples,
                }
                for t in self._tools.values()
            ],
        }
