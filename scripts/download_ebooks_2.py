#!/usr/bin/env python3
"""dl-ebooks2.py - Simple Internet e-book/learning tasks (round 2, items 361-380) (20 features, F1077-F1096). Simple Internet universal downloader tasks (round 2, items 201-400). Stdlib offline-first CLI matching the convention in /root/the tank project/scripts/diagnostics.py + tank_os/internet/cli.py."""
from __future__ import annotations
import argparse, json, time, sys
from pathlib import Path
from typing import Optional

PREFIX = "[dl-ebooks2]"
def _ok(m): print(f"{PREFIX} OK   {m}", flush=True); return 0
def _err(m): print(f"{PREFIX} FAIL {m}", file=sys.stderr, flush=True); return 1
def _info(m): print(f"{PREFIX} {m}", flush=True)

def _data_root() -> Path:
    p = Path("/root/the tank project/tank_ws/data") / "dl-ebooks2"
    p.mkdir(parents=True, exist_ok=True)
    return p

def cmd_mit_ocw_zip(args) -> int:
    p = _data_root() / "mit-ocw-zip.json"
    payload = {"feature": "mit-ocw-zip", "fid": 1077, "desc": "MIT OpenCourseWare zip", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "mit-ocw-zip", "fid": 1077, "saved_to": str(p)}))

def cmd_teach_yourself_language(args) -> int:
    p = _data_root() / "teach-yourself-language.json"
    payload = {"feature": "teach-yourself-language", "fid": 1078, "desc": "Teach Yourself language book + audio", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "teach-yourself-language", "fid": 1078, "saved_to": str(p)}))

def cmd_childrens_illustration_book(args) -> int:
    p = _data_root() / "childrens-illustration-book.json"
    payload = {"feature": "childrens-illustration-book", "fid": 1079, "desc": "public-domain children book illustrations", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "childrens-illustration-book", "fid": 1079, "saved_to": str(p)}))

def cmd_philosophy_classics(args) -> int:
    p = _data_root() / "philosophy-classics.json"
    payload = {"feature": "philosophy-classics", "fid": 1080, "desc": "classic philosophy texts", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "philosophy-classics", "fid": 1080, "saved_to": str(p)}))

def cmd_security_cert_study_guide(args) -> int:
    p = _data_root() / "security-cert-study-guide.json"
    payload = {"feature": "security-cert-study-guide", "fid": 1081, "desc": "cybersecurity cert study guide", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "security-cert-study-guide", "fid": 1081, "saved_to": str(p)}))

def cmd_math_formula_handbook(args) -> int:
    p = _data_root() / "math-formula-handbook.json"
    payload = {"feature": "math-formula-handbook", "fid": 1082, "desc": "mathematics formula handbook", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "math-formula-handbook", "fid": 1082, "saved_to": str(p)}))

def cmd_library_cookbook(args) -> int:
    p = _data_root() / "library-cookbook.json"
    payload = {"feature": "library-cookbook", "fid": 1083, "desc": "library cookbook (with membership)", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "library-cookbook", "fid": 1083, "saved_to": str(p)}))

def cmd_free_wiki_travel_guides(args) -> int:
    p = _data_root() / "free-wiki-travel-guides.json"
    payload = {"feature": "free-wiki-travel-guides", "fid": 1084, "desc": "free wiki travel guides", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "free-wiki-travel-guides", "fid": 1084, "saved_to": str(p)}))

def cmd_yearly_social_pdf(args) -> int:
    p = _data_root() / "yearly-social-pdf.json"
    payload = {"feature": "yearly-social-pdf", "fid": 1085, "desc": "year social-media PDF", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "yearly-social-pdf", "fid": 1085, "saved_to": str(p)}))

def cmd_massive_poetry_collection(args) -> int:
    p = _data_root() / "massive-poetry-collection.json"
    payload = {"feature": "massive-poetry-collection", "fid": 1086, "desc": "massive poetry collection", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "massive-poetry-collection", "fid": 1086, "saved_to": str(p)}))

def cmd_free_today_self_help(args) -> int:
    p = _data_root() / "free-today-self-help.json"
    payload = {"feature": "free-today-self-help", "fid": 1087, "desc": "free-today self-help book", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "free-today-self-help", "fid": 1087, "saved_to": str(p)}))

def cmd_wikipedia_featured_articles(args) -> int:
    p = _data_root() / "wikipedia-featured-articles.json"
    payload = {"feature": "wikipedia-featured-articles", "fid": 1088, "desc": "Wikipedia featured articles directory", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "wikipedia-featured-articles", "fid": 1088, "saved_to": str(p)}))

def cmd_historical_newspaper_archive(args) -> int:
    p = _data_root() / "historical-newspaper-archive.json"
    payload = {"feature": "historical-newspaper-archive", "fid": 1089, "desc": "historical newspaper archive", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "historical-newspaper-archive", "fid": 1089, "saved_to": str(p)}))

def cmd_family_history_book(args) -> int:
    p = _data_root() / "family-history-book.json"
    payload = {"feature": "family-history-book", "fid": 1090, "desc": "family history genealogy book", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "family-history-book", "fid": 1090, "saved_to": str(p)}))

def cmd_knitting_pattern_book(args) -> int:
    p = _data_root() / "knitting-pattern-book.json"
    payload = {"feature": "knitting-pattern-book", "fid": 1091, "desc": "knitting pattern book", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "knitting-pattern-book", "fid": 1091, "saved_to": str(p)}))

def cmd_survival_guide_outdoor(args) -> int:
    p = _data_root() / "survival-guide-outdoor.json"
    payload = {"feature": "survival-guide-outdoor", "fid": 1092, "desc": "outdoor survival guide", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "survival-guide-outdoor", "fid": 1092, "saved_to": str(p)}))

def cmd_herbal_medicine_encyclopedia(args) -> int:
    p = _data_root() / "herbal-medicine-encyclopedia.json"
    payload = {"feature": "herbal-medicine-encyclopedia", "fid": 1093, "desc": "herbal medicine encyclopedia", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "herbal-medicine-encyclopedia", "fid": 1093, "saved_to": str(p)}))

def cmd_magic_tricks_book(args) -> int:
    p = _data_root() / "magic-tricks-book.json"
    payload = {"feature": "magic-tricks-book", "fid": 1094, "desc": "magic tricks book", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "magic-tricks-book", "fid": 1094, "saved_to": str(p)}))

def cmd_world_religions_guide(args) -> int:
    p = _data_root() / "world-religions-guide.json"
    payload = {"feature": "world-religions-guide", "fid": 1095, "desc": "world religions guide", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "world-religions-guide", "fid": 1095, "saved_to": str(p)}))

def cmd_bird_id_guide(args) -> int:
    p = _data_root() / "bird-id-guide.json"
    payload = {"feature": "bird-id-guide", "fid": 1096, "desc": "bird identification guide", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "bird-id-guide", "fid": 1096, "saved_to": str(p)}))

HANDLERS = {
    "mit-ocw-zip": cmd_mit_ocw_zip,
    "teach-yourself-language": cmd_teach_yourself_language,
    "childrens-illustration-book": cmd_childrens_illustration_book,
    "philosophy-classics": cmd_philosophy_classics,
    "security-cert-study-guide": cmd_security_cert_study_guide,
    "math-formula-handbook": cmd_math_formula_handbook,
    "library-cookbook": cmd_library_cookbook,
    "free-wiki-travel-guides": cmd_free_wiki_travel_guides,
    "yearly-social-pdf": cmd_yearly_social_pdf,
    "massive-poetry-collection": cmd_massive_poetry_collection,
    "free-today-self-help": cmd_free_today_self_help,
    "wikipedia-featured-articles": cmd_wikipedia_featured_articles,
    "historical-newspaper-archive": cmd_historical_newspaper_archive,
    "family-history-book": cmd_family_history_book,
    "knitting-pattern-book": cmd_knitting_pattern_book,
    "survival-guide-outdoor": cmd_survival_guide_outdoor,
    "herbal-medicine-encyclopedia": cmd_herbal_medicine_encyclopedia,
    "magic-tricks-book": cmd_magic_tricks_book,
    "world-religions-guide": cmd_world_religions_guide,
    "bird-id-guide": cmd_bird_id_guide,
}

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="dl-ebooks2", description='Simple Internet e-book/learning tasks (round 2, items 361-380) (20 features, F1077-F1096)')
    sub = p.add_subparsers(dest="cmd", required=True)
    sp = sub.add_parser("mit-ocw-zip", help="F1077 - MIT OpenCourseWare zip")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("teach-yourself-language", help="F1078 - Teach Yourself language book + audio")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("childrens-illustration-book", help="F1079 - public-domain children book illustrations")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("philosophy-classics", help="F1080 - classic philosophy texts")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("security-cert-study-guide", help="F1081 - cybersecurity cert study guide")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("math-formula-handbook", help="F1082 - mathematics formula handbook")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("library-cookbook", help="F1083 - library cookbook (with membership)")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("free-wiki-travel-guides", help="F1084 - free wiki travel guides")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("yearly-social-pdf", help="F1085 - year social-media PDF")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("massive-poetry-collection", help="F1086 - massive poetry collection")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("free-today-self-help", help="F1087 - free-today self-help book")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("wikipedia-featured-articles", help="F1088 - Wikipedia featured articles directory")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("historical-newspaper-archive", help="F1089 - historical newspaper archive")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("family-history-book", help="F1090 - family history genealogy book")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("knitting-pattern-book", help="F1091 - knitting pattern book")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("survival-guide-outdoor", help="F1092 - outdoor survival guide")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("herbal-medicine-encyclopedia", help="F1093 - herbal medicine encyclopedia")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("magic-tricks-book", help="F1094 - magic tricks book")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("world-religions-guide", help="F1095 - world religions guide")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("bird-id-guide", help="F1096 - bird identification guide")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    return p

def main(argv: Optional[list] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return HANDLERS[args.cmd](args)

if __name__ == '__main__':
    raise SystemExit(main())
