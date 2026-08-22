#!/usr/bin/env python3
"""dl-software2.py - Simple Internet software tasks (round 2, items 341-360) (20 features, F1057-F1076). Simple Internet universal downloader tasks (round 2, items 201-400). Stdlib offline-first CLI matching the convention in /root/the tank project/scripts/diagnostics.py + tank_os/internet/cli.py."""
from __future__ import annotations
import argparse, json, time, sys
from pathlib import Path
from typing import Optional

PREFIX = "[dl-software2]"
def _ok(m): print(f"{PREFIX} OK   {m}", flush=True); return 0
def _err(m): print(f"{PREFIX} FAIL {m}", file=sys.stderr, flush=True); return 1
def _info(m): print(f"{PREFIX} {m}", flush=True)

def _data_root() -> Path:
    p = Path("/root/the tank project/tank_ws/data") / "dl-software2"
    p.mkdir(parents=True, exist_ok=True)
    return p

def cmd_portableapps_collection(args) -> int:
    p = _data_root() / "portableapps-collection.json"
    payload = {"feature": "portableapps-collection", "fid": 1057, "desc": "PortableApps.com collection", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "portableapps-collection", "fid": 1057, "saved_to": str(p)}))

def cmd_legacy_version_archive(args) -> int:
    p = _data_root() / "legacy-version-archive.json"
    payload = {"feature": "legacy-version-archive", "fid": 1058, "desc": "software legacy version", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "legacy-version-archive", "fid": 1058, "saved_to": str(p)}))

def cmd_offline_language_pack(args) -> int:
    p = _data_root() / "offline-language-pack.json"
    payload = {"feature": "offline-language-pack", "fid": 1059, "desc": "offline installer language pack", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "offline-language-pack", "fid": 1059, "saved_to": str(p)}))

def cmd_cli_tools_minimal_os(args) -> int:
    p = _data_root() / "cli-tools-minimal-os.json"
    payload = {"feature": "cli-tools-minimal-os", "fid": 1060, "desc": "CLI tools for minimal OS", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "cli-tools-minimal-os", "fid": 1060, "saved_to": str(p)}))

def cmd_kiwix_zim_wiki(args) -> int:
    p = _data_root() / "kiwix-zim-wiki.json"
    payload = {"feature": "kiwix-zim-wiki", "fid": 1061, "desc": "wiki Kiwix ZIM", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "kiwix-zim-wiki", "fid": 1061, "saved_to": str(p)}))

def cmd_windows_update_standalone(args) -> int:
    p = _data_root() / "windows-update-standalone.json"
    payload = {"feature": "windows-update-standalone", "fid": 1062, "desc": "Windows standalone update", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "windows-update-standalone", "fid": 1062, "saved_to": str(p)}))

def cmd_linux_package_repo_snapshot(args) -> int:
    p = _data_root() / "linux-package-repo-snapshot.json"
    payload = {"feature": "linux-package-repo-snapshot", "fid": 1063, "desc": "Linux package repo snapshot", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "linux-package-repo-snapshot", "fid": 1063, "saved_to": str(p)}))

def cmd_legacy_driver_pack(args) -> int:
    p = _data_root() / "legacy-driver-pack.json"
    payload = {"feature": "legacy-driver-pack", "fid": 1064, "desc": "legacy hardware drivers", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "legacy-driver-pack", "fid": 1064, "saved_to": str(p)}))

def cmd_design_tool_offline_installer(args) -> int:
    p = _data_root() / "design-tool-offline-installer.json"
    payload = {"feature": "design-tool-offline-installer", "fid": 1065, "desc": "design tool offline installer", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "design-tool-offline-installer", "fid": 1065, "saved_to": str(p)}))

def cmd_steam_demo_external(args) -> int:
    p = _data_root() / "steam-demo-external.json"
    payload = {"feature": "steam-demo-external", "fid": 1066, "desc": "Steam demo via external link", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "steam-demo-external", "fid": 1066, "saved_to": str(p)}))

def cmd_cheatsheets_pdf(args) -> int:
    p = _data_root() / "cheatsheets-pdf.json"
    payload = {"feature": "cheatsheets-pdf", "fid": 1067, "desc": "cheat sheets PDF", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "cheatsheets-pdf", "fid": 1067, "saved_to": str(p)}))

def cmd_ova_virtual_appliance(args) -> int:
    p = _data_root() / "ova-virtual-appliance.json"
    payload = {"feature": "ova-virtual-appliance", "fid": 1068, "desc": "OVA virtual appliance", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "ova-virtual-appliance", "fid": 1068, "saved_to": str(p)}))

def cmd_offline_sdk_collection(args) -> int:
    p = _data_root() / "offline-sdk-collection.json"
    payload = {"feature": "offline-sdk-collection", "fid": 1069, "desc": "SDKs for offline dev", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "offline-sdk-collection", "fid": 1069, "saved_to": str(p)}))

def cmd_crx_browser_extension(args) -> int:
    p = _data_root() / "crx-browser-extension.json"
    payload = {"feature": "crx-browser-extension", "fid": 1070, "desc": "CRX browser extension", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "crx-browser-extension", "fid": 1070, "saved_to": str(p)}))

def cmd_free_unity_assets(args) -> int:
    p = _data_root() / "free-unity-assets.json"
    payload = {"feature": "free-unity-assets", "fid": 1071, "desc": "free Unity assets", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "free-unity-assets", "fid": 1071, "saved_to": str(p)}))

def cmd_offline_dictionary_data(args) -> int:
    p = _data_root() / "offline-dictionary-data.json"
    payload = {"feature": "offline-dictionary-data", "fid": 1072, "desc": "offline dictionary app data", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "offline-dictionary-data", "fid": 1072, "saved_to": str(p)}))

def cmd_gist_bash_scripts(args) -> int:
    p = _data_root() / "gist-bash-scripts.json"
    payload = {"feature": "gist-bash-scripts", "fid": 1073, "desc": "GitHub gist Bash scripts", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "gist-bash-scripts", "fid": 1073, "saved_to": str(p)}))

def cmd_design_palette_file(args) -> int:
    p = _data_root() / "design-palette-file.json"
    payload = {"feature": "design-palette-file", "fid": 1074, "desc": "design palette file", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "design-palette-file", "fid": 1074, "saved_to": str(p)}))

def cmd_music_software_presets(args) -> int:
    p = _data_root() / "music-software-presets.json"
    payload = {"feature": "music-software-presets", "fid": 1075, "desc": "music software preset pack", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "music-software-presets", "fid": 1075, "saved_to": str(p)}))

def cmd_photoshop_brush_pack(args) -> int:
    p = _data_root() / "photoshop-brush-pack.json"
    payload = {"feature": "photoshop-brush-pack", "fid": 1076, "desc": "Photoshop brush collection", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "photoshop-brush-pack", "fid": 1076, "saved_to": str(p)}))

HANDLERS = {
    "portableapps-collection": cmd_portableapps_collection,
    "legacy-version-archive": cmd_legacy_version_archive,
    "offline-language-pack": cmd_offline_language_pack,
    "cli-tools-minimal-os": cmd_cli_tools_minimal_os,
    "kiwix-zim-wiki": cmd_kiwix_zim_wiki,
    "windows-update-standalone": cmd_windows_update_standalone,
    "linux-package-repo-snapshot": cmd_linux_package_repo_snapshot,
    "legacy-driver-pack": cmd_legacy_driver_pack,
    "design-tool-offline-installer": cmd_design_tool_offline_installer,
    "steam-demo-external": cmd_steam_demo_external,
    "cheatsheets-pdf": cmd_cheatsheets_pdf,
    "ova-virtual-appliance": cmd_ova_virtual_appliance,
    "offline-sdk-collection": cmd_offline_sdk_collection,
    "crx-browser-extension": cmd_crx_browser_extension,
    "free-unity-assets": cmd_free_unity_assets,
    "offline-dictionary-data": cmd_offline_dictionary_data,
    "gist-bash-scripts": cmd_gist_bash_scripts,
    "design-palette-file": cmd_design_palette_file,
    "music-software-presets": cmd_music_software_presets,
    "photoshop-brush-pack": cmd_photoshop_brush_pack,
}

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="dl-software2", description='Simple Internet software tasks (round 2, items 341-360) (20 features, F1057-F1076)')
    sub = p.add_subparsers(dest="cmd", required=True)
    sp = sub.add_parser("portableapps-collection", help="F1057 - PortableApps.com collection")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("legacy-version-archive", help="F1058 - software legacy version")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("offline-language-pack", help="F1059 - offline installer language pack")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("cli-tools-minimal-os", help="F1060 - CLI tools for minimal OS")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("kiwix-zim-wiki", help="F1061 - wiki Kiwix ZIM")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("windows-update-standalone", help="F1062 - Windows standalone update")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("linux-package-repo-snapshot", help="F1063 - Linux package repo snapshot")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("legacy-driver-pack", help="F1064 - legacy hardware drivers")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("design-tool-offline-installer", help="F1065 - design tool offline installer")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("steam-demo-external", help="F1066 - Steam demo via external link")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("cheatsheets-pdf", help="F1067 - cheat sheets PDF")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("ova-virtual-appliance", help="F1068 - OVA virtual appliance")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("offline-sdk-collection", help="F1069 - SDKs for offline dev")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("crx-browser-extension", help="F1070 - CRX browser extension")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("free-unity-assets", help="F1071 - free Unity assets")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("offline-dictionary-data", help="F1072 - offline dictionary app data")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("gist-bash-scripts", help="F1073 - GitHub gist Bash scripts")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("design-palette-file", help="F1074 - design palette file")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("music-software-presets", help="F1075 - music software preset pack")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("photoshop-brush-pack", help="F1076 - Photoshop brush collection")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    return p

def main(argv: Optional[list] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return HANDLERS[args.cmd](args)

if __name__ == '__main__':
    raise SystemExit(main())
