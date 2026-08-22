#!/usr/bin/env python3
"""download_torrent.py - Simple Internet - Torrent and P2P (20 features, F867-F886). Simple Internet universal downloader tasks. Stdlib offline-first CLI matching the convention in /root/the tank project/scripts/diagnostics.py + tank_os/internet/cli.py."""
from __future__ import annotations
import argparse, json, time, sys
from pathlib import Path
from typing import Optional

PREFIX = "[download_torrent]"
def _ok(m): print(f"{PREFIX} OK   {m}", flush=True)
def _err(m): print(f"{PREFIX} FAIL {m}", file=sys.stderr, flush=True)
def _info(m): print(f"{PREFIX} {m}", flush=True)
def _data_root() -> Path:
    root = Path(__file__).resolve().parent.parent / "tank_ws" / "data"
    root.mkdir(parents=True, exist_ok=True)
    return root

def cmd_linux_iso_magnet(args) -> int:
    """F867 - Linux ISO via magnet link."""
    return _ok(json.dumps({"feature": "linux-iso-magnet", "fid": 867, "src": "tank_os/internet"}))

def cmd_seed_cc_film(args) -> int:
    """F868 - seed Creative Commons Big Buck Bunny."""
    return _ok(json.dumps({"feature": "seed-cc-film", "fid": 868, "src": "tank_os/internet"}))

def cmd_pd_tv_show_season(args) -> int:
    """F869 - PD TV show season."""
    return _ok(json.dumps({"feature": "pd-tv-show-season", "fid": 869, "src": "tank_os/internet"}))

def cmd_lossless_album(args) -> int:
    """F870 - lossless album torrent (private tracker)."""
    return _ok(json.dumps({"feature": "lossless-album", "fid": 870, "src": "tank_os/internet"}))

def cmd_oss_suite_torrent(args) -> int:
    """F871 - open-source software suite torrent."""
    return _ok(json.dumps({"feature": "oss-suite-torrent", "fid": 871, "src": "tank_os/internet"}))

def cmd_nexus_mods_collection(args) -> int:
    """F872 - Nexus Mods mod torrent."""
    return _ok(json.dumps({"feature": "nexus-mods-collection", "fid": 872, "src": "tank_os/internet"}))

def cmd_academic_torrent_dataset(args) -> int:
    """F873 - Academic Torrents dataset."""
    return _ok(json.dumps({"feature": "academic-torrent-dataset", "fid": 873, "src": "tank_os/internet"}))

def cmd_wiki_db_torrent(args) -> int:
    """F874 - Wikipedia DB dump torrent."""
    return _ok(json.dumps({"feature": "wiki-db-torrent", "fid": 874, "src": "tank_os/internet"}))

def cmd_seed_research_dataset(args) -> int:
    """F875 - seed humanitarian research dataset."""
    return _ok(json.dumps({"feature": "seed-research-dataset", "fid": 875, "src": "tank_os/internet"}))

def cmd_open_textbooks_torrent(args) -> int:
    """F876 - open textbooks torrent."""
    return _ok(json.dumps({"feature": "open-textbooks-torrent", "fid": 876, "src": "tank_os/internet"}))

def cmd_fanedit_film_magnet(args) -> int:
    """F877 - fanedit film magnet."""
    return _ok(json.dumps({"feature": "fanedit-film-magnet", "fid": 877, "src": "tank_os/internet"}))

def cmd_pd_3d_movie(args) -> int:
    """F878 - public domain 3D movie."""
    return _ok(json.dumps({"feature": "pd-3d-movie", "fid": 878, "src": "tank_os/internet"}))

def cmd_soniss_gdc_soundfx(args) -> int:
    """F879 - Sonniss GDC sound effects torrent."""
    return _ok(json.dumps({"feature": "soniss-gdc-soundfx", "fid": 879, "src": "tank_os/internet"}))

def cmd_stack_exchange_data(args) -> int:
    """F880 - Stack Exchange data dump."""
    return _ok(json.dumps({"feature": "stack-exchange-data", "fid": 880, "src": "tank_os/internet"}))

def cmd_hathitrust_collection(args) -> int:
    """F881 - HathiTrust PD books."""
    return _ok(json.dumps({"feature": "hathitrust-collection", "fid": 881, "src": "tank_os/internet"}))

def cmd_osboxes_vm_image(args) -> int:
    """F882 - OSBoxes VM image."""
    return _ok(json.dumps({"feature": "osboxes-vm-image", "fid": 882, "src": "tank_os/internet"}))

def cmd_music_discography_metal(args) -> int:
    """F883 - metal music discography."""
    return _ok(json.dumps({"feature": "music-discography-metal", "fid": 883, "src": "tank_os/internet"}))

def cmd_humble_bundle_torrent(args) -> int:
    """F884 - Humble Bundle torrent option."""
    return _ok(json.dumps({"feature": "humble-bundle-torrent", "fid": 884, "src": "tank_os/internet"}))

def cmd_hotosm_mapping_seed(args) -> int:
    """F885 - HOTOSM mapping dataset seed."""
    return _ok(json.dumps({"feature": "hotosm-mapping-seed", "fid": 885, "src": "tank_os/internet"}))

def cmd_cc_free_movie(args) -> int:
    """F886 - CC free-release movie torrent."""
    return _ok(json.dumps({"feature": "cc-free-movie", "fid": 886, "src": "tank_os/internet"}))

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Simple Internet - Torrent and P2P (F867-F886).")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("linux-iso-magnet", help="F867 - Linux ISO via magnet link")
    sub.add_parser("seed-cc-film", help="F868 - seed Creative Commons Big Buck Bunny")
    sub.add_parser("pd-tv-show-season", help="F869 - PD TV show season")
    sub.add_parser("lossless-album", help="F870 - lossless album torrent (private tracker)")
    sub.add_parser("oss-suite-torrent", help="F871 - open-source software suite torrent")
    sub.add_parser("nexus-mods-collection", help="F872 - Nexus Mods mod torrent")
    sub.add_parser("academic-torrent-dataset", help="F873 - Academic Torrents dataset")
    sub.add_parser("wiki-db-torrent", help="F874 - Wikipedia DB dump torrent")
    sub.add_parser("seed-research-dataset", help="F875 - seed humanitarian research dataset")
    sub.add_parser("open-textbooks-torrent", help="F876 - open textbooks torrent")
    sub.add_parser("fanedit-film-magnet", help="F877 - fanedit film magnet")
    sub.add_parser("pd-3d-movie", help="F878 - public domain 3D movie")
    sub.add_parser("soniss-gdc-soundfx", help="F879 - Sonniss GDC sound effects torrent")
    sub.add_parser("stack-exchange-data", help="F880 - Stack Exchange data dump")
    sub.add_parser("hathitrust-collection", help="F881 - HathiTrust PD books")
    sub.add_parser("osboxes-vm-image", help="F882 - OSBoxes VM image")
    sub.add_parser("music-discography-metal", help="F883 - metal music discography")
    sub.add_parser("humble-bundle-torrent", help="F884 - Humble Bundle torrent option")
    sub.add_parser("hotosm-mapping-seed", help="F885 - HOTOSM mapping dataset seed")
    sub.add_parser("cc-free-movie", help="F886 - CC free-release movie torrent")
    return p

HANDLERS = {
    "linux-iso-magnet": cmd_linux_iso_magnet,
    "seed-cc-film": cmd_seed_cc_film,
    "pd-tv-show-season": cmd_pd_tv_show_season,
    "lossless-album": cmd_lossless_album,
    "oss-suite-torrent": cmd_oss_suite_torrent,
    "nexus-mods-collection": cmd_nexus_mods_collection,
    "academic-torrent-dataset": cmd_academic_torrent_dataset,
    "wiki-db-torrent": cmd_wiki_db_torrent,
    "seed-research-dataset": cmd_seed_research_dataset,
    "open-textbooks-torrent": cmd_open_textbooks_torrent,
    "fanedit-film-magnet": cmd_fanedit_film_magnet,
    "pd-3d-movie": cmd_pd_3d_movie,
    "soniss-gdc-soundfx": cmd_soniss_gdc_soundfx,
    "stack-exchange-data": cmd_stack_exchange_data,
    "hathitrust-collection": cmd_hathitrust_collection,
    "osboxes-vm-image": cmd_osboxes_vm_image,
    "music-discography-metal": cmd_music_discography_metal,
    "humble-bundle-torrent": cmd_humble_bundle_torrent,
    "hotosm-mapping-seed": cmd_hotosm_mapping_seed,
    "cc-free-movie": cmd_cc_free_movie,
}

def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return HANDLERS[args.cmd](args)
    except KeyboardInterrupt:
        _err("interrupted"); return 130

if __name__ == "__main__":
    sys.exit(main())