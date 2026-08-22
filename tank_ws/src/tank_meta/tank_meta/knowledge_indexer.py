"""Walk ``docs/`` (or any markdown tree) and index each ``*.md`` file.

The agent searches the knowledge table when the user asks about a topic
that's neither a code file nor a hardware component nor a past decision
(e.g. "how do I install ROS 2 Humble under Ubuntu?").
"""
from __future__ import annotations

import os
import re
from typing import Iterable, List, Optional

from .meta_store import MetaStore


DEFAULT_EXCLUDES = (".git", "node_modules", "build", "__pycache__")


def _first_heading(source: str) -> str:
    for line in source.splitlines():
        s = line.strip()
        if s.startswith("#"):
            return s.lstrip("#").strip()[:200]
    fn = os.path.basename(getattr(_first_heading, "_path", "<unknown>"))
    return fn


def _first_paragraph(source: str) -> str:
    paras: List[str] = []
    cur: List[str] = []
    for line in source.splitlines():
        s = line.strip()
        if not s:
            if cur:
                paras.append(" ".join(cur).strip())
                cur = []
                if len(paras) >= 1:
                    break
        elif s.startswith("#"):
            continue
        else:
            cur.append(s)
    if cur and not paras:
        paras.append(" ".join(cur).strip())
    return (paras[0] if paras else "")[:400]


def _extract_tags(path: str, source: str) -> List[str]:
    # Look for "Tags: foo bar" inline header in the first 50 lines.
    head = "\n".join(source.splitlines()[:50])
    m = re.search(r"(?im)^Tags?:\s*(.+)$", head)
    if m:
        return [t.strip("# ").lower() for t in m.group(1).split() if t.strip()]
    # Otherwise derive from path components.
    parts = []
    for p in path.replace(os.sep, "/").split("/"):
        if p.lower() in (".", "..", "docs", "knowledge", "notes", "readme.md"):
            continue
        parts.append(p.lower().replace(".md", ""))
    return [t for t in parts if t]


def index_markdown_file(path: str, source_tag: str = "notes"
                        ) -> Optional[dict]:
    """Build a knowledge-row dict for one markdown file. ``None`` on failure."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
    except (OSError, UnicodeDecodeError):
        return None
    title = _first_heading(text) or os.path.basename(path)
    body = _first_paragraph(text)
    tags = _extract_tags(path, text)
    kid = f"md:{os.path.basename(path)}"
    return {
        "id": kid, "title": title, "source": source_tag,
        "path": path, "text": body, "tags": tags,
    }


def iter_md_files(root: str,
                  excludes: Iterable[str] = DEFAULT_EXCLUDES) -> Iterable[str]:
    excl = tuple(excludes)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in excl]
        for fname in filenames:
            if fname.lower().endswith((".md", ".markdown")):
                yield os.path.join(dirpath, fname)


def index_directory(root: str, store: MetaStore,
                    source_tag: str = "notes",
                    verbose: bool = False) -> int:
    """Walk ``root`` for markdown and upsert each. Returns count."""
    n = 0
    for p in iter_md_files(root):
        row = index_markdown_file(p, source_tag=source_tag)
        if row is None:
            continue
        store.upsert_knowledge(
            row["id"], row["title"], row["source"],
            row["path"], row["text"], row["tags"],
        )
        n += 1
        if verbose:
            print(f"  indexed md {row['title']}")
    return n
