#!/usr/bin/env python3
"""apply_learned.py — Bridge learned GitHub knowledge into installed tools.

Reads learned_scripts JSON files, extracts actionable items:
  1. pip packages → pip install (safe, user-visible)
  2. git repos → clone into tank_ws/tools/
  3. commands/scripts → create wrapper scripts (discoverable by ToolRegistry)

State is tracked in tank_ws/data/evolution/applied_state.json
so nothing gets double-installed.

Usage:
  python3 scripts/apply_learned.py              # apply all un-applied learnings
  python3 scripts/apply_learned.py --dry-run    # preview what would be applied
  python3 scripts/apply_learned.py --status     # show what's been applied
  python3 scripts/apply_learned.py --recent 5   # apply 5 most recent learnings
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

PREFIX = "[apply-learned]"
LEARNED_DIR = _PROJECT_ROOT / "tank_ws" / "data" / "learned_scripts"
TOOLS_DIR = _PROJECT_ROOT / "tank_ws" / "tools"
SCRIPTS_TOOLS_DIR = _PROJECT_ROOT / "scripts" / "tools"
EVOLUTION_DIR = _PROJECT_ROOT / "tank_ws" / "data" / "evolution"
STATE_FILE = EVOLUTION_DIR / "applied_state.json"

# Packages that are potentially dangerous or already system-critical
SKIP_PACKAGES = {
    "os", "sys", "time", "json", "re", "random", "math", "collections",
    "typing", "pathlib", "datetime", "subprocess", "argparse", "logging",
    "threading", "multiprocessing", "socket", "http", "urllib",
    "pip", "setuptools", "wheel", "pytest", "python", "python3",
}

# Minimum stars to clone a repo
MIN_STARS_TO_CLONE = 100

# Maximum pip packages to auto-install per run (safety limit)
MAX_PIP_INSTALLS = 5


def _info(msg: str) -> None:
    print(f"{PREFIX} {msg}", flush=True)


def _ok(msg: str) -> None:
    print(f"{PREFIX} ✅ {msg}", flush=True)


def _warn(msg: str) -> None:
    print(f"{PREFIX} ⚠️  {msg}", flush=True)


def _err(msg: str) -> None:
    print(f"{PREFIX} ❌ {msg}", file=sys.stderr, flush=True)


# ═══════════════════════════════════════════════════════════════════════
# State management — track what's been applied to avoid duplicates
# ═══════════════════════════════════════════════════════════════════════

def load_state() -> Dict[str, Any]:
    """Load applied state from disk."""
    if not STATE_FILE.exists():
        return {"pip_installed": [], "repos_cloned": [], "wrappers_created": [],
                "files_processed": [], "last_run": None}
    try:
        return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, KeyError):
        return {"pip_installed": [], "repos_cloned": [], "wrappers_created": [],
                "files_processed": [], "last_run": None}


def save_state(state: Dict[str, Any]) -> None:
    """Persist applied state to disk."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    state["last_run"] = datetime.now().isoformat()
    STATE_FILE.write_text(json.dumps(state, indent=2, default=str))


# ═══════════════════════════════════════════════════════════════════════
# Extract actionable items from learned knowledge files
# ═══════════════════════════════════════════════════════════════════════

def extract_pip_packages(findings: List[Dict]) -> List[str]:
    """Extract unique, safe pip package names from findings."""
    import re as _re
    packages = []
    seen = set()
    # Valid pip package name: must match PEP 508 name pattern
    VALID_PKG = _re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9._-]*$')
    for f in findings:
        if f.get("type") == "pip_package":
            raw = f.get("value", "").strip()
            # Strip trailing backticks, quotes, parentheses from README parse noise
            pkg = _re.sub(r'[`"' + "'" + r')\]]+$', '', raw).strip().lower()
            # Remove version/extras specifiers
            pkg = pkg.split("==")[0].split(">=")[0].split("<=")[0].split("~=")[0].split("[")[0].strip()
            # Validate: must look like a real package name
            if (pkg and VALID_PKG.match(pkg)
                    and pkg not in seen
                    and len(pkg) > 1
                    and not pkg.startswith("-")
                    and not pkg.startswith("<")
                    and pkg not in ("pip", "setuptools", "wheel", "python", "python3", "requirements")):
                packages.append(pkg)
                seen.add(pkg)
    return packages


def extract_repos_to_clone(learned_data: Dict) -> List[Dict]:
    """Extract repos worth cloning (high stars, significant findings)."""
    repos = learned_data.get("repos", [])
    total_findings = learned_data.get("total_findings", 0)

    candidates = []
    for repo in repos:
        stars = repo.get("stars", 0)
        if stars >= MIN_STARS_TO_CLONE and total_findings >= 10:
            candidates.append({
                "full_name": repo.get("full_name", ""),
                "url": repo.get("html_url", f"https://github.com/{repo.get('full_name', '')}"),
                "stars": stars,
                "language": repo.get("language", ""),
                "description": (repo.get("description", "") or "")[:100],
            })
    return candidates


def extract_commands(findings: List[Dict]) -> List[str]:
    """Extract CLI-friendly commands from findings."""
    commands = []
    seen = set()
    for f in findings:
        if f.get("type") in ("command", "script"):
            cmd = f.get("value", "").strip()
            if cmd and cmd not in seen and len(cmd) < 300:
                commands.append(cmd)
                seen.add(cmd)
    return commands


def extract_tools(findings: List[Dict]) -> List[Dict]:
    """Extract named tools from findings, filtering out README parse noise."""
    import re as _re
    tools = []
    seen = set()
    # Names that are clearly not real tool names
    NOISE_PATTERNS = [
        _re.compile(r'^https?://'),       # URLs
        _re.compile(r'<[^>]+>'),           # HTML tags
        _re.compile(r'\.\.\.$'),          # Trailing ellipsis  
        _re.compile(r'^[`' + "'" + r'"\[\](){}]'),  # Starts with punctuation
        _re.compile(r'^\d{4}$'),           # Just a year
        _re.compile(r'^[a-z]:'),           # Drive letters
    ]
    for f in findings:
        if f.get("type") != "tool":
            continue
        name = f.get("name", "").strip()
        desc = f.get("description", "").strip()
        # Skip garbage names
        if not name or name in seen:
            continue
        if len(name) < 3 or len(name) > 35:
            continue
        if any(p.search(name) for p in NOISE_PATTERNS):
            continue
        # Name should have at least one letter
        if not _re.search(r'[a-zA-Z]', name):
            continue
        # Name should be mostly normal characters
        weird_chars = sum(1 for c in name if c in ':;.,<>/\\?|[]{}()!@#$%^&*+=`~')
        if weird_chars > 2:
            continue
        tools.append({"name": name, "description": desc})
        seen.add(name)
    return tools


# ═══════════════════════════════════════════════════════════════════════
# Apply actions: install pip packages, clone repos, create wrappers
# ═══════════════════════════════════════════════════════════════════════

def apply_pip_install(packages: List[str], state: Dict, dry_run: bool = False) -> int:
    """Install pip packages. Skips already-installed and already-applied."""
    installed = set(state.get("pip_installed", []))
    to_install = [p for p in packages if p not in installed]

    if not to_install:
        return 0

    # Deduplicate (just in case)
    to_install = list(dict.fromkeys(to_install))
    # Limit batch size
    to_install = to_install[:MAX_PIP_INSTALLS]

    if dry_run:
        print(f"\n  📦 Would pip install ({len(to_install)}):")
        for p in to_install:
            print(f"     pip install {p}")
        return 0

    installed_count = 0
    for pkg in to_install:
        _info(f"pip install {pkg} ...")
        try:
            result = subprocess.run(
                ["pip", "install", pkg, "--break-system-packages", "--quiet"],
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode == 0:
                _ok(f"Installed: {pkg}")
                state.setdefault("pip_installed", []).append(pkg)
                installed_count += 1
            else:
                err_msg = result.stderr.strip()[-120:] if result.stderr else "unknown error"
                _warn(f"Failed: {pkg} — {err_msg}")
        except subprocess.TimeoutExpired:
            _warn(f"Timeout: {pkg}")
        except Exception as e:
            _warn(f"Error installing {pkg}: {e}")

    return installed_count


def apply_clone_repos(repos: List[Dict], state: Dict, dry_run: bool = False) -> int:
    """Clone repos into tank_ws/tools/. Skips already-cloned."""
    TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    cloned_set = set(state.get("repos_cloned", []))
    to_clone = [r for r in repos if r["full_name"] not in cloned_set]

    # Deduplicate by full_name within this run
    seen = set()
    unique = []
    for r in to_clone:
        if r["full_name"] not in seen:
            seen.add(r["full_name"])
            unique.append(r)
    to_clone = unique

    if not to_clone:
        return 0

    if dry_run:
        print(f"\n  🐙 Would clone ({len(to_clone)}):")
        for r in to_clone:
            print(f"     git clone {r['url']} → tools/{r['full_name'].split('/')[-1]}")
        return 0

    cloned_count = 0
    for repo in to_clone:
        repo_name = repo["full_name"].split("/")[-1]
        target = TOOLS_DIR / repo_name
        if target.exists():
            _info(f"Already exists: {repo_name}")
            continue

        _info(f"Cloning {repo['full_name']} ({repo['stars']:,}⭐)...")
        try:
            result = subprocess.run(
                ["git", "clone", "--depth", "1", repo["url"], str(target)],
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode == 0:
                _ok(f"Cloned: {repo_name}")
                state.setdefault("repos_cloned", []).append(repo["full_name"])
                cloned_count += 1
            else:
                _warn(f"Clone failed: {repo_name}")
        except subprocess.TimeoutExpired:
            _warn(f"Clone timeout: {repo_name}")
        except Exception as e:
            _warn(f"Clone error {repo_name}: {e}")

    return cloned_count


def apply_create_wrappers(tools: List[Dict], commands: List[str],
                          topic: str, state: Dict,
                          dry_run: bool = False) -> int:
    """Create discoverable wrapper scripts in scripts/tools/ for ToolRegistry."""
    SCRIPTS_TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    created_set = set(state.get("wrappers_created", []))

    created_count = 0

    # Create standalone wrapper scripts for meaningful tools
    for tool in tools[:5]:  # Max 5 wrappers per run
        name = tool["name"].lower().replace(" ", "_").replace("-", "_")[:40]
        wrapper_name = f"tool_{name}.py"

        if wrapper_name in created_set:
            continue

        desc = tool.get("description", f"Discovered tool: {name}")

        if dry_run:
            print(f"     Would create wrapper: scripts/tools/{wrapper_name}")
            continue

        wrapper_content = f'''#!/usr/bin/env python3
"""Wrapper for discovered tool: {name}

Topic: {topic}
Description: {desc}
Auto-generated by apply_learned.py on {datetime.now().strftime("%Y-%m-%d %H:%M")}
"""
# This wrapper makes the tool discoverable by TankOS ToolRegistry.
# To fully activate: implement the tool's actual functionality.

def main():
    print("🚀 Discovered tool: {name}")
    print("   {desc}")
    print()
    print("   💡 This tool was auto-discovered from GitHub.")
    print("   To activate: clone the repo → install deps → wire into this wrapper.")

if __name__ == "__main__":
    main()
'''

        wrapper_path = SCRIPTS_TOOLS_DIR / wrapper_name
        if not wrapper_path.exists():
            wrapper_path.write_text(wrapper_content)
            wrapper_path.chmod(0o755)
            state.setdefault("wrappers_created", []).append(wrapper_name)
            created_count += 1
            _info(f"Created wrapper: scripts/tools/{wrapper_name}")

    return created_count


# ═══════════════════════════════════════════════════════════════════════
# Main apply loop
# ═══════════════════════════════════════════════════════════════════════

def apply_learned(dry_run: bool = False, recent: Optional[int] = None,
                  min_findings: int = 10) -> Dict[str, Any]:
    """Process learned knowledge files and apply discoveries."""

    if not LEARNED_DIR.exists():
        _err(f"No learned data at {LEARNED_DIR}")
        return {"error": "No learned data directory"}

    files = sorted(LEARNED_DIR.glob("learned_*.json"), reverse=True)
    if not files:
        _err("No learned knowledge files found")
        return {"error": "No files"}

    state = load_state()
    processed = set(state.get("files_processed", []))

    # Filter to unprocessed files
    to_process = [f for f in files if f.name not in processed]
    if recent:
        to_process = to_process[:recent]

    if not to_process:
        _ok("All learned files already applied!")
        return {"applied": 0, "status": "up_to_date"}

    mode = "DRY RUN — " if dry_run else ""
    print(f"\n  🔧 {mode}Applying Learned Knowledge\n")
    print(f"  {'─'*56}")
    print(f"  Files to process:  {len(to_process)}"
          f"{f' (most recent {recent})' if recent else ''}")
    print(f"  Previously applied: {len(processed)}")
    print(f"  {'─'*56}")

    total_pip = 0
    total_cloned = 0
    total_wrappers = 0

    for file_path in to_process:
        try:
            data = json.loads(file_path.read_text())
        except (json.JSONDecodeError, OSError):
            _warn(f"Skipping unreadable: {file_path.name}")
            continue

        topic = data.get("topic", file_path.stem)
        findings = data.get("findings", [])
        total_findings = data.get("total_findings", 0)

        if total_findings < min_findings:
            continue  # Skip low-signal learnings

        _info(f"Processing: {topic} ({total_findings} findings)")

        # 1. Install pip packages
        pip_pkgs = extract_pip_packages(findings)
        if pip_pkgs:
            n = apply_pip_install(pip_pkgs, state, dry_run=dry_run)
            total_pip += n

        # 2. Clone repos (only if significant)
        repos = extract_repos_to_clone(data)
        if repos:
            n = apply_clone_repos(repos, state, dry_run=dry_run)
            total_cloned += n

        # 3. Create wrapper scripts for tools
        tools = extract_tools(findings)
        commands = extract_commands(findings)
        if tools or commands:
            n = apply_create_wrappers(tools, commands, topic, state, dry_run=dry_run)
            total_wrappers += n

        if not dry_run:
            state.setdefault("files_processed", []).append(file_path.name)

    # Save state
    if not dry_run:
        save_state(state)

    summary = {
        "pip_installed": total_pip,
        "repos_cloned": total_cloned,
        "wrappers_created": total_wrappers,
        "files_processed": len(to_process) if not dry_run else 0,
        "dry_run": dry_run,
    }

    print(f"\n  {'─'*56}")
    if dry_run:
        print(f"  📋 DRY RUN — nothing was actually installed")
    print(f"  📦 pip packages installed: {total_pip}")
    print(f"  🐙 repos cloned:          {total_cloned}")
    print(f"  📝 wrappers created:      {total_wrappers}")
    print(f"  {'─'*56}\n")

    return summary


def show_status() -> None:
    """Display what's been applied so far."""
    state = load_state()

    print(f"\n  📊 Applied Knowledge Status\n")
    print(f"  {'─'*56}")

    last = state.get("last_run", "never")
    print(f"  Last run:     {last[:19] if last else 'never'}")
    print(f"  Pip packages: {len(state.get('pip_installed', []))}")
    print(f"  Repos cloned: {len(state.get('repos_cloned', []))}")
    print(f"  Wrappers:     {len(state.get('wrappers_created', []))}")
    print(f"  Files done:   {len(state.get('files_processed', []))}")

    # Show what's installed
    pip = state.get("pip_installed", [])
    if pip:
        print(f"\n  📦 Installed packages:")
        for p in pip[-10:]:
            print(f"     {p}")

    repos = state.get("repos_cloned", [])
    if repos:
        print(f"\n  🐙 Cloned repos:")
        for r in repos[-5:]:
            print(f"     {r}")

    wrappers = state.get("wrappers_created", [])
    if wrappers:
        print(f"\n  📝 Created wrappers:")
        for w in wrappers[-10:]:
            print(f"     scripts/tools/{w}")

    # Show what's still pending
    files = sorted(LEARNED_DIR.glob("learned_*.json"), reverse=True) if LEARNED_DIR.exists() else []
    processed = set(state.get("files_processed", []))
    pending = [f for f in files if f.name not in processed]
    print(f"\n  ⏳ Pending:     {len(pending)} files not yet applied")
    print()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="apply-learned",
        description="Bridge learned GitHub knowledge → installed tools. "
                    "Reads learned_scripts JSON, installs pip packages, "
                    "clones repos, creates discoverable wrapper scripts.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  apply_learned.py                  # Apply all un-applied learnings
  apply_learned.py --dry-run        # Preview what would be applied
  apply_learned.py --status         # Show applied state
  apply_learned.py --recent 5       # Apply 5 most recent learnings only
        """,
    )
    p.add_argument("--dry-run", "-n", action="store_true",
                   help="Preview without making changes")
    p.add_argument("--status", "-s", action="store_true",
                   help="Show applied state and pending files")
    p.add_argument("--recent", "-r", type=int, default=None,
                   help="Only apply N most recent learned files")
    p.add_argument("--min-findings", "-m", type=int, default=10,
                   help="Minimum findings required to process a file (default: 10)")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    if args.status:
        show_status()
        return 0

    result = apply_learned(
        dry_run=args.dry_run,
        recent=args.recent,
        min_findings=args.min_findings,
    )

    if result.get("error"):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
