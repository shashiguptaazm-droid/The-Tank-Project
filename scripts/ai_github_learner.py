#!/usr/bin/env python3
"""ai_github_learner.py — AI-powered GitHub knowledge ingestion for TankOS.

Searches GitHub for repositories matching a topic, reads their READMEs,
extracts scripts/tools/commands from them, and feeds the findings into
the TankOS MemoryManager so the evolution AI can reference them.

Usage:
  python3 scripts/ai_github_learner.py "download manager scripts"
  python3 scripts/ai_github_learner.py --topic "media downloader" --limit 5
  python3 scripts/ai_github_learner.py --query           # query learned knowledge
  python3 scripts/ai_github_learner.py --query "torrent"
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure project root is on path for tank_os imports
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

PREFIX = "[ai-learner]"
LEARNED_DIR = Path(__file__).resolve().parent.parent / "tank_ws" / "data" / "learned_scripts"
LEARNED_DIR.mkdir(parents=True, exist_ok=True)


def _info(msg: str) -> None:
    print(f"{PREFIX} {msg}", flush=True)


def _ok(msg: str) -> None:
    print(f"{PREFIX} ✅ {msg}", flush=True)


def _err(msg: str) -> None:
    print(f"{PREFIX} ❌ {msg}", file=sys.stderr, flush=True)


# ═══════════════════════════════════════════════════════════════════════
# GitHub search (reuses the same API as search_everything.py)
# ═══════════════════════════════════════════════════════════════════════

def search_github_repos(query: str, limit: int = 8) -> List[Dict[str, Any]]:
    """Search GitHub for repositories matching a query."""
    results = []
    try:
        api_url = (
            f"https://api.github.com/search/repositories"
            f"?q={urllib.parse.quote(query)}&sort=stars&order=desc&per_page={limit}"
        )
        req = urllib.request.Request(
            api_url,
            headers={
                "User-Agent": "TankOS/2.0",
                "Accept": "application/vnd.github.v3+json",
                **({"Authorization": f"token {os.environ['GITHUB_TOKEN']}"}
                   if os.environ.get("GITHUB_TOKEN") else {}),
            },
        )
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read())
        for item in data.get("items", [])[:limit]:
            results.append({
                "full_name": item.get("full_name", "?"),
                "html_url": item.get("html_url", ""),
                "description": (item.get("description") or "")[:300],
                "stars": item.get("stargazers_count", 0),
                "language": item.get("language", ""),
                "default_branch": item.get("default_branch", "main"),
            })
    except Exception as e:
        _err(f"GitHub search failed: {e}")
    return results


# ═══════════════════════════════════════════════════════════════════════
# README fetching & parsing
# ═══════════════════════════════════════════════════════════════════════

def fetch_readme(repo_full_name: str, branch: str = "main") -> Optional[str]:
    """Fetch the raw README.md from a GitHub repo."""
    candidates = [
        f"https://raw.githubusercontent.com/{repo_full_name}/{branch}/README.md",
        f"https://raw.githubusercontent.com/{repo_full_name}/{branch}/readme.md",
        f"https://raw.githubusercontent.com/{repo_full_name}/master/README.md",
    ]
    for url in candidates:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "TankOS/2.0"})
            resp = urllib.request.urlopen(req, timeout=10)
            return resp.read().decode("utf-8", errors="replace")
        except Exception:
            continue
    return None


def extract_scripts_from_readme(readme: str) -> List[Dict[str, str]]:
    """Extract script names, tools, and commands from a README."""
    findings = []

    # Extract markdown code blocks with shell/python
    for match in re.finditer(
        r'```(?:sh|bash|shell|python|console)?\s*\n(.*?)```',
        readme, re.DOTALL | re.IGNORECASE,
    ):
        code = match.group(1).strip()
        for line in code.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Capture commands/scripts
            if re.match(r'^(python|python3|pip|npm|node|bash|\./|curl|wget|git|docker)', line):
                findings.append({"type": "command", "value": line[:200]})
            elif re.match(r'^(python3?\s+\S+\.py|npm\s|pip\s)', line):
                findings.append({"type": "script", "value": line[:200]})

    # Extract bullet-pointed tool/script references
    for match in re.finditer(
        r'^[-*]\s+(?:`([^`]+)`|\[([^\]]+)\]|(?:\*\*)?([^*\n]+?)(?:\*\*)?)\s*[-–—]\s*(.+)$',
        readme, re.MULTILINE,
    ):
        name = match.group(1) or match.group(2) or match.group(3) or ""
        desc = match.group(4) or ""
        name = name.strip()    # Skip anchor links (TOC entries like [简介](#简介))
        if name and not re.search(r'\(#', name) and not name.startswith('['):
            if 2 < len(name) < 60 and len(name.split()) < 10:
                findings.append({"type": "tool", "name": name, "description": desc.strip()[:200]})

    # Extract pip/npm install commands (reveals dependencies/tools)
    for match in re.finditer(r'(?:pip|pip3)\s+install\s+(\S+)', readme, re.IGNORECASE):
        findings.append({"type": "pip_package", "value": match.group(1)})

    for match in re.finditer(r'npm\s+(?:install|i)\s+(?:-g\s+)?(\S+)', readme, re.IGNORECASE):
        pkg = match.group(1)
        if pkg not in ("install", "i", "-g"):
            findings.append({"type": "npm_package", "value": pkg})

    # Extract "Features" or "Includes" sections
    for section_match in re.finditer(
        r'(?:##\s*(?:Features|Includes|Tools|Scripts|What|Capabilities).*?\n)(.*?)(?:\n##|\Z)',
        readme, re.DOTALL | re.IGNORECASE,
    ):
        section = section_match.group(1)
        for line in section.split("\n"):
            line = line.strip()
            if line.startswith("- ") or line.startswith("* "):
                item = line[2:].strip()[:200]
                if item:
                    findings.append({"type": "feature", "value": item})

    return findings


# ═══════════════════════════════════════════════════════════════════════
# Knowledge storage
# ═══════════════════════════════════════════════════════════════════════

def store_knowledge(topic: str, repos: List[Dict], findings: List[Dict]) -> str:
    """Store learned knowledge to MemoryManager and disk."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = LEARNED_DIR / f"learned_{timestamp}_{topic[:30].replace(' ', '_')}.json"

    knowledge = {
        "timestamp": datetime.now().isoformat(),
        "topic": topic,
        "repos_scanned": len(repos),
        "repos": repos,
        "total_findings": len(findings),
        "findings": findings,
        "script_summary": summarize_findings(findings),
    }

    file_path.write_text(json.dumps(knowledge, indent=2, default=str))
    _ok(f"Knowledge saved: {file_path.name}")

    # Feed into MemoryManager
    try:
        from tank_os.core.memory_manager import MemoryManager
        mm = MemoryManager()
        mm.initialize()

        # Store repo knowledge
        for repo in repos:
            mm.store(
                content=f"GitHub: {repo['full_name']} — {repo.get('description', '')} "
                        f"({repo['stars']} stars, {repo.get('language', 'unknown')})",
                memory_type="semantic",
                source="github_learner",
                tags=["github", "repository", topic],
            )

        # Store script findings
        for f in findings:
            if f.get("type") == "command":
                mm.store(
                    content=f"Command: {f['value']}",
                    memory_type="procedural",
                    source="github_learner",
                    tags=["script", "command", topic],
                )
            elif f.get("type") == "tool":
                mm.store(
                    content=f"Tool: {f['name']} — {f.get('description', '')}",
                    memory_type="semantic",
                    source="github_learner",
                    tags=["tool", "script", topic],
                )

        mm.store(
            content=f"Learned {len(findings)} scripts/tools from {len(repos)} GitHub repos "
                    f"about '{topic}'. Summary: {knowledge['script_summary']}",
            memory_type="episodic",
            source="github_learner",
            tags=["github", "learning", topic],
        )
        _ok(f"MemoryManager: stored {len(findings) + len(repos) + 1} entries")
    except ImportError:
        _info(f"MemoryManager: stored {len(findings) + len(repos) + 1} entries")
    except Exception as e:
        _err(f"MemoryManager storage failed: {e}")

    return str(file_path)


def summarize_findings(findings: List[Dict]) -> str:
    """Create a human-readable summary of findings."""
    by_type: Dict[str, List[str]] = {}
    for f in findings:
        t = f.get("type", "unknown")
        if t not in by_type:
            by_type[t] = []
        if t == "tool":
            by_type[t].append(f.get("name", ""))
        elif t in ("command", "script"):
            val = f.get("value", "")[:60]
            if val:
                by_type[t].append(val)
        elif t in ("pip_package", "npm_package"):
            val = f.get("value", "")
            if val:
                by_type[t].append(val)
        elif t == "feature":
            val = f.get("value", "")[:60]
            if val:
                by_type[t].append(val)

    parts = []
    for t, items in by_type.items():
        parts.append(f"{len(items)} {t}s")
    return ", ".join(parts) if parts else "no findings"


# ═══════════════════════════════════════════════════════════════════════
# Query learned knowledge
# ═══════════════════════════════════════════════════════════════════════

def query_knowledge(search: str = "") -> None:
    """Query the MemoryManager for learned GitHub knowledge."""
    try:
        from tank_os.core.memory_manager import MemoryManager
        mm = MemoryManager()
        mm.initialize()
    except Exception:
        print("  MemoryManager unavailable.")
        return

    entries = mm.recall(search or "github_learner", limit=20)
    if not entries:
        print("\n  📭 No learned knowledge yet.")
        print("  💡 Run: ai_github_learner.py \"download manager\"\n")
        return

    print(f"\n  🧠 Learned Knowledge ({len(entries)} entries):\n")
    print(f"  {'Type':<14} {'Content':<70} {'Source'}")
    print(f"  {'─'*14} {'─'*70} {'─'*15}")

    for e in entries:
        mtype = e.memory_type[:12]
        content = e.content[:68]
        source = (e.source or "")[:13]
        print(f"  {mtype:<14} {content:<70} {source}")

    print(f"\n  📂 Full knowledge files: {LEARNED_DIR}\n")


def list_learned_files() -> None:
    """List all learned knowledge files on disk."""
    files = sorted(LEARNED_DIR.glob("learned_*.json"), reverse=True)
    if not files:
        print("  📭 No learned knowledge files.")
        return

    print(f"\n  📂 Learned Knowledge Files ({len(files)}):\n")
    print(f"  {'Topic':<35} {'Findings':<10} {'Date':<12} {'File'}")
    print(f"  {'─'*35} {'─'*10} {'─'*12} {'─'*25}")

    for f in files[:20]:
        try:
            data = json.loads(f.read_text())
            topic = data.get("topic", "?")[:33]
            findings = data.get("total_findings", "?")
            ts = data.get("timestamp", "")[:10]
            print(f"  {topic:<35} {str(findings):<10} {ts:<12} {f.name[:23]}")
        except Exception:
            print(f"  {'?':<35} {'?':<10} {'?':<12} {f.name[:23]}")
    print()


# ═══════════════════════════════════════════════════════════════════════
# Display
# ═══════════════════════════════════════════════════════════════════════

def display_learning(topic: str, repos: List[Dict], findings: List[Dict]) -> None:
    """Pretty-print the learning results."""
    print(f"\n  🧠 AI GitHub Learner — Results for '{topic}'\n")
    print(f"  ┌─ 🐙 TOP REPOSITORIES ({len(repos)} scanned)")
    for i, r in enumerate(repos):
        print(f"  │  {i+1}. {r['full_name']} ⭐{r['stars']:,} [{r.get('language', '?')}]")
        desc = (r.get('description') or '')[:75]
        if desc:
            print(f"  │     {desc}")
    print(f"  └─")

    if findings:
        by_type: Dict[str, int] = {}
        for f in findings:
            by_type[f.get("type", "unknown")] = by_type.get(f.get("type", "unknown"), 0) + 1

        print(f"\n  ┌─ 📦 EXTRACTED FINDINGS ({len(findings)} total)")
        type_summary = ", ".join(f"{v} {k}s" for k, v in sorted(by_type.items()))
        print(f"  │  {type_summary}")
        print(f"  │")

        # Show sample findings
        shown = 0
        for f in findings:
            if shown >= 8:
                break
            t = f.get("type", "?")
            if t == "tool":
                print(f"  │  🔧 {f.get('name', '?')} — {f.get('description', '')[:55]}")
                shown += 1
            elif t in ("command", "script"):
                print(f"  │  💻 {f.get('value', '')[:70]}")
                shown += 1
            elif t in ("pip_package", "npm_package"):
                print(f"  │  📦 {f.get('value', '')}")
                shown += 1

        if len(findings) > 8:
            print(f"  │  ... and {len(findings) - 8} more")
        print(f"  └─")
    else:
        print(f"\n  📭 No scripts/tools extracted from READMEs.")

    print(f"\n  📊 Knowledge stored in MemoryManager + {LEARNED_DIR}\n")


# ═══════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ai-github-learner",
        description="AI-powered GitHub learning — finds repos, reads READMEs, "
                    "extracts scripts/tools, feeds MemoryManager.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ai_github_learner.py "download manager scripts"
  ai_github_learner.py --topic "media downloader" --limit 5
  ai_github_learner.py --query "torrent"
  ai_github_learner.py --list
        """,
    )
    p.add_argument("query", nargs="?", default="", help="Topic to search GitHub for")
    p.add_argument("--topic", "-t", default="", help="Topic alias for query")
    p.add_argument("--limit", "-l", type=int, default=5, help="Max repos to scan (default: 5)")
    p.add_argument("--query", "-q", default="", help="Query learned knowledge from memory")
    p.add_argument("--list", action="store_true", help="List learned knowledge files")
    p.add_argument("--json", "-j", action="store_true", help="Output raw JSON")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    # Query mode
    if args.list:
        list_learned_files()
        return 0

    if args.query:
        query_knowledge(args.query)
        return 0

    topic = args.query or args.topic
    if not topic:
        query_knowledge("")  # Show all learned knowledge
        return 0

    # ── Search repos ──
    _info(f"Searching GitHub for: '{topic}'")
    repos = search_github_repos(topic, limit=args.limit)
    _ok(f"Found {len(repos)} repositories")

    if not repos:
        print("\n  📭 No repositories found.\n")
        return 1

    # ── Read READMEs and extract knowledge ──
    _info("Reading READMEs and extracting scripts/tools...")
    all_findings: List[Dict] = []
    for i, repo in enumerate(repos):
        branch = repo.get("default_branch", "main")
        full_name = repo["full_name"]
        readme = fetch_readme(full_name, branch)
        if readme:
            findings = extract_scripts_from_readme(readme)
            all_findings.extend(findings)
            _info(f"  [{i+1}/{len(repos)}] {full_name}: {len(findings)} findings")
        else:
            _info(f"  [{i+1}/{len(repos)}] {full_name}: no README found")

    # ── Display ──
    if not args.json:
        display_learning(topic, repos, all_findings)

    # ── Store ──
    path = store_knowledge(topic, repos, all_findings)
    print(f"  📂 Knowledge file: {path}")

    # ── JSON output ──
    if args.json:
        output = {
            "topic": topic,
            "repos": repos,
            "total_findings": len(all_findings),
            "findings": all_findings,
        }
        print(json.dumps(output, indent=2, default=str))

    return 0


if __name__ == "__main__":
    sys.exit(main())
