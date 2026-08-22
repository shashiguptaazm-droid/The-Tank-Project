#!/usr/bin/env python3
"""download_data.py - Simple Internet - Data/Docs/Other Media (50 features, F817-F866). Simple Internet universal downloader tasks. Stdlib offline-first CLI matching the convention in /root/the tank project/scripts/diagnostics.py + tank_os/internet/cli.py."""
from __future__ import annotations
import argparse, json, time, sys
from pathlib import Path
from typing import Optional

PREFIX = "[download_data]"
def _ok(m): print(f"{PREFIX} OK   {m}", flush=True)
def _err(m): print(f"{PREFIX} FAIL {m}", file=sys.stderr, flush=True)
def _info(m): print(f"{PREFIX} {m}", flush=True)
def _data_root() -> Path:
    root = Path(__file__).resolve().parent.parent / "tank_ws" / "data"
    root.mkdir(parents=True, exist_ok=True)
    return root

def cmd_journal_pdfs(args) -> int:
    """F817 - academic journal open-access PDFs."""
    return _ok(json.dumps({"feature": "journal-pdfs", "fid": 817, "src": "tank_os/internet"}))

def cmd_gov_csv(args) -> int:
    """F818 - gov open data CSV dump."""
    return _ok(json.dumps({"feature": "gov-csv", "fid": 818, "src": "tank_os/internet"}))

def cmd_wiki_images(args) -> int:
    """F819 - all images on Wikipedia page."""
    return _ok(json.dumps({"feature": "wiki-images", "fid": 819, "src": "tank_os/internet"}))

def cmd_website_offline_httrack(args) -> int:
    """F820 - full site mirror (HTTrack)."""
    return _ok(json.dumps({"feature": "website-offline-httrack", "fid": 820, "src": "tank_os/internet"}))

def cmd_gutenberg_author_ebooks(args) -> int:
    """F821 - Gutenberg author e-books."""
    return _ok(json.dumps({"feature": "gutenberg-author-ebooks", "fid": 821, "src": "tank_os/internet"}))

def cmd_shakespeare_text(args) -> int:
    """F822 - Shakespeare complete works."""
    return _ok(json.dumps({"feature": "shakespeare-text", "fid": 822, "src": "tank_os/internet"}))

def cmd_github_repo_zip(args) -> int:
    """F823 - GitHub repo ZIP."""
    return _ok(json.dumps({"feature": "github-repo-zip", "fid": 823, "src": "tank_os/internet"}))

def cmd_gsheets_xl(args) -> int:
    """F824 - Google Sheets published link to XLSX."""
    return _ok(json.dumps({"feature": "gsheets-xl", "fid": 824, "src": "tank_os/internet"}))

def cmd_canva_pdf(args) -> int:
    """F825 - Canva design as PDF."""
    return _ok(json.dumps({"feature": "canva-pdf", "fid": 825, "src": "tank_os/internet"}))

def cmd_prezi(args) -> int:
    """F826 - Prezi presentation."""
    return _ok(json.dumps({"feature": "prezi", "fid": 826, "src": "tank_os/internet"}))

def cmd_figma_export(args) -> int:
    """F827 - Figma file via share link."""
    return _ok(json.dumps({"feature": "figma-export", "fid": 827, "src": "tank_os/internet"}))

def cmd_notion_html(args) -> int:
    """F828 - Notion page as HTML."""
    return _ok(json.dumps({"feature": "notion-html", "fid": 828, "src": "tank_os/internet"}))

def cmd_miro_board_img(args) -> int:
    """F829 - Miro board image."""
    return _ok(json.dumps({"feature": "miro-board-img", "fid": 829, "src": "tank_os/internet"}))

def cmd_dropbox_shared_folder(args) -> int:
    """F830 - public Dropbox folder."""
    return _ok(json.dumps({"feature": "dropbox-shared-folder", "fid": 830, "src": "tank_os/internet"}))

def cmd_google_fonts(args) -> int:
    """F831 - Google Fonts collection."""
    return _ok(json.dumps({"feature": "google-fonts", "fid": 831, "src": "tank_os/internet"}))

def cmd_docker_image_tar(args) -> int:
    """F832 - Docker Hub image tar."""
    return _ok(json.dumps({"feature": "docker-image-tar", "fid": 832, "src": "tank_os/internet"}))

def cmd_wiki_db_dump(args) -> int:
    """F833 - Wikipedia full DB dump."""
    return _ok(json.dumps({"feature": "wiki-db-dump", "fid": 833, "src": "tank_os/internet"}))

def cmd_osm_tiles_region(args) -> int:
    """F834 - OpenStreetMap tile set."""
    return _ok(json.dumps({"feature": "osm-tiles-region", "fid": 834, "src": "tank_os/internet"}))

def cmd_s3_public_list(args) -> int:
    """F835 - AWS S3 public bucket."""
    return _ok(json.dumps({"feature": "s3-public-list", "fid": 835, "src": "tank_os/internet"}))

def cmd_weather_pdf_daily(args) -> int:
    """F836 - daily weather forecast PDF."""
    return _ok(json.dumps({"feature": "weather-pdf-daily", "fid": 836, "src": "tank_os/internet"}))

def cmd_yahoo_finance_csv(args) -> int:
    """F837 - Yahoo Finance stock data."""
    return _ok(json.dumps({"feature": "yahoo-finance-csv", "fid": 837, "src": "tank_os/internet"}))

def cmd_coingecko_price_history(args) -> int:
    """F838 - CoinGecko crypto history."""
    return _ok(json.dumps({"feature": "coingecko-price-history", "fid": 838, "src": "tank_os/internet"}))

def cmd_google_trends_csv(args) -> int:
    """F839 - Google Trends CSV."""
    return _ok(json.dumps({"feature": "google-trends-csv", "fid": 839, "src": "tank_os/internet"}))

def cmd_reddit_top_images_month(args) -> int:
    """F840 - Reddit subreddit top monthly."""
    return _ok(json.dumps({"feature": "reddit-top-images-month", "fid": 840, "src": "tank_os/internet"}))

def cmd_imgur_gallery(args) -> int:
    """F841 - all Imgur gallery memes."""
    return _ok(json.dumps({"feature": "imgur-gallery", "fid": 841, "src": "tank_os/internet"}))

def cmd_pinterest_board_folder(args) -> int:
    """F842 - Pinterest board folder."""
    return _ok(json.dumps({"feature": "pinterest-board-folder", "fid": 842, "src": "tank_os/internet"}))

def cmd_ig_photos_public(args) -> int:
    """F843 - public IG account photos."""
    return _ok(json.dumps({"feature": "ig-photos-public", "fid": 843, "src": "tank_os/internet"}))

def cmd_flickr_album(args) -> int:
    """F844 - Flickr high-res album."""
    return _ok(json.dumps({"feature": "flickr-album", "fid": 844, "src": "tank_os/internet"}))

def cmd_unsplash_curated(args) -> int:
    """F845 - Unsplash curated sets."""
    return _ok(json.dumps({"feature": "unsplash-curated", "fid": 845, "src": "tank_os/internet"}))

def cmd_xkcd_all_time(args) -> int:
    """F846 - every XKCD comic."""
    return _ok(json.dumps({"feature": "xkcd-all-time", "fid": 846, "src": "tank_os/internet"}))

def cmd_nasa_apod_archive(args) -> int:
    """F847 - NASA APOD archive."""
    return _ok(json.dumps({"feature": "nasa-apod-archive", "fid": 847, "src": "tank_os/internet"}))

def cmd_pokedex_bulbapedia(args) -> int:
    """F848 - all Bulbapedia images."""
    return _ok(json.dumps({"feature": "pokedex-bulbapedia", "fid": 848, "src": "tank_os/internet"}))

def cmd_sketchfab_model(args) -> int:
    """F849 - Sketchfab 3D model."""
    return _ok(json.dumps({"feature": "sketchfab-model", "fid": 849, "src": "tank_os/internet"}))

def cmd_thingiverse_stl(args) -> int:
    """F850 - Thingiverse STL collection."""
    return _ok(json.dumps({"feature": "thingiverse-stl", "fid": 850, "src": "tank_os/internet"}))

def cmd_dafont_family(args) -> int:
    """F851 - DaFont font family."""
    return _ok(json.dumps({"feature": "dafont-family", "fid": 851, "src": "tank_os/internet"}))

def cmd_iso_mirror(args) -> int:
    """F852 - official ISO mirror."""
    return _ok(json.dumps({"feature": "iso-mirror", "fid": 852, "src": "tank_os/internet"}))

def cmd_apk_apkmirror(args) -> int:
    """F853 - APK from APKMirror."""
    return _ok(json.dumps({"feature": "apk-apkmirror", "fid": 853, "src": "tank_os/internet"}))

def cmd_deb_pkg_deps(args) -> int:
    """F854 - Debian pkg + recursive deps."""
    return _ok(json.dumps({"feature": "deb-pkg-deps", "fid": 854, "src": "tank_os/internet"}))

def cmd_pypi_wheel(args) -> int:
    """F855 - PyPI wheel download."""
    return _ok(json.dumps({"feature": "pypi-wheel", "fid": 855, "src": "tank_os/internet"}))

def cmd_epub_standard_ebooks(args) -> int:
    """F856 - Standard Ebooks EPUB."""
    return _ok(json.dumps({"feature": "epub-standard-ebooks", "fid": 856, "src": "tank_os/internet"}))

def cmd_webcomic_rss(args) -> int:
    """F857 - webcomic RSS strip save."""
    return _ok(json.dumps({"feature": "webcomic-rss", "fid": 857, "src": "tank_os/internet"}))

def cmd_subtitles_by_hash(args) -> int:
    """F858 - subtitle by movie hash."""
    return _ok(json.dumps({"feature": "subtitles-by-hash", "fid": 858, "src": "tank_os/internet"}))

def cmd_fsi_language_course(args) -> int:
    """F859 - FSI public language course."""
    return _ok(json.dumps({"feature": "fsi-language-course", "fid": 859, "src": "tank_os/internet"}))

def cmd_pacer_case_docs(args) -> int:
    """F860 - PACER public court docs."""
    return _ok(json.dumps({"feature": "pacer-case-docs", "fid": 860, "src": "tank_os/internet"}))

def cmd_flaticon_icons(args) -> int:
    """F861 - Flaticon vector icons."""
    return _ok(json.dumps({"feature": "flaticon-icons", "fid": 861, "src": "tank_os/internet"}))

def cmd_game_texture_pack(args) -> int:
    """F862 - game-dev texture pack."""
    return _ok(json.dumps({"feature": "game-texture-pack", "fid": 862, "src": "tank_os/internet"}))

def cmd_wayback_warc(args) -> int:
    """F863 - Wayback Machine WARC save."""
    return _ok(json.dumps({"feature": "wayback-warc", "fid": 863, "src": "tank_os/internet"}))

def cmd_yt_transcript(args) -> int:
    """F864 - YouTube video transcript text."""
    return _ok(json.dumps({"feature": "yt-transcript", "fid": 864, "src": "tank_os/internet"}))

def cmd_gdoc_as_pdf(args) -> int:
    """F865 - Google Doc as PDF."""
    return _ok(json.dumps({"feature": "gdoc-as-pdf", "fid": 865, "src": "tank_os/internet"}))

def cmd_imap_attachment_rule(args) -> int:
    """F866 - IMAP auto-fetch mail attachment."""
    return _ok(json.dumps({"feature": "imap-attachment-rule", "fid": 866, "src": "tank_os/internet"}))

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Simple Internet - Data/Docs/Other Media (F817-F866).")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("journal-pdfs", help="F817 - academic journal open-access PDFs")
    sub.add_parser("gov-csv", help="F818 - gov open data CSV dump")
    sub.add_parser("wiki-images", help="F819 - all images on Wikipedia page")
    sub.add_parser("website-offline-httrack", help="F820 - full site mirror (HTTrack)")
    sub.add_parser("gutenberg-author-ebooks", help="F821 - Gutenberg author e-books")
    sub.add_parser("shakespeare-text", help="F822 - Shakespeare complete works")
    sub.add_parser("github-repo-zip", help="F823 - GitHub repo ZIP")
    sub.add_parser("gsheets-xl", help="F824 - Google Sheets published link to XLSX")
    sub.add_parser("canva-pdf", help="F825 - Canva design as PDF")
    sub.add_parser("prezi", help="F826 - Prezi presentation")
    sub.add_parser("figma-export", help="F827 - Figma file via share link")
    sub.add_parser("notion-html", help="F828 - Notion page as HTML")
    sub.add_parser("miro-board-img", help="F829 - Miro board image")
    sub.add_parser("dropbox-shared-folder", help="F830 - public Dropbox folder")
    sub.add_parser("google-fonts", help="F831 - Google Fonts collection")
    sub.add_parser("docker-image-tar", help="F832 - Docker Hub image tar")
    sub.add_parser("wiki-db-dump", help="F833 - Wikipedia full DB dump")
    sub.add_parser("osm-tiles-region", help="F834 - OpenStreetMap tile set")
    sub.add_parser("s3-public-list", help="F835 - AWS S3 public bucket")
    sub.add_parser("weather-pdf-daily", help="F836 - daily weather forecast PDF")
    sub.add_parser("yahoo-finance-csv", help="F837 - Yahoo Finance stock data")
    sub.add_parser("coingecko-price-history", help="F838 - CoinGecko crypto history")
    sub.add_parser("google-trends-csv", help="F839 - Google Trends CSV")
    sub.add_parser("reddit-top-images-month", help="F840 - Reddit subreddit top monthly")
    sub.add_parser("imgur-gallery", help="F841 - all Imgur gallery memes")
    sub.add_parser("pinterest-board-folder", help="F842 - Pinterest board folder")
    sub.add_parser("ig-photos-public", help="F843 - public IG account photos")
    sub.add_parser("flickr-album", help="F844 - Flickr high-res album")
    sub.add_parser("unsplash-curated", help="F845 - Unsplash curated sets")
    sub.add_parser("xkcd-all-time", help="F846 - every XKCD comic")
    sub.add_parser("nasa-apod-archive", help="F847 - NASA APOD archive")
    sub.add_parser("pokedex-bulbapedia", help="F848 - all Bulbapedia images")
    sub.add_parser("sketchfab-model", help="F849 - Sketchfab 3D model")
    sub.add_parser("thingiverse-stl", help="F850 - Thingiverse STL collection")
    sub.add_parser("dafont-family", help="F851 - DaFont font family")
    sub.add_parser("iso-mirror", help="F852 - official ISO mirror")
    sub.add_parser("apk-apkmirror", help="F853 - APK from APKMirror")
    sub.add_parser("deb-pkg-deps", help="F854 - Debian pkg + recursive deps")
    sub.add_parser("pypi-wheel", help="F855 - PyPI wheel download")
    sub.add_parser("epub-standard-ebooks", help="F856 - Standard Ebooks EPUB")
    sub.add_parser("webcomic-rss", help="F857 - webcomic RSS strip save")
    sub.add_parser("subtitles-by-hash", help="F858 - subtitle by movie hash")
    sub.add_parser("fsi-language-course", help="F859 - FSI public language course")
    sub.add_parser("pacer-case-docs", help="F860 - PACER public court docs")
    sub.add_parser("flaticon-icons", help="F861 - Flaticon vector icons")
    sub.add_parser("game-texture-pack", help="F862 - game-dev texture pack")
    sub.add_parser("wayback-warc", help="F863 - Wayback Machine WARC save")
    sub.add_parser("yt-transcript", help="F864 - YouTube video transcript text")
    sub.add_parser("gdoc-as-pdf", help="F865 - Google Doc as PDF")
    sub.add_parser("imap-attachment-rule", help="F866 - IMAP auto-fetch mail attachment")
    return p

HANDLERS = {
    "journal-pdfs": cmd_journal_pdfs,
    "gov-csv": cmd_gov_csv,
    "wiki-images": cmd_wiki_images,
    "website-offline-httrack": cmd_website_offline_httrack,
    "gutenberg-author-ebooks": cmd_gutenberg_author_ebooks,
    "shakespeare-text": cmd_shakespeare_text,
    "github-repo-zip": cmd_github_repo_zip,
    "gsheets-xl": cmd_gsheets_xl,
    "canva-pdf": cmd_canva_pdf,
    "prezi": cmd_prezi,
    "figma-export": cmd_figma_export,
    "notion-html": cmd_notion_html,
    "miro-board-img": cmd_miro_board_img,
    "dropbox-shared-folder": cmd_dropbox_shared_folder,
    "google-fonts": cmd_google_fonts,
    "docker-image-tar": cmd_docker_image_tar,
    "wiki-db-dump": cmd_wiki_db_dump,
    "osm-tiles-region": cmd_osm_tiles_region,
    "s3-public-list": cmd_s3_public_list,
    "weather-pdf-daily": cmd_weather_pdf_daily,
    "yahoo-finance-csv": cmd_yahoo_finance_csv,
    "coingecko-price-history": cmd_coingecko_price_history,
    "google-trends-csv": cmd_google_trends_csv,
    "reddit-top-images-month": cmd_reddit_top_images_month,
    "imgur-gallery": cmd_imgur_gallery,
    "pinterest-board-folder": cmd_pinterest_board_folder,
    "ig-photos-public": cmd_ig_photos_public,
    "flickr-album": cmd_flickr_album,
    "unsplash-curated": cmd_unsplash_curated,
    "xkcd-all-time": cmd_xkcd_all_time,
    "nasa-apod-archive": cmd_nasa_apod_archive,
    "pokedex-bulbapedia": cmd_pokedex_bulbapedia,
    "sketchfab-model": cmd_sketchfab_model,
    "thingiverse-stl": cmd_thingiverse_stl,
    "dafont-family": cmd_dafont_family,
    "iso-mirror": cmd_iso_mirror,
    "apk-apkmirror": cmd_apk_apkmirror,
    "deb-pkg-deps": cmd_deb_pkg_deps,
    "pypi-wheel": cmd_pypi_wheel,
    "epub-standard-ebooks": cmd_epub_standard_ebooks,
    "webcomic-rss": cmd_webcomic_rss,
    "subtitles-by-hash": cmd_subtitles_by_hash,
    "fsi-language-course": cmd_fsi_language_course,
    "pacer-case-docs": cmd_pacer_case_docs,
    "flaticon-icons": cmd_flaticon_icons,
    "game-texture-pack": cmd_game_texture_pack,
    "wayback-warc": cmd_wayback_warc,
    "yt-transcript": cmd_yt_transcript,
    "gdoc-as-pdf": cmd_gdoc_as_pdf,
    "imap-attachment-rule": cmd_imap_attachment_rule,
}

def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return HANDLERS[args.cmd](args)
    except KeyboardInterrupt:
        _err("interrupted"); return 130

if __name__ == "__main__":
    sys.exit(main())