#!/usr/bin/env python3
"""auto_learn.py — AI-powered self-learning based on TankOS abilities.

Reads the TankOS tool catalog and shell commands, maps them to GitHub
search topics, then runs the AI learner to discover new scripts/tools
for each ability. Builds a comprehensive knowledge base.

SELF-MAINTAINING: Loads base abilities from hardcoded map + appends
live discoveries from tank_ws/data/evolution/abilities_live.json.
New abilities discovered by daily_evolution.py get persisted and
used on the next run — the map grows itself.

Usage:
  python3 scripts/auto_learn.py                    # learn from all abilities
  python3 scripts/auto_learn.py --category torrent  # learn one category
  python3 scripts/auto_learn.py --dry-run           # show what would be learned
  python3 scripts/auto_learn.py --list-abilities    # list all TankOS abilities

SELF-MAINTAINING: The ability map grows daily as daily_evolution.py
discovers new categories. Use 'evolve --list' to see discoveries.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure project root is on path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

PREFIX = "[auto-learn]"
LEARNER_SCRIPT = Path(__file__).resolve().parent / "ai_github_learner.py"
EVOLUTION_DIR = _PROJECT_ROOT / "tank_ws" / "data" / "evolution"
EVOLUTION_DIR.mkdir(parents=True, exist_ok=True)
LIVE_ABILITIES_FILE = EVOLUTION_DIR / "abilities_live.json"  # self-maintaining map

# ═══════════════════════════════════════════════════════════════════════
# ABILITY → LEARNING TOPIC MAPPING
# Each TankOS ability maps to GitHub search queries for new scripts/tools
# ═══════════════════════════════════════════════════════════════════════

ABILITY_LEARNING_MAP: Dict[str, Dict[str, Any]] = {
    # ── Downloads ──
    "download-torrent": {
        "description": "Torrent search & download",
        "topics": [
            "torrent downloader scripts python",
            "aria2 automation tools",
            "magnet link downloader",
        ],
        "shell_commands": ["torrent", "search"],
    },
    "download-video": {
        "description": "Video downloading from YouTube etc",
        "topics": [
            "youtube downloader script python",
            "video downloader CLI tool",
            "yt-dlp wrapper scripts",
        ],
        "shell_commands": ["search --youtube"],
    },
    "download-music": {
        "description": "Music downloading",
        "topics": [
            "music downloader python script",
            "soundcloud downloader CLI",
            "spotify downloader tool",
        ],
        "shell_commands": [],
    },
    "download-data": {
        "description": "Dataset & file downloading",
        "topics": [
            "bulk file downloader python",
            "dataset downloader script",
            "wget curl download manager",
        ],
        "shell_commands": [],
    },
    "download-ebooks": {
        "description": "Ebook downloading",
        "topics": [
            "ebook downloader python script",
            "library genesis downloader",
        ],
        "shell_commands": [],
    },
    "download-deepweb": {
        "description": "Deep web content access",
        "topics": [
            "tor onion downloader script",
            "deep web scraper python",
        ],
        "shell_commands": [],
    },

    # ── Media ──
    "media-streaming": {
        "description": "Media streaming & server",
        "topics": [
            "media server python script",
            "streaming server CLI tool",
            "plex jellyfin automation",
        ],
        "shell_commands": [],
    },
    "media": {
        "description": "Media processing & conversion",
        "topics": [
            "media converter python ffmpeg",
            "video audio converter script",
        ],
        "shell_commands": [],
    },

    # ── AI / ML ──
    "ai-ml-tools": {
        "description": "AI & ML automation tools",
        "topics": [
            "AI automation scripts python",
            "LLM wrapper tools CLI",
            "machine learning pipeline scripts",
            "openai api wrapper python",
        ],
        "shell_commands": ["ai", "model", "ask", "curiosity", "knowledge", "learning"],
    },
    "vision": {
        "description": "Computer vision & camera",
        "topics": [
            "computer vision python scripts",
            "object detection CLI tool",
            "camera automation python",
        ],
        "shell_commands": ["camera"],
    },
    "voice": {
        "description": "Voice & speech processing",
        "topics": [
            "text to speech python CLI",
            "speech recognition scripts",
            "voice assistant python tools",
        ],
        "shell_commands": [],
    },
    "voice-audio": {
        "description": "Audio processing",
        "topics": [
            "audio processing python script",
            "sound analysis CLI tool",
        ],
        "shell_commands": [],
    },

    # ── System & DevOps ──
    "sysadmin-tools": {
        "description": "System administration",
        "topics": [
            "system administration python scripts",
            "linux automation tools CLI",
            "server management scripts",
        ],
        "shell_commands": ["status", "system", "health", "ps", "env"],
    },
    "docker-ops": {
        "description": "Docker & container operations",
        "topics": [
            "docker management python script",
            "container automation tools",
        ],
        "shell_commands": [],
    },
    "cloud-infra": {
        "description": "Cloud infrastructure",
        "topics": [
            "cloud deployment python scripts",
            "infrastructure automation tools",
        ],
        "shell_commands": [],
    },
    "backup-restore": {
        "description": "Backup & restore tools",
        "topics": [
            "backup script python linux",
            "rsync backup automation",
        ],
        "shell_commands": [],
    },
    "monitoring-health": {
        "description": "System monitoring & health",
        "topics": [
            "system monitoring python script",
            "health check automation CLI",
        ],
        "shell_commands": ["health", "diag"],
    },
    "diagnostics": {
        "description": "Diagnostics & debugging",
        "topics": [
            "diagnostic scripts python",
            "debugging tools CLI",
        ],
        "shell_commands": ["diag"],
    },
    "security-hardening": {
        "description": "Security & hardening",
        "topics": [
            "security hardening scripts linux",
            "firewall automation tools",
        ],
        "shell_commands": ["security"],
    },
    "network-web": {
        "description": "Networking & web tools",
        "topics": [
            "network tools python CLI",
            "web server automation scripts",
        ],
        "shell_commands": ["network"],
    },

    # ── Hardware / IoT ──
    "raspberry-pi": {
        "description": "Jetson tools",
        "topics": [
            "NVIDIA Jetson automation scripts",
            "pi gpio python tools",
            "NVIDIA Jetson home server",
        ],
        "shell_commands": [],
    },
    "iot-home": {
        "description": "IoT & home automation",
        "topics": [
            "iot home automation python",
            "mqtt home assistant scripts",
        ],
        "shell_commands": [],
    },
    "home-automation": {
        "description": "Home automation",
        "topics": [
            "home automation python scripts",
            "smart home CLI tools",
        ],
        "shell_commands": [],
    },
    "energy": {
        "description": "Energy & power management",
        "topics": [
            "energy monitoring python",
            "power management linux scripts",
        ],
        "shell_commands": ["power"],
    },

    # ── Development ──
    "dev-tools": {
        "description": "Developer tools",
        "topics": [
            "developer tools python CLI",
            "git automation scripts",
            "code generation tools",
        ],
        "shell_commands": ["dev"],
    },
    "database-tools": {
        "description": "Database tools",
        "topics": [
            "database management python scripts",
            "sql automation CLI tools",
        ],
        "shell_commands": [],
    },
    "api-integration": {
        "description": "API integration tools",
        "topics": [
            "API integration python scripts",
            "REST API automation tools",
        ],
        "shell_commands": [],
    },
    "data-science": {
        "description": "Data science tools",
        "topics": [
            "data science automation python",
            "data pipeline scripts CLI",
        ],
        "shell_commands": [],
    },

    # ── Gaming ──
    "gaming-tools": {
        "description": "Gaming tools & utilities",
        "topics": [
            "gaming tools python scripts",
            "game automation CLI",
        ],
        "shell_commands": [],
    },
    "gaming": {
        "description": "Gaming utilities",
        "topics": [
            "game server management scripts",
            "gaming overlay tools python",
        ],
        "shell_commands": [],
    },

    # ── Productivity ──
    "productivity": {
        "description": "Productivity tools",
        "topics": [
            "productivity CLI tools python",
            "task automation scripts",
            "note taking CLI tool",
        ],
        "shell_commands": [],
    },
    "document-tools": {
        "description": "Document processing",
        "topics": [
            "document processing python scripts",
            "PDF manipulation CLI tools",
        ],
        "shell_commands": [],
    },
    "email-messaging": {
        "description": "Email & messaging",
        "topics": [
            "email automation python scripts",
            "messaging bot CLI tool",
        ],
        "shell_commands": [],
    },

    # ── Navigation & Robotics ──
    "mobility": {
        "description": "Robot navigation & mobility",
        "topics": [
            "robot navigation python scripts",
            "SLAM ROS automation tools",
        ],
        "shell_commands": ["nav", "patrol"],
    },
    "outdoor-security": {
        "description": "Outdoor security",
        "topics": [
            "surveillance camera python scripts",
            "motion detection automation",
        ],
        "shell_commands": [],
    },
    "mission": {
        "description": "Mission & patrol planning",
        "topics": [
            "mission planning python scripts",
            "patrol automation tools",
        ],
        "shell_commands": ["patrol"],
    },
    "calibrate": {
        "description": "Sensor calibration",
        "topics": [
            "sensor calibration python script",
            "camera calibration tools",
        ],
        "shell_commands": [],
    },
    "hardware": {
        "description": "Hardware interfaces",
        "topics": [
            "hardware interface python scripts",
            "GPIO sensor automation",
        ],
        "shell_commands": [],
    },

    # ── General ──
    "general": {
        "description": "General utility scripts",
        "topics": [
            "useful python CLI scripts",
            "linux utility scripts collection",
            "awesome command line tools",
        ],
        "shell_commands": ["help"],
    },
    "maker": {
        "description": "Maker & DIY tools",
        "topics": [
            "maker DIY python scripts",
            "arduino NVIDIA Jetson projects",
        ],
        "shell_commands": [],
    },
    "creativity": {
        "description": "Creative tools",
        "topics": [
            "creative coding python scripts",
            "generative art tools CLI",
        ],
        "shell_commands": [],
    },
    "education": {
        "description": "Educational tools",
        "topics": [
            "educational tools python CLI",
            "learning platform scripts",
        ],
        "shell_commands": [],
    },
    "education-tools": {
        "description": "Learning & education",
        "topics": [
            "educational python scripts collection",
            "quiz learning automation tools",
        ],
        "shell_commands": [],
    },
}


def _info(msg: str) -> None:
    print(f"{PREFIX} {msg}", flush=True)


def _ok(msg: str) -> None:
    print(f"{PREFIX} ✅ {msg}", flush=True)


# ═══════════════════════════════════════════════════════════════════════
# Self-maintaining ability map: load live + merge with base
# ═══════════════════════════════════════════════════════════════════════

def load_live_abilities() -> Dict[str, Dict[str, Any]]:
    """Load dynamically discovered abilities from the live JSON file."""
    if not LIVE_ABILITIES_FILE.exists():
        return {}
    try:
        data = json.loads(LIVE_ABILITIES_FILE.read_text())
        return data.get("abilities", {})
    except (json.JSONDecodeError, KeyError):
        return {}


def save_live_abilities(abilities: Dict[str, Dict[str, Any]]) -> None:
    """Persist the live ability map to JSON."""
    payload = {
        "updated": datetime.now().isoformat(),
        "total_abilities": len(abilities),
        "abilities": abilities,
    }
    LIVE_ABILITIES_FILE.write_text(json.dumps(payload, indent=2))


def get_merged_abilities() -> Dict[str, Dict[str, Any]]:
    """Return the full ability map: base hardcoded + live discoveries.

    Live abilities take priority for keys that exist in both.
    Flags evolved entries with '_source': 'discovered'.
    """
    merged = dict(ABILITY_LEARNING_MAP)  # start with hardcoded base
    live = load_live_abilities()
    for key, info in live.items():
        info["_source"] = "discovered"  # mark as auto-discovered
        merged[key] = info  # overwrite or add
    return merged


# ═══════════════════════════════════════════════════════════════════════
# Discovery: list all TankOS abilities
# ═══════════════════════════════════════════════════════════════════════

def list_abilities() -> None:
    """Print all TankOS abilities and their learning topics."""
    abilities = get_merged_abilities()
    live = load_live_abilities()

    print(f"\n  🧠 TankOS Abilities → Learning Topics\n")
    print(f"  {'Ability':<30} {'Topics':<10} {'Source':<12} {'Shell Cmds'}")
    print(f"  {'─'*30} {'─'*10} {'─'*12} {'─'*20}")

    total_topics = 0
    for ability, info in sorted(abilities.items()):
        n_topics = len(info["topics"])
        total_topics += n_topics
        source = "🆕 discovered" if ability in live else "📦 built-in"
        cmds = ", ".join(info.get("shell_commands", [])[:3]) or "—"
        print(f"  {ability:<30} {n_topics:<10} {source:<12} {cmds:<20}")

    print(f"\n  📊 {len(abilities)} abilities → {total_topics} total learning topics")
    print(f"     ({len(ABILITY_LEARNING_MAP)} built-in + {len(live)} discovered)\n")


# ═══════════════════════════════════════════════════════════════════════
# Auto-learner: runs the learner script on each topic
# ═══════════════════════════════════════════════════════════════════════

def learn_ability(ability: str, info: Dict[str, Any], dry_run: bool = False) -> int:
    """Run the AI learner on all topics for one ability."""
    found = 0
    for topic in info["topics"]:
        if dry_run:
            _info(f"[DRY RUN] {ability}: would learn '{topic}'")
            continue

        _info(f"Learning [{ability}]: {topic}")
        try:
            result = subprocess.run(
                ["python3", str(LEARNER_SCRIPT), "--topic", topic, "--limit", "3"],
                capture_output=True, text=True, timeout=60,
            )
            # Count findings from output
            for line in result.stdout.split("\n"):
                if "total_findings" in line or "📦" in line:
                    _info(f"  {line.strip()[:100]}")
            if result.stdout.strip():
                found += 1
        except subprocess.TimeoutExpired:
            _info(f"  ⏰ Timeout on '{topic}'")
        except Exception as e:
            _info(f"  ❌ Failed: {e}")

        time.sleep(1)  # Rate-limit GitHub API

    return found


def learn_all(dry_run: bool = False, category: Optional[str] = None) -> None:
    """Run the learner on all (or one) TankOS abilities."""
    abilities = get_merged_abilities()  # use self-maintaining map

    if category:
        if category not in abilities:
            print(f"\n  ❌ Unknown ability: '{category}'")
            close = [a for a in abilities if category.lower() in a.lower()]
            if close:
                print(f"  Did you mean: {', '.join(close)}?")
            print(f"  Use --list-abilities to see all options.\n")
            return
        abilities = {category: abilities[category]}

    mode = "DRY RUN — " if dry_run else ""
    print(f"\n  🧠 {mode}Auto-Learning from TankOS Abilities\n")
    print(f"  {'─'*56}")
    print(f"  Abilities: {len(abilities)}")
    print(f"  Topics:    {sum(len(v['topics']) for v in abilities.values())}")
    print(f"  Mode:      {'dry-run (no API calls)' if dry_run else 'live learning'}")
    print(f"  {'─'*56}\n")

    start = time.time()
    total_found = 0
    for ability, info in sorted(abilities.items()):
        found = learn_ability(ability, info, dry_run=dry_run)
        total_found += found
        if not dry_run and found:
            _ok(f"{ability}: {found} topics with findings")

    elapsed = time.time() - start

    if dry_run:
        print(f"\n  📊 Would search {sum(len(v['topics']) for v in abilities.values())} topics "
              f"across {len(abilities)} categories.\n")
    else:
        print(f"\n  📊 Learned from {total_found}/{sum(len(v['topics']) for v in abilities.values())} "
              f"topics in {elapsed:.0f}s\n")

    # Show what was learned
    if not dry_run:
        try:
            subprocess.run(
                ["python3", str(LEARNER_SCRIPT), "--list"],
                timeout=10,
            )
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="auto-learn",
        description="AI self-learning from TankOS abilities — "
                    "auto-generates GitHub learning queries from tool catalog.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  auto_learn.py --list-abilities     # Show all TankOS abilities
  auto_learn.py --dry-run            # Preview what would be learned
  auto_learn.py                      # Learn from ALL abilities
  auto_learn.py --category torrent   # Learn one category only
        """,
    )
    p.add_argument("--category", "-c", default=None,
                   help="Learn from one ability category only")
    p.add_argument("--dry-run", "-n", action="store_true",
                   help="Show what would be learned without making API calls")
    p.add_argument("--list-abilities", action="store_true",
                   help="List all TankOS abilities and their learning topics")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    if args.list_abilities:
        list_abilities()
        return 0

    learn_all(dry_run=args.dry_run, category=args.category)
    return 0


if __name__ == "__main__":
    sys.exit(main())
