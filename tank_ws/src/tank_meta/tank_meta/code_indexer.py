"""Python AST-based code-file indexer for The Tank Project coding agent.

Walks a workspace root, opens every ``*.py`` file, parses it with :mod:`ast`,
and produces a :class:`tank_meta.meta_store.CodeFileRow`.

The agent can later search these rows with :meth:`MetaStore.search_code` to
answer questions like:

    "Which file handles the pan-servo GPIO?"
    "Which functions in tank_motion touch the motor driver?"

The indexer is **read-only** with respect to source files — it never writes
to anything except the supplied :class:`MetaStore`.
"""
from __future__ import annotations

import ast
import os
from typing import Iterable, List, Optional

from .meta_store import CodeFileRow, MetaStore


DEFAULT_EXCLUDES = (
    "__pycache__",
    ".git",
    "build",
    "install",
    "log",
)


def _safe_module_name(path: str, root: str) -> str:
    rel = os.path.relpath(path, root)
    rel = rel[:-3] if rel.endswith(".py") else rel  # drop ".py"
    if rel.endswith("__init__"):
        rel = rel[:-len("__init__")].rstrip("/")
    return rel.replace(os.sep, ".")


def _parse_deps(tree: ast.AST) -> List[str]:
    deps: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                deps.append(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                deps.append(node.module.split(".")[0])
    # dedupe but keep order
    seen = set()
    out: List[str] = []
    for d in deps:
        if d and d not in seen:
            seen.add(d)
            out.append(d)
    return out


def _first_docstring(tree: ast.AST) -> str:
    body = getattr(tree, "body", [])
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
        if isinstance(body[0].value.value, str):
            return body[0].value.value.strip().splitlines()[0][:200]
    return ""


def index_file(path: str, root: str) -> Optional[CodeFileRow]:
    """Index a single Python file. Returns ``None`` on parse failure."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            source = fh.read()
    except (OSError, UnicodeDecodeError):
        return None
    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError:
        return None

    functions: List[str] = []
    classes: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(node.name)
        elif isinstance(node, ast.ClassDef):
            classes.append(node.name)

    try:
        line_count = source.count("\n") + (0 if source.endswith("\n") else 1)
    except Exception:
        line_count = 0
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        mtime = 0.0

    return CodeFileRow(
        path=os.path.relpath(path, root),
        module=_safe_module_name(path, root),
        language="python",
        purpose=_first_docstring(tree) or "",
        line_count=line_count,
        last_modified=mtime,
        functions=sorted(set(functions)),
        classes=sorted(set(classes)),
        deps=_parse_deps(tree),
        source="ast",
    )


def iter_python_files(root: str,
                      excludes: Iterable[str] = DEFAULT_EXCLUDES
                      ) -> Iterable[str]:
    """Yield each ``*.py`` file under ``root``, skipping common artefacts."""
    excl = tuple(excludes)
    for dirpath, dirnames, filenames in os.walk(root):
        # prune
        dirnames[:] = [d for d in dirnames if d not in excl and not d.endswith(".egg-info")]
        for fname in filenames:
            if fname.endswith(".py"):
                yield os.path.join(dirpath, fname)


def index_directory(root: str, store: MetaStore,
                    excludes: Iterable[str] = DEFAULT_EXCLUDES,
                    verbose: bool = False) -> int:
    """Walk ``root`` and push parsed rows into ``store``. Returns count."""
    n = 0
    for path in iter_python_files(root, excludes=excludes):
        row = index_file(path, root)
        if row is None:
            continue
        store.upsert_code(row)
        n += 1
        if verbose:
            print(f"  indexed {row.module}  ({row.line_count} lines)")
    return n
