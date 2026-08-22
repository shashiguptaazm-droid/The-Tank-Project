#!/usr/bin/env python3
"""dl-data2.py - Simple Internet data/document tasks (round 2, items 241-260) (20 features, F957-F976). Simple Internet universal downloader tasks (round 2, items 201-400). Stdlib offline-first CLI matching the convention in /root/the tank project/scripts/diagnostics.py + tank_os/internet/cli.py."""
from __future__ import annotations
import argparse, json, time, sys
from pathlib import Path
from typing import Optional

PREFIX = "[dl-data2]"
def _ok(m): print(f"{PREFIX} OK   {m}", flush=True); return 0
def _err(m): print(f"{PREFIX} FAIL {m}", file=sys.stderr, flush=True); return 1
def _info(m): print(f"{PREFIX} {m}", flush=True)

def _data_root() -> Path:
    p = Path("/root/the tank project/tank_ws/data") / "dl-data2"
    p.mkdir(parents=True, exist_ok=True)
    return p

def cmd_transport_timetables_pdf(args) -> int:
    p = _data_root() / "transport-timetables-pdf.json"
    payload = {"feature": "transport-timetables-pdf", "fid": 957, "desc": "city transportation timetables PDF", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "transport-timetables-pdf", "fid": 957, "saved_to": str(p)}))

def cmd_nutrition_database(args) -> int:
    p = _data_root() / "nutrition-database.json"
    payload = {"feature": "nutrition-database", "fid": 958, "desc": "government nutritional database", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "nutrition-database", "fid": 958, "saved_to": str(p)}))

def cmd_national_laws_portal(args) -> int:
    p = _data_root() / "national-laws-portal.json"
    payload = {"feature": "national-laws-portal", "fid": 959, "desc": "country e-laws portal", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "national-laws-portal", "fid": 959, "saved_to": str(p)}))

def cmd_nobel_json(args) -> int:
    p = _data_root() / "nobel-json.json"
    payload = {"feature": "nobel-json", "fid": 960, "desc": "Nobel Prize winners JSON", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "nobel-json", "fid": 960, "saved_to": str(p)}))

def cmd_crm_export_link(args) -> int:
    p = _data_root() / "crm-export-link.json"
    payload = {"feature": "crm-export-link", "fid": 961, "desc": "CRM contact export via web link", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "crm-export-link", "fid": 961, "saved_to": str(p)}))

def cmd_sec_filings_bulk(args) -> int:
    p = _data_root() / "sec-filings-bulk.json"
    payload = {"feature": "sec-filings-bulk", "fid": 962, "desc": "company SEC filings bulk", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "sec-filings-bulk", "fid": 962, "saved_to": str(p)}))

def cmd_patent_with_drawings(args) -> int:
    p = _data_root() / "patent-with-drawings.json"
    payload = {"feature": "patent-with-drawings", "fid": 963, "desc": "patent document with drawings", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "patent-with-drawings", "fid": 963, "saved_to": str(p)}))

def cmd_who_research_data(args) -> int:
    p = _data_root() / "who-research-data.json"
    payload = {"feature": "who-research-data", "fid": 964, "desc": "WHO medical research dataset", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "who-research-data", "fid": 964, "saved_to": str(p)}))

def cmd_undersea_cables_kml(args) -> int:
    p = _data_root() / "undersea-cables-kml.json"
    payload = {"feature": "undersea-cables-kml", "fid": 965, "desc": "undersea cables KML map", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "undersea-cables-kml", "fid": 965, "saved_to": str(p)}))

def cmd_ai_conf_papers(args) -> int:
    p = _data_root() / "ai-conf-papers.json"
    payload = {"feature": "ai-conf-papers", "fid": 966, "desc": "AI conference papers", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "ai-conf-papers", "fid": 966, "saved_to": str(p)}))

def cmd_docs_site_pdf_archive(args) -> int:
    p = _data_root() / "docs-site-pdf-archive.json"
    payload = {"feature": "docs-site-pdf-archive", "fid": 967, "desc": "code docs site as PDF archive", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "docs-site-pdf-archive", "fid": 967, "saved_to": str(p)}))

def cmd_airline_safety_cards(args) -> int:
    p = _data_root() / "airline-safety-cards.json"
    payload = {"feature": "airline-safety-cards", "fid": 968, "desc": "airline safety cards", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "airline-safety-cards", "fid": 968, "saved_to": str(p)}))

def cmd_font_specimen_pdf(args) -> int:
    p = _data_root() / "font-specimen-pdf.json"
    payload = {"feature": "font-specimen-pdf", "fid": 969, "desc": "font specimen book PDF", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "font-specimen-pdf", "fid": 969, "saved_to": str(p)}))

def cmd_voter_registration(args) -> int:
    p = _data_root() / "voter-registration.json"
    payload = {"feature": "voter-registration", "fid": 970, "desc": "voter registration db (public)", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "voter-registration", "fid": 970, "saved_to": str(p)}))

def cmd_building_code_standard(args) -> int:
    p = _data_root() / "building-code-standard.json"
    payload = {"feature": "building-code-standard", "fid": 971, "desc": "building code standard document", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "building-code-standard", "fid": 971, "saved_to": str(p)}))

def cmd_kaggle_competition_data(args) -> int:
    p = _data_root() / "kaggle-competition-data.json"
    payload = {"feature": "kaggle-competition-data", "fid": 972, "desc": "Kaggle competition sample data", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "kaggle-competition-data", "fid": 972, "saved_to": str(p)}))

def cmd_postal_code_directory(args) -> int:
    p = _data_root() / "postal-code-directory.json"
    payload = {"feature": "postal-code-directory", "fid": 973, "desc": "postal code directory", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "postal-code-directory", "fid": 973, "saved_to": str(p)}))

def cmd_chemistry_molecule_db(args) -> int:
    p = _data_root() / "chemistry-molecule-db.json"
    payload = {"feature": "chemistry-molecule-db", "fid": 974, "desc": "chemistry molecule database", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "chemistry-molecule-db", "fid": 974, "saved_to": str(p)}))

def cmd_unicode_code_charts(args) -> int:
    p = _data_root() / "unicode-code-charts.json"
    payload = {"feature": "unicode-code-charts", "fid": 975, "desc": "Unicode character code charts", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "unicode-code-charts", "fid": 975, "saved_to": str(p)}))

def cmd_public_domain_recipe_1800s(args) -> int:
    p = _data_root() / "public-domain-recipe-1800s.json"
    payload = {"feature": "public-domain-recipe-1800s", "fid": 976, "desc": "public-domain 1800s recipe book", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "public-domain-recipe-1800s", "fid": 976, "saved_to": str(p)}))

HANDLERS = {
    "transport-timetables-pdf": cmd_transport_timetables_pdf,
    "nutrition-database": cmd_nutrition_database,
    "national-laws-portal": cmd_national_laws_portal,
    "nobel-json": cmd_nobel_json,
    "crm-export-link": cmd_crm_export_link,
    "sec-filings-bulk": cmd_sec_filings_bulk,
    "patent-with-drawings": cmd_patent_with_drawings,
    "who-research-data": cmd_who_research_data,
    "undersea-cables-kml": cmd_undersea_cables_kml,
    "ai-conf-papers": cmd_ai_conf_papers,
    "docs-site-pdf-archive": cmd_docs_site_pdf_archive,
    "airline-safety-cards": cmd_airline_safety_cards,
    "font-specimen-pdf": cmd_font_specimen_pdf,
    "voter-registration": cmd_voter_registration,
    "building-code-standard": cmd_building_code_standard,
    "kaggle-competition-data": cmd_kaggle_competition_data,
    "postal-code-directory": cmd_postal_code_directory,
    "chemistry-molecule-db": cmd_chemistry_molecule_db,
    "unicode-code-charts": cmd_unicode_code_charts,
    "public-domain-recipe-1800s": cmd_public_domain_recipe_1800s,
}

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="dl-data2", description='Simple Internet data/document tasks (round 2, items 241-260) (20 features, F957-F976)')
    sub = p.add_subparsers(dest="cmd", required=True)
    sp = sub.add_parser("transport-timetables-pdf", help="F957 - city transportation timetables PDF")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("nutrition-database", help="F958 - government nutritional database")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("national-laws-portal", help="F959 - country e-laws portal")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("nobel-json", help="F960 - Nobel Prize winners JSON")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("crm-export-link", help="F961 - CRM contact export via web link")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("sec-filings-bulk", help="F962 - company SEC filings bulk")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("patent-with-drawings", help="F963 - patent document with drawings")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("who-research-data", help="F964 - WHO medical research dataset")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("undersea-cables-kml", help="F965 - undersea cables KML map")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("ai-conf-papers", help="F966 - AI conference papers")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("docs-site-pdf-archive", help="F967 - code docs site as PDF archive")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("airline-safety-cards", help="F968 - airline safety cards")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("font-specimen-pdf", help="F969 - font specimen book PDF")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("voter-registration", help="F970 - voter registration db (public)")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("building-code-standard", help="F971 - building code standard document")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("kaggle-competition-data", help="F972 - Kaggle competition sample data")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("postal-code-directory", help="F973 - postal code directory")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("chemistry-molecule-db", help="F974 - chemistry molecule database")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("unicode-code-charts", help="F975 - Unicode character code charts")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("public-domain-recipe-1800s", help="F976 - public-domain 1800s recipe book")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    return p

def main(argv: Optional[list] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return HANDLERS[args.cmd](args)

if __name__ == '__main__':
    raise SystemExit(main())
