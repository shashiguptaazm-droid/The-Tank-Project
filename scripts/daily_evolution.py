#!/usr/bin/env python3
"""daily_evolution.py — Self-evolving AI that daily learns + discovers new abilities.

Auto-Evolution pipeline:
  1. LEARN — run auto_learn on all TankOS abilities (base + discovered)
  2. DISCOVER — search GitHub for trending/new tool categories
  3. EXPAND — add new discoveries to the LIVE abilities map so they persist
  4. CHANGELOG — record what was added/updated each day
  5. REPORT — generate daily evolution summary

The abilities map is SELF-MAINTAINING: new discoveries get saved to
abilities_live.json and are used by auto_learn.py on the next cycle.

Usage:
  python3 scripts/daily_evolution.py              # full evolution cycle
  python3 scripts/daily_evolution.py --discover   # discover new abilities only
  python3 scripts/daily_evolution.py --report     # show recent evolution reports
  python3 scripts/daily_evolution.py --changelog  # show daily changelog
  python3 scripts/daily_evolution.py --list       # list current live ability map
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

PREFIX = "[evolution]"
SCRIPTS_DIR = Path(__file__).resolve().parent
AUTO_LEARN_SCRIPT = SCRIPTS_DIR / "auto_learn.py"
LEARNER_SCRIPT = SCRIPTS_DIR / "ai_github_learner.py"
APPLY_SCRIPT = SCRIPTS_DIR / "apply_learned.py"
EVOLUTION_DIR = _PROJECT_ROOT / "tank_ws" / "data" / "evolution"
EVOLUTION_DIR.mkdir(parents=True, exist_ok=True)
EVOLUTION_LOG = EVOLUTION_DIR / "evolution_log.jsonl"
ABILITIES_FILE = EVOLUTION_DIR / "discovered_abilities.json"
LIVE_ABILITIES_FILE = EVOLUTION_DIR / "abilities_live.json"  # self-maintaining map
CHANGELOG_FILE = EVOLUTION_DIR / "daily_changelog.jsonl"  # what changed each day


def _info(msg: str) -> None:
    print(f"{PREFIX} {msg}", flush=True)


def _ok(msg: str) -> None:
    print(f"{PREFIX} ✅ {msg}", flush=True)


def _sep(title: str = "") -> None:
    if title:
        print(f"\n  ═══ {title} ═══")
    else:
        print(f"  {'─'*56}")


# ═══════════════════════════════════════════════════════════════════════
# Self-maintaining ability map helpers
# ═══════════════════════════════════════════════════════════════════════

def load_live_abilities() -> Dict[str, Dict[str, Any]]:
    """Load dynamically discovered abilities from live JSON."""
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


def generate_topics_for_ability(name: str, description: str) -> List[str]:
    """Auto-generate sensible GitHub search topics for a new ability."""
    # Convert kebab-case name to readable keywords
    words = name.replace("-", " ").replace("_", " ")
    return [
        f"{words} python scripts",
        f"{words} CLI tools",
        f"{words} automation",
    ]


def add_to_live_map(name: str, description: str, repos: List[Dict]) -> bool:
    """Add a newly discovered ability to the live map. Returns True if new."""
    live = load_live_abilities()

    # Already in live map? Skip
    if name in live:
        return False

    # Check against known categories using auto_learn's hardcoded map
    try:
        sys.path.insert(0, str(SCRIPTS_DIR))
        import auto_learn as _al
        if name in _al.ABILITY_LEARNING_MAP:
            return False  # already a built-in
    except ImportError:
        pass

    # Auto-generate topics
    topics = generate_topics_for_ability(name, description)

    live[name] = {
        "description": description,
        "topics": topics,
        "shell_commands": [],
        "_source": "discovered",
        "_added": datetime.now().isoformat(),
        "_repos": repos[:3],
    }
    save_live_abilities(live)
    return True


def write_changelog_entry(added: List[Dict], updated: List[Dict],
                          removed: List[str]) -> None:
    """Write today's changelog entry."""
    entry = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "timestamp": datetime.now().isoformat(),
        "added": added,
        "updated": updated,
        "removed": removed,
    }
    with open(CHANGELOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


# ═══════════════════════════════════════════════════════════════════════
# PHASE 1: Learn existing abilities
# ═══════════════════════════════════════════════════════════════════════

def phase_learn(quick: bool = False) -> Dict[str, Any]:
    """Run auto_learn on all known TankOS abilities."""
    _sep("PHASE 1: Learning existing abilities")
    _info("Running auto_learn on all 43 abilities...")

    start = time.time()
    try:
        subprocess.run(
            ["python3", str(AUTO_LEARN_SCRIPT)],
            timeout=1200,  # 20 min max
        )
        ok = True
    except subprocess.TimeoutExpired:
        _info("⚠ Auto-learn timed out — partial results saved")
        ok = False
    except Exception as e:
        _info(f"⚠ Auto-learn failed: {e}")
        ok = False

    elapsed = time.time() - start
    return {"phase": "learn", "success": ok, "duration_s": round(elapsed, 1)}


# ═══════════════════════════════════════════════════════════════════════
# PHASE 2: Discover NEW abilities (trending repos, new categories)
# ═══════════════════════════════════════════════════════════════════════

DISCOVERY_TOPICS = [
    "trending CLI tools python 2026",
    "new automation scripts github",
    "awesome list python tools",
    "most starred python scripts 2026",
    "AI powered CLI tools",
    "linux utility tools python github",
    "home automation python scripts 2026",
    "devops automation tools python",
]

EXISTING_CATEGORIES = {
    "torrent", "video", "music", "data", "ebooks", "deepweb",
    "media", "streaming", "ai", "ml", "vision", "voice", "audio",
    "sysadmin", "docker", "cloud", "backup", "monitoring", "diagnostics",
    "security", "network", "raspberry", "iot", "home", "energy",
    "dev", "database", "api", "data-science", "gaming", "productivity",
    "document", "email", "messaging", "mobility", "robot", "surveillance",
    "mission", "patrol", "calibrate", "hardware", "maker", "creative",
    "education",
}


def classify_ability(repo_name: str, description: str) -> Optional[str]:
    """Try to classify a GitHub repo into a TankOS ability category."""
    text = f"{repo_name} {description}".lower()

    mappings = {
        "download-torrent": ["torrent", "magnet", "bittorrent"],
        "download-video": ["youtube", "video download", "yt-dlp"],
        "download-music": ["music download", "spotify", "soundcloud"],
        "ai-ml-tools": ["ai ", "llm", "gpt", "machine learning", "nlp"],
        "voice": ["tts", "speech", "voice", "whisper", "stt"],
        "vision": ["computer vision", "object detection", "camera", "ocr"],
        "media-streaming": ["streaming", "plex", "jellyfin", "media server"],
        "docker-ops": ["docker", "container", "kubernetes"],
        "sysadmin-tools": ["sysadmin", "server management", "linux admin"],
        "security-hardening": ["security", "firewall", "harden", "vpn"],
        "backup-restore": ["backup", "restore", "rsync", "snapshot"],
        "iot-home": ["iot", "mqtt", "home assistant", "sensor"],
        "raspberry-pi": ["NVIDIA Jetson", "gpio", "pico"],
        "gaming-tools": ["game", "gaming", "emulator"],
        "productivity": ["productivity", "todo", "note", "task"],
        "dev-tools": ["developer tool", "git ", "code generation", "ide"],
        "database-tools": ["database", "sql", "postgres"],
        "network-web": ["network", "web server", "proxy", "dns"],
        "api-integration": ["api ", "rest ", "graphql", "webhook"],
        "data-science": ["data science", "pandas", "numpy", "analytics"],
    }

    for ability, keywords in mappings.items():
        for kw in keywords:
            if kw in text:
                return ability

    return None  # truly new category


def phase_discover() -> Dict[str, Any]:
    """Search GitHub for trending/new tools and discover new abilities."""
    _sep("PHASE 2: Discovering new abilities")
    _info(f"Searching {len(DISCOVERY_TOPICS)} discovery topics...")

    new_abilities: Dict[str, Dict] = {}
    total_found = 0

    for topic in DISCOVERY_TOPICS:
        _info(f"Discovering: {topic}")
        try:
            result = subprocess.run(
                ["python3", str(LEARNER_SCRIPT), "--topic", topic, "--limit", "5", "--json"],
                capture_output=True, text=True, timeout=60,
            )
            if result.stdout.strip():
                try:
                    data = json.loads(result.stdout[result.stdout.index("{"):])
                    repos = data.get("repos", [])
                    for repo in repos:
                        full_name = repo.get("full_name", "")
                        desc = repo.get("description", "")
                        stars = repo.get("stars", 0)

                        # Classify into existing or new category
                        category = classify_ability(full_name, desc)
                        if category:
                            if category not in new_abilities:
                                new_abilities[category] = {"repos": [], "total_stars": 0}
                            new_abilities[category]["repos"].append({
                                "name": full_name,
                                "stars": stars,
                                "desc": desc[:120],
                            })
                            new_abilities[category]["total_stars"] += stars
                            total_found += 1
                except (json.JSONDecodeError, ValueError):
                    pass
        except subprocess.TimeoutExpired:
            _info(f"  ⏰ Timeout on '{topic}'")
        except Exception as e:
            _info(f"  ❌ Failed: {e}")

        time.sleep(1.5)  # Rate limit

    # Save discovered abilities
    if new_abilities:
        ABILITIES_FILE.write_text(json.dumps({
            "timestamp": datetime.now().isoformat(),
            "discovered": new_abilities,
            "total_repos": total_found,
        }, indent=2))

    # ── SELF-MAINTAINING: add new discoveries to live abilities map ──
    added_today: List[Dict] = []
    for category, data in new_abilities.items():
        repos = data.get("repos", [])
        top_repo = repos[0] if repos else {}
        desc = top_repo.get("desc", f"Tools for {category}")
        if add_to_live_map(category, desc, repos):
            added_today.append({
                "ability": category,
                "description": desc,
                "top_repo": top_repo.get("name", ""),
                "stars": top_repo.get("stars", 0),
            })
            _info(f"➕ ADDED to live map: {category} ({top_repo.get('name', '?')})")

    if added_today:
        write_changelog_entry(added=added_today, updated=[], removed=[])

    _ok(f"Discovered {total_found} repos across {len(new_abilities)} categories "
        f"(+{len(added_today)} new abilities added to map)")
    return {"phase": "discover", "new_categories": len(new_abilities),
            "total_repos": total_found, "abilities": new_abilities,
            "added_to_map": len(added_today)}


# ═══════════════════════════════════════════════════════════════════════
# PHASE 3: Learn from new discoveries
# ═══════════════════════════════════════════════════════════════════════

def phase_expand(discoveries: Dict[str, Any]) -> Dict[str, Any]:
    """Deep-learn from newly discovered repos."""
    abilities = discoveries.get("abilities", {})
    if not abilities:
        _info("No new abilities to expand — skipping")
        return {"phase": "expand", "topics_learned": 0}

    _sep("PHASE 3: Deep-learning new discoveries")
    learned = 0
    for ability, data in list(abilities.items())[:5]:  # Top 5 new categories
        repos = data.get("repos", [])
        if not repos:
            continue
        top_repo = repos[0]["name"]
        _info(f"Learning {ability} from {top_repo}")
        try:
            subprocess.run(
                ["python3", str(LEARNER_SCRIPT), "--topic", ability.replace("-", " "), "--limit", "3"],
                timeout=60,
            )
            learned += 1
        except Exception as e:
            _info(f"  ⚠ Failed: {e}")
        time.sleep(1)

    return {"phase": "expand", "topics_learned": learned}


# ═══════════════════════════════════════════════════════════════════════
# PHASE 4: Apply discoveries — install packages, clone repos, create wrappers
# ═══════════════════════════════════════════════════════════════════════

def phase_apply() -> Dict[str, Any]:
    """Bridge learned knowledge → installed tools.

    Runs apply_learned.py to:
      - pip install discovered packages
      - clone high-star repos into tank_ws/tools/
      - create wrapper scripts discoverable by ToolRegistry
    """
    _sep("PHASE 4: Applying discoveries to installed tools")
    _info("Installing pip packages, cloning repos, creating wrappers...")

    start = time.time()
    try:
        result = subprocess.run(
            ["python3", str(APPLY_SCRIPT), "--min-findings", "10"],
            capture_output=True, text=True, timeout=300,
        )
        # Show key output lines
        for line in result.stdout.split("\n"):
            if any(kw in line for kw in ["✅", "⚠️", "Installed", "Cloned", "wrapper",
                                           "pip packages", "repos cloned"]):
                _info(f"  {line.strip()}")
        ok = result.returncode == 0
    except subprocess.TimeoutExpired:
        _info("⚠ Apply timed out — partial results")
        ok = False
    except Exception as e:
        _info(f"⚠ Apply failed: {e}")
        ok = False

    elapsed = time.time() - start
    return {"phase": "apply", "success": ok, "duration_s": round(elapsed, 1)}


# ═══════════════════════════════════════════════════════════════════════
# Evolution Report
# ═══════════════════════════════════════════════════════════════════════

def generate_report(phases: List[Dict]) -> Dict[str, Any]:
    """Generate a daily evolution report."""
    report = {
        "timestamp": datetime.now().isoformat(),
        "phases": phases,
        "summary": {},
    }

    for p in phases:
        report["summary"][p["phase"]] = {
            k: v for k, v in p.items() if k != "phase"
        }

    return report


def save_report(report: Dict) -> None:
    """Save evolution report to log."""
    with open(EVOLUTION_LOG, "a") as f:
        f.write(json.dumps(report) + "\n")

    # Also save daily summary
    today = datetime.now().strftime("%Y%m%d")
    daily = EVOLUTION_DIR / f"evolution_{today}.json"
    daily.write_text(json.dumps(report, indent=2))


def show_report() -> None:
    """Display recent evolution reports."""
    if not EVOLUTION_LOG.exists():
        print("\n  📭 No evolution reports yet.")
        print("  💡 Run: daily_evolution.py\n")
        return

    lines = EVOLUTION_LOG.read_text().strip().split("\n")
    print(f"\n  🧬 Evolution History ({len(lines)} cycles):\n")

    for line in lines[-10:]:
        try:
            r = json.loads(line)
            ts = r.get("timestamp", "")[:19].replace("T", " ")
            summary = r.get("summary", {})
            parts = []
            for phase, data in summary.items():
                emoji = "✅" if data.get("success", True) else "⚠"
                parts.append(f"{emoji} {phase}")
            print(f"  {ts}  {' | '.join(parts)}")
        except (json.JSONDecodeError, KeyError):
            pass  # skip malformed changelog entries

    print()

    # Show discovered abilities
    if ABILITIES_FILE.exists():
        data = json.loads(ABILITIES_FILE.read_text())
        discovered = data.get("discovered", {})
        if discovered:
            print(f"  🆕 Discovered abilities ({len(discovered)}):")
            for ability, info in sorted(discovered.items()):
                repos = info.get("repos", [])
                top = repos[0]["name"] if repos else "?"
                print(f"     {ability}: {top} (+{len(repos)-1} more)")
            print()


# ═══════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════

def show_changelog() -> None:
    """Display the daily changelog of ability map changes."""
    if not CHANGELOG_FILE.exists():
        print("\n  📭 No changelog entries yet.")
        print("  💡 Run: daily_evolution.py to start the self-evolving cycle\n")
        return

    lines = CHANGELOG_FILE.read_text().strip().split("\n")
    print(f"\n  📋 Daily Evolution Changelog ({len(lines)} days):\n")
    print(f"  {'─'*70}")

    for line in lines:
        try:
            entry = json.loads(line)
            date = entry.get("date", "?")
            added = entry.get("added", [])
            if added:
                print(f"  📅 {date}  +{len(added)} new abilities:")
                for a in added:
                    name = a.get("ability", "?")
                    desc = a.get("description", "")[:60]
                    print(f"       🆕 {name:<30} {desc}")
            else:
                print(f"  📅 {date}  no changes")
        except (json.JSONDecodeError, KeyError):
            pass  # skip malformed changelog entries
    print()

    # Also show current live map size
    live = load_live_abilities()
    if live:
        print(f"  📊 Current live map: {len(live)} discovered abilities\n")


def show_live_map() -> None:
    """Display the current self-maintained ability map."""
    try:
        sys.path.insert(0, str(SCRIPTS_DIR))
        import auto_learn as _al
    except ImportError:
        print("  ❌ Cannot import auto_learn.py\n")
        return

    merged = _al.get_merged_abilities()
    live = load_live_abilities()

    print(f"\n  🧬 Self-Maintaining Ability Map\n")
    print(f"  {'─'*70}")
    print(f"  📦 Built-in:  {len(_al.ABILITY_LEARNING_MAP)} abilities")
    print(f"  🆕 Discovered: {len(live)} abilities")
    print(f"  📊 Total:      {len(merged)} abilities")
    print(f"  {'─'*70}\n")

    if live:
        print(f"  🆕 Evolved (auto-discovered):\n")
        for name, info in sorted(live.items()):
            added = info.get("_added", "unknown")[:10]
            desc = info.get("description", "")[:60]
            topics = len(info.get("topics", []))
            repos = info.get("_repos", [])
            top = repos[0]["name"] if repos else "?"
            print(f"  {name:<30} {desc}")
            print(f"  {'':30} {topics} topics | top: {top}")
            print()

    if not live:
        print(f"  💡 Run 'evolve' to auto-discover new abilities from GitHub trending.\n")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="daily-evolution",
        description="Self-evolving AI — daily learns + discovers new abilities from GitHub.\n"
                    "Maintains its own ability list, growing daily.",
    )
    p.add_argument("--discover", action="store_true",
                   help="Only run discovery phase")
    p.add_argument("--quick", action="store_true",
                   help="Quick mode: fewer topics, faster")
    p.add_argument("--report", "-r", action="store_true",
                   help="Show recent evolution reports")
    p.add_argument("--changelog", "-c", action="store_true",
                   help="Show daily changelog of ability map changes")
    p.add_argument("--list", "-l", action="store_true",
                   help="List current self-maintained ability map")
    p.add_argument("--apply", "-a", action="store_true",
                   help="Only run apply phase (install discovered tools)")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    if args.report:
        show_report()
        return 0

    if args.changelog:
        show_changelog()
        return 0

    if args.list:
        show_live_map()
        return 0

    if args.apply:
        a = phase_apply()
        report = generate_report([a])
        save_report(report)
        print(f"\n  ✅ APPLY: {a.get('success', False)}, {a.get('duration_s', 0)}s\n")
        return 0

    print(f"\n  🧬 TankOS Self-Evolution Cycle")
    print(f"  {'═'*56}")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  {'═'*56}")

    phases = []

    if args.discover:
        # Discovery only mode
        d = phase_discover()
        phases.append(d)
    else:
        # Full evolution cycle
        l = phase_learn(quick=args.quick)
        phases.append(l)

        d = phase_discover()
        phases.append(d)

        e = phase_expand(d)
        phases.append(e)

        a = phase_apply()
        phases.append(a)

    # Report
    _sep("Evolution Complete")
    report = generate_report(phases)
    save_report(report)

    # Show changelog summary if anything was added
    added_today = d.get("added_to_map", 0) if phases else 0
    if added_today:
        print(f"\n  📋 {added_today} new abilities added to self-maintaining map!")
        print(f"  💡 See full changelog: daily_evolution.py --changelog")

    # Summary
    for p in phases:
        phase_name = p["phase"]
        if phase_name == "learn":
            status = "✅" if p.get("success") else "⚠"
            print(f"  {status} LEARN:    existing abilities refreshed")
        elif phase_name == "discover":
            print(f"  ✅ DISCOVER: {p.get('new_categories', 0)} new categories, "
                  f"{p.get('total_repos', 0)} repos found")
        elif phase_name == "expand":
            print(f"  ✅ EXPAND:   {p.get('topics_learned', 0)} new topics deep-learned")

    print(f"\n  📂 Report: {EVOLUTION_DIR}")
    print(f"  🔁 Next evolution: runs daily via 'evolve' in shell\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
