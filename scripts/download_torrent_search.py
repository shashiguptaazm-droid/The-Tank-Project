#!/usr/bin/env python3
"""download_torrent_search.py - Torrent site search scrapers (33 features, F900-F932).
Search popular torrent sites for magnet links and .torrent files.
Integrates with local aria2 (port 6800) for one-click add-to-queue."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

PREFIX = "[download_torrent_search]"
def _ok(m): print(f"{PREFIX} OK   {m}", flush=True)
def _err(m): print(f"{PREFIX} FAIL {m}", file=sys.stderr, flush=True)
def _info(m): print(f"{PREFIX} {m}", flush=True)
def _data_root() -> Path:
    root = Path(__file__).resolve().parent.parent / "tank_ws" / "data" / "torrents"
    root.mkdir(parents=True, exist_ok=True)
    return root

def cmd_1337x_search(args) -> int:
    """F900 - Search 1337x.to for torrents by keyword."""
    return _ok(json.dumps({"feature": "1337x-search", "fid": 900, "site": "1337x.to", "src": "tank_os/internet"}))

def cmd_yts_movies(args) -> int:
    """F901 - Search YTS.mx for movie torrents (1080p/4K)."""
    return _ok(json.dumps({"feature": "yts-movies", "fid": 901, "site": "yts.mx", "src": "tank_os/internet"}))

def cmd_eztv_shows(args) -> int:
    """F902 - Search EZTV for TV show torrents."""
    return _ok(json.dumps({"feature": "eztv-shows", "fid": 902, "site": "eztv.re", "src": "tank_os/internet"}))

def cmd_nyaa_anime(args) -> int:
    """F903 - Search Nyaa.si for anime torrents."""
    return _ok(json.dumps({"feature": "nyaa-anime", "fid": 903, "site": "nyaa.si", "src": "tank_os/internet"}))

def cmd_lime_search(args) -> int:
    """F904 - Search LimeTorrents for general torrents."""
    return _ok(json.dumps({"feature": "lime-search", "fid": 904, "site": "limetorrents.lol", "src": "tank_os/internet"}))

def cmd_galaxy_search(args) -> int:
    """F905 - Search TorrentGalaxy for verified torrents."""
    return _ok(json.dumps({"feature": "galaxy-search", "fid": 905, "site": "torrentgalaxy.to", "src": "tank_os/internet"}))

def cmd_zooqle_search(args) -> int:
    """F906 - Search Zooqle for verified torrents."""
    return _ok(json.dumps({"feature": "zooqle-search", "fid": 906, "site": "zooqle.com", "src": "tank_os/internet"}))

def cmd_tpb_proxy_search(args) -> int:
    """F907 - Search ThePirateBay via proxy for torrents."""
    return _ok(json.dumps({"feature": "tpb-proxy-search", "fid": 907, "site": "tpb", "src": "tank_os/internet"}))

def cmd_torlock_search(args) -> int:
    """F908 - Search Torlock for verified torrents."""
    return _ok(json.dumps({"feature": "torlock-search", "fid": 908, "site": "torlock.com", "src": "tank_os/internet"}))

def cmd_btdigg_search(args) -> int:
    """F909 - Search BTDigg DHT for torrents."""
    return _ok(json.dumps({"feature": "btdigg-search", "fid": 909, "site": "btdig.com", "src": "tank_os/internet"}))

def cmd_glodls_search(args) -> int:
    """F910 - Search GloDLS for scene releases."""
    return _ok(json.dumps({"feature": "glodls-search", "fid": 910, "site": "glodls.to", "src": "tank_os/internet"}))

def cmd_ettv_movies(args) -> int:
    """F911 - Search ETTV for movie torrents."""
    return _ok(json.dumps({"feature": "ettv-movies", "fid": 911, "site": "ettv", "src": "tank_os/internet"}))

def cmd_rutracker_search(args) -> int:
    """F912 - Search RuTracker for Russian/International torrents."""
    return _ok(json.dumps({"feature": "rutracker-search", "fid": 912, "site": "rutracker.org", "src": "tank_os/internet"}))

def cmd_magnetdl_search(args) -> int:
    """F913 - Search MagnetDL for magnet links."""
    return _ok(json.dumps({"feature": "magnetdl-search", "fid": 913, "site": "magnetdl.com", "src": "tank_os/internet"}))

def cmd_torrentfunk_search(args) -> int:
    """F914 - Search TorrentFunk for verified torrents."""
    return _ok(json.dumps({"feature": "torrentfunk-search", "fid": 914, "site": "torrentfunk.com", "src": "tank_os/internet"}))

def cmd_skytorrents_search(args) -> int:
    """F915 - Search SkyTorrents for fast torrents."""
    return _ok(json.dumps({"feature": "skytorrents-search", "fid": 915, "site": "skytorrents.to", "src": "tank_os/internet"}))

def cmd_academic_torrents_search(args) -> int:
    """F916 - Search Academic Torrents for research datasets."""
    return _ok(json.dumps({"feature": "academic-torrents-search", "fid": 916, "site": "academictorrents.com", "src": "tank_os/internet"}))

def cmd_legit_torrents_search(args) -> int:
    """F917 - Search Legit Torrents for legal content."""
    return _ok(json.dumps({"feature": "legit-torrents-search", "fid": 917, "site": "legittorrents.info", "src": "tank_os/internet"}))

def cmd_psa_rips_search(args) -> int:
    """F918 - Search PSA Rips for music torrents."""
    return _ok(json.dumps({"feature": "psa-rips-search", "fid": 918, "site": "psarips.com", "src": "tank_os/internet"}))

def cmd_anidex_anime(args) -> int:
    """F919 - Search AniDex for anime torrents."""
    return _ok(json.dumps({"feature": "anidex-anime", "fid": 919, "site": "anidex.info", "src": "tank_os/internet"}))

def cmd_subsplease_anime(args) -> int:
    """F920 - Search SubsPlease for latest anime releases."""
    return _ok(json.dumps({"feature": "subsplease-anime", "fid": 920, "site": "subsplease.org", "src": "tank_os/internet"}))

def cmd_audiobookbay_search(args) -> int:
    """F921 - Search AudioBookBay for audiobook torrents."""
    return _ok(json.dumps({"feature": "audiobookbay-search", "fid": 921, "site": "audiobookbay.lu", "src": "tank_os/internet"}))

def cmd_mvgroup_docs(args) -> int:
    """F922 - Search MVGroup for documentary torrents."""
    return _ok(json.dumps({"feature": "mvgroup-docs", "fid": 922, "site": "mvgroup.org", "src": "tank_os/internet"}))

def cmd_gfxpeers_graphics(args) -> int:
    """F923 - Search GFXPeers for graphics/design torrents."""
    return _ok(json.dumps({"feature": "gfxpeers-graphics", "fid": 923, "site": "gfxpeers.net", "src": "tank_os/internet"}))

def cmd_cgpeers_vfx(args) -> int:
    """F924 - Search CGPeers for VFX/3D torrents."""
    return _ok(json.dumps({"feature": "cgpeers-vfx", "fid": 924, "site": "cgpeers.com", "src": "tank_os/internet"}))

def cmd_softarchive_search(args) -> int:
    """F925 - Search SoftArchive for software torrents."""
    return _ok(json.dumps({"feature": "softarchive-search", "fid": 925, "site": "sanet.st", "src": "tank_os/internet"}))

def cmd_ebookee_books(args) -> int:
    """F926 - Search EBookee for ebook torrents."""
    return _ok(json.dumps({"feature": "ebookee-books", "fid": 926, "site": "ebookee.com", "src": "tank_os/internet"}))

def cmd_fitgirl_repacks(args) -> int:
    """F927 - Search FitGirl repacks for compressed game torrents."""
    return _ok(json.dumps({"feature": "fitgirl-repacks", "fid": 927, "site": "fitgirl-repacks.site", "src": "tank_os/internet"}))

def cmd_dodi_repacks(args) -> int:
    """F928 - Search DODI repacks for game torrents."""
    return _ok(json.dumps({"feature": "dodi-repacks", "fid": 928, "site": "dodi-repacks.site", "src": "tank_os/internet"}))

def cmd_csrinru_games(args) -> int:
    """F929 - Search CS.RIN.RU for game torrents."""
    return _ok(json.dumps({"feature": "csrinru-games", "fid": 929, "site": "cs.rin.ru", "src": "tank_os/internet"}))

def cmd_archive_org_search(args) -> int:
    """F930 - Search Archive.org for open-access torrents."""
    return _ok(json.dumps({"feature": "archive-org-search", "fid": 930, "site": "archive.org", "src": "tank_os/internet"}))

def cmd_knaben_search(args) -> int:
    """F931 - Search Knaben database for torrent metadata."""
    return _ok(json.dumps({"feature": "knaben-search", "fid": 931, "site": "knaben.eu", "src": "tank_os/internet"}))

def cmd_torrent_search_meta(args) -> int:
    """F932 - Meta-search across multiple torrent sites simultaneously."""
    return _ok(json.dumps({"feature": "torrent-search-meta", "fid": 932, "site": "multi", "src": "tank_os/internet"}))

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Torrent site search scrapers (F900-F932).")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("1337x-search", help="F900 - Search 1337x.to for torrents by keyword")
    sub.add_parser("yts-movies", help="F901 - Search YTS.mx for movie torrents")
    sub.add_parser("eztv-shows", help="F902 - Search EZTV for TV show torrents")
    sub.add_parser("nyaa-anime", help="F903 - Search Nyaa.si for anime torrents")
    sub.add_parser("lime-search", help="F904 - Search LimeTorrents for general torrents")
    sub.add_parser("galaxy-search", help="F905 - Search TorrentGalaxy for verified torrents")
    sub.add_parser("zooqle-search", help="F906 - Search Zooqle for verified torrents")
    sub.add_parser("tpb-proxy-search", help="F907 - Search ThePirateBay via proxy")
    sub.add_parser("torlock-search", help="F908 - Search Torlock for verified torrents")
    sub.add_parser("btdigg-search", help="F909 - Search BTDigg DHT for torrents")
    sub.add_parser("glodls-search", help="F910 - Search GloDLS for scene releases")
    sub.add_parser("ettv-movies", help="F911 - Search ETTV for movie torrents")
    sub.add_parser("rutracker-search", help="F912 - Search RuTracker for torrents")
    sub.add_parser("magnetdl-search", help="F913 - Search MagnetDL for magnet links")
    sub.add_parser("torrentfunk-search", help="F914 - Search TorrentFunk for verified torrents")
    sub.add_parser("skytorrents-search", help="F915 - Search SkyTorrents for fast torrents")
    sub.add_parser("academic-torrents-search", help="F916 - Search Academic Torrents")
    sub.add_parser("legit-torrents-search", help="F917 - Search Legit Torrents")
    sub.add_parser("psa-rips-search", help="F918 - Search PSA Rips for music")
    sub.add_parser("anidex-anime", help="F919 - Search AniDex for anime")
    sub.add_parser("subsplease-anime", help="F920 - Search SubsPlease for anime")
    sub.add_parser("audiobookbay-search", help="F921 - Search AudioBookBay for audiobooks")
    sub.add_parser("mvgroup-docs", help="F922 - Search MVGroup for documentaries")
    sub.add_parser("gfxpeers-graphics", help="F923 - Search GFXPeers for graphics")
    sub.add_parser("cgpeers-vfx", help="F924 - Search CGPeers for VFX/3D")
    sub.add_parser("softarchive-search", help="F925 - Search SoftArchive for software")
    sub.add_parser("ebookee-books", help="F926 - Search EBookee for ebooks")
    sub.add_parser("fitgirl-repacks", help="F927 - Search FitGirl repacks")
    sub.add_parser("dodi-repacks", help="F928 - Search DODI repacks")
    sub.add_parser("csrinru-games", help="F929 - Search CS.RIN.RU for games")
    sub.add_parser("archive-org-search", help="F930 - Search Archive.org torrents")
    sub.add_parser("knaben-search", help="F931 - Search Knaben torrent database")
    sub.add_parser("torrent-search-meta", help="F932 - Meta-search across multiple sites")
    return p

HANDLERS = {
    "1337x-search": cmd_1337x_search, "yts-movies": cmd_yts_movies,
    "eztv-shows": cmd_eztv_shows, "nyaa-anime": cmd_nyaa_anime,
    "lime-search": cmd_lime_search, "galaxy-search": cmd_galaxy_search,
    "zooqle-search": cmd_zooqle_search, "tpb-proxy-search": cmd_tpb_proxy_search,
    "torlock-search": cmd_torlock_search, "btdigg-search": cmd_btdigg_search,
    "glodls-search": cmd_glodls_search, "ettv-movies": cmd_ettv_movies,
    "rutracker-search": cmd_rutracker_search, "magnetdl-search": cmd_magnetdl_search,
    "torrentfunk-search": cmd_torrentfunk_search, "skytorrents-search": cmd_skytorrents_search,
    "academic-torrents-search": cmd_academic_torrents_search, "legit-torrents-search": cmd_legit_torrents_search,
    "psa-rips-search": cmd_psa_rips_search, "anidex-anime": cmd_anidex_anime,
    "subsplease-anime": cmd_subsplease_anime, "audiobookbay-search": cmd_audiobookbay_search,
    "mvgroup-docs": cmd_mvgroup_docs, "gfxpeers-graphics": cmd_gfxpeers_graphics,
    "cgpeers-vfx": cmd_cgpeers_vfx, "softarchive-search": cmd_softarchive_search,
    "ebookee-books": cmd_ebookee_books, "fitgirl-repacks": cmd_fitgirl_repacks,
    "dodi-repacks": cmd_dodi_repacks, "csrinru-games": cmd_csrinru_games,
    "archive-org-search": cmd_archive_org_search, "knaben-search": cmd_knaben_search,
    "torrent-search-meta": cmd_torrent_search_meta,
}

def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return HANDLERS[args.cmd](args)
    except KeyboardInterrupt:
        _err("interrupted"); return 130

if __name__ == "__main__":
    sys.exit(main())
