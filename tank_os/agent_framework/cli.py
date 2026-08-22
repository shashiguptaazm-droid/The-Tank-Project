"""Top-level CLI for the TankOS Agent Framework.

Subcommands (mirror the HTTP surface):
  list [--category CAT]                     table view of all tools
  show <tool>                                detailed JSON view of one tool
  manifest [--format=openai|anthropic|raw|summary] [--write FILE]
  invoke <tool> [--dry-run] [--out PATH] [--timeout N]
  categories                                 histogram of tools per category
  server [--port N] [--scripts DIR] [--audit DB]
  search <query> [--limit N]                 naive keyword search

Usable as:
  python3 -m tank_os.agent_framework.cli list
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

from .registry import ToolRegistry
from .invoker import ToolInvoker
from .manifest import Manifest
from .schemas import ToolCallRequest


def _default_paths():
    return (
        Path("/root/the tank project/scripts"),
        Path("/root/the tank project/tank_ws/data/agent_audit.db"),
    )


def cmd_list(args):
    scripts_dir, _ = _default_paths()
    reg = ToolRegistry(scripts_dir=scripts_dir)
    n = reg.discover()
    print(f"# {n} tools discovered under {scripts_dir}\n", file=sys.stderr)
    tools = reg.list(category=args.category) if args.category else reg.list()
    for t in tools:
        fids_str = ",".join(f"F{f}" for f in t.fids) if t.fids else "-"
        print(f"{t.risk_tier:<6} | {t.category:<22} | {t.name:<55} | {fids_str}")
    print(f"\n{len(tools)} tools shown.")


def cmd_show(args):
    scripts_dir, _ = _default_paths()
    reg = ToolRegistry(scripts_dir=scripts_dir)
    reg.discover()
    t = reg.get(args.tool)
    if t is None:
        print(f"# unknown tool: {args.tool}", file=sys.stderr)
        return 2
    print(json.dumps(t.to_dict(), indent=2))
    return 0


def cmd_manifest(args):
    scripts_dir, _ = _default_paths()
    reg = ToolRegistry(scripts_dir=scripts_dir)
    reg.discover()
    m = Manifest(reg)
    if args.format == "openai":
        out = m.openai()
    elif args.format == "anthropic":
        out = m.anthropic()
    elif args.format == "summary":
        out = m.summary()
    else:
        out = reg.as_dict()
    text = json.dumps(out, indent=2)
    if args.write:
        Path(args.write).write_text(text)
        print(f"# wrote {args.write}", file=sys.stderr)
    else:
        print(text)
    return 0


def cmd_invoke(args):
    scripts_dir, _ = _default_paths()
    reg = ToolRegistry(scripts_dir=scripts_dir)
    reg.discover()
    cl_args = {}
    if args.dry_run:
        cl_args["dry_run"] = True
    if args.out:
        cl_args["out"] = args.out
    req = ToolCallRequest(
        tool_name=args.tool,
        args=cl_args,
        timeout_s=args.timeout,
    )
    inv = ToolInvoker(reg)
    res = inv.invoke(req)
    print(json.dumps(res.to_dict(), indent=2))
    return 0 if res.status == "ok" else 1


def cmd_categories(args):
    scripts_dir, _ = _default_paths()
    reg = ToolRegistry(scripts_dir=scripts_dir)
    reg.discover()
    cats = reg.categories()
    for c, n in sorted(cats.items(), key=lambda kv: -kv[1]):
        print(f"{n:>5}  {c}")
    print(f"\n{sum(cats.values())} total across {len(cats)} categories.")


def cmd_server(args):
    scripts_dir = Path(args.scripts) if args.scripts else _default_paths()[0]
    audit_db = Path(args.audit) if args.audit else _default_paths()[1]
    from .server import main as server_main
    server_main(scripts_dir=str(scripts_dir), audit_db=str(audit_db), port=args.port)


def cmd_search(args):
    scripts_dir, _ = _default_paths()
    reg = ToolRegistry(scripts_dir=scripts_dir)
    reg.discover()
    results = reg.search(args.query, top_k=args.limit)
    print(f"# {len(results)} matches for '{args.query}'\n", file=sys.stderr)
    for t in results:
        print(f"{t.category:<22} | {t.name:<55} | {t.description[:80]}")


HANDLERS = {
    "list": cmd_list,
    "show": cmd_show,
    "manifest": cmd_manifest,
    "invoke": cmd_invoke,
    "categories": cmd_categories,
    "server": cmd_server,
    "search": cmd_search,
}


def build_parser():
    p = argparse.ArgumentParser(
        prog="tank-agent-framework",
        description="TankOS Agent Framework — unified plugin surface for AI LLMs.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("list", help="Table view of all tools (filterable by category)")
    s.add_argument("--category", help="Filter to a single category")

    s = sub.add_parser("show", help="Detailed JSON view of a single tool")
    s.add_argument("tool", help="Tool name (dotted script.sub)")

    s = sub.add_parser("manifest", help="Emit a manifest in various formats")
    s.add_argument("--format", choices=["raw", "openai", "anthropic", "summary"],
                   default="raw")
    s.add_argument("--write", help="Write to this file path")

    s = sub.add_parser("invoke", help="Run a tool")
    s.add_argument("tool", help="Tool name (dotted script.sub)")
    s.add_argument("--dry-run", action="store_true")
    s.add_argument("--out", help="Override output directory")
    s.add_argument("--timeout", type=int, default=30)

    s = sub.add_parser("categories", help="Histogram of tools per category")

    s = sub.add_parser("server", help="Boot the FastAPI server")
    s.add_argument("--port", type=int, default=8085)
    s.add_argument("--scripts", help="Override scripts directory")
    s.add_argument("--audit", help="Override audit DB path")

    s = sub.add_parser("search", help="Keyword search across tools")
    s.add_argument("query")
    s.add_argument("--limit", type=int, default=20)

    return p


def main(argv=None):
    p = build_parser()
    args = p.parse_args(argv)
    return HANDLERS[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
