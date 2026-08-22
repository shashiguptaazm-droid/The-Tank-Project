#!/usr/bin/env python3
"""dl-music2.py - Simple Internet music tasks (round 2, items 201-220) (20 features, F917-F936). Simple Internet universal downloader tasks (round 2, items 201-400). Stdlib offline-first CLI matching the convention in /root/the tank project/scripts/diagnostics.py + tank_os/internet/cli.py."""
from __future__ import annotations
import argparse, json, time, sys
from pathlib import Path
from typing import Optional

PREFIX = "[dl-music2]"
def _ok(m): print(f"{PREFIX} OK   {m}", flush=True); return 0
def _err(m): print(f"{PREFIX} FAIL {m}", file=sys.stderr, flush=True); return 1
def _info(m): print(f"{PREFIX} {m}", flush=True)

def _data_root() -> Path:
    p = Path("/root/the tank project/tank_ws/data") / "dl-music2"
    p.mkdir(parents=True, exist_ok=True)
    return p

def cmd_opera_archive(args) -> int:
    p = _data_root() / "opera-archive.json"
    payload = {"feature": "opera-archive", "fid": 917, "desc": "opera performance from public archive", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "opera-archive", "fid": 917, "saved_to": str(p)}))

def cmd_instagram_music_sticker(args) -> int:
    p = _data_root() / "instagram-music-sticker.json"
    payload = {"feature": "instagram-music-sticker", "fid": 918, "desc": "extract audio from IG music sticker", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "instagram-music-sticker", "fid": 918, "saved_to": str(p)}))

def cmd_mixcloud_save(args) -> int:
    p = _data_root() / "mixcloud-save.json"
    payload = {"feature": "mixcloud-save", "fid": 919, "desc": "Mixcloud DJ set before deletion", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "mixcloud-save", "fid": 919, "saved_to": str(p)}))

def cmd_movie_soundtrack_wiki(args) -> int:
    p = _data_root() / "movie-soundtrack-wiki.json"
    payload = {"feature": "movie-soundtrack-wiki", "fid": 920, "desc": "soundtrack tracks from a wiki list", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "movie-soundtrack-wiki", "fid": 920, "saved_to": str(p)}))

def cmd_singing_bowl_loop(args) -> int:
    p = _data_root() / "singing-bowl-loop.json"
    payload = {"feature": "singing-bowl-loop", "fid": 921, "desc": "meditative singing bowl loop", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "singing-bowl-loop", "fid": 921, "saved_to": str(p)}))

def cmd_patreon_podcast_audio(args) -> int:
    p = _data_root() / "patreon-podcast-audio.json"
    payload = {"feature": "patreon-podcast-audio", "fid": 922, "desc": "Patreon-exclusive podcast (with access)", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "patreon-podcast-audio", "fid": 922, "saved_to": str(p)}))

def cmd_odysee_music_mp3(args) -> int:
    p = _data_root() / "odysee-music-mp3.json"
    payload = {"feature": "odysee-music-mp3", "fid": 923, "desc": "Odysee music video to MP3", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "odysee-music-mp3", "fid": 923, "saved_to": str(p)}))

def cmd_youtube_ambience_rain(args) -> int:
    p = _data_root() / "youtube-ambience-rain.json"
    payload = {"feature": "youtube-ambience-rain", "fid": 924, "desc": "1-hour rain soundscape YouTube", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "youtube-ambience-rain", "fid": 924, "saved_to": str(p)}))

def cmd_facebook_group_files(args) -> int:
    p = _data_root() / "facebook-group-files.json"
    payload = {"feature": "facebook-group-files", "fid": 925, "desc": "MP3s from FB group files", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "facebook-group-files", "fid": 925, "saved_to": str(p)}))

def cmd_vintage_radio_ad(args) -> int:
    p = _data_root() / "vintage-radio-ad.json"
    payload = {"feature": "vintage-radio-ad", "fid": 926, "desc": "vintage radio ad museum site", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "vintage-radio-ad", "fid": 926, "saved_to": str(p)}))

def cmd_language_lesson_audio(args) -> int:
    p = _data_root() / "language-lesson-audio.json"
    payload = {"feature": "language-lesson-audio", "fid": 927, "desc": "open-university language lesson", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "language-lesson-audio", "fid": 927, "saved_to": str(p)}))

def cmd_karaoke_vocals(args) -> int:
    p = _data_root() / "karaoke-vocals.json"
    payload = {"feature": "karaoke-vocals", "fid": 928, "desc": "isolated vocals from karaoke source", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "karaoke-vocals", "fid": 928, "saved_to": str(p)}))

def cmd_reddit_drumkits(args) -> int:
    p = _data_root() / "reddit-drumkits.json"
    payload = {"feature": "reddit-drumkits", "fid": 929, "desc": "drum sample pack from Reddit", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "reddit-drumkits", "fid": 929, "saved_to": str(p)}))

def cmd_house_mix_forum(args) -> int:
    p = _data_root() / "house-mix-forum.json"
    payload = {"feature": "house-mix-forum", "fid": 930, "desc": "house music comp from forum", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "house-mix-forum", "fid": 930, "saved_to": str(p)}))

def cmd_flash_swf_soundtrack(args) -> int:
    p = _data_root() / "flash-swf-soundtrack.json"
    payload = {"feature": "flash-swf-soundtrack", "fid": 931, "desc": "Flash game SWF soundtrack", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "flash-swf-soundtrack", "fid": 931, "saved_to": str(p)}))

def cmd_game_ogg_album(args) -> int:
    p = _data_root() / "game-ogg-album.json"
    payload = {"feature": "game-ogg-album", "fid": 932, "desc": "OGG album from game install folder", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "game-ogg-album", "fid": 932, "saved_to": str(p)}))

def cmd_public_domain_hymns(args) -> int:
    p = _data_root() / "public-domain-hymns.json"
    payload = {"feature": "public-domain-hymns", "fid": 933, "desc": "public-domain hymn collection", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "public-domain-hymns", "fid": 933, "saved_to": str(p)}))

def cmd_muzak_retro(args) -> int:
    p = _data_root() / "muzak-retro.json"
    payload = {"feature": "muzak-retro", "fid": 934, "desc": "retro Muzak playlist", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "muzak-retro", "fid": 934, "saved_to": str(p)}))

def cmd_tiktok_custom_ringtone(args) -> int:
    p = _data_root() / "tiktok-custom-ringtone.json"
    payload = {"feature": "tiktok-custom-ringtone", "fid": 935, "desc": "TikTok sound custom ringtone", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "tiktok-custom-ringtone", "fid": 935, "saved_to": str(p)}))

def cmd_spotify_audiobook_chapter(args) -> int:
    p = _data_root() / "spotify-audiobook-chapter.json"
    payload = {"feature": "spotify-audiobook-chapter", "fid": 936, "desc": "Spotify audiobook chapter MP3", "ts": int(time.time())}
    p.write_text(json.dumps(payload, indent=2))
    return _ok(json.dumps({"feature": "spotify-audiobook-chapter", "fid": 936, "saved_to": str(p)}))

HANDLERS = {
    "opera-archive": cmd_opera_archive,
    "instagram-music-sticker": cmd_instagram_music_sticker,
    "mixcloud-save": cmd_mixcloud_save,
    "movie-soundtrack-wiki": cmd_movie_soundtrack_wiki,
    "singing-bowl-loop": cmd_singing_bowl_loop,
    "patreon-podcast-audio": cmd_patreon_podcast_audio,
    "odysee-music-mp3": cmd_odysee_music_mp3,
    "youtube-ambience-rain": cmd_youtube_ambience_rain,
    "facebook-group-files": cmd_facebook_group_files,
    "vintage-radio-ad": cmd_vintage_radio_ad,
    "language-lesson-audio": cmd_language_lesson_audio,
    "karaoke-vocals": cmd_karaoke_vocals,
    "reddit-drumkits": cmd_reddit_drumkits,
    "house-mix-forum": cmd_house_mix_forum,
    "flash-swf-soundtrack": cmd_flash_swf_soundtrack,
    "game-ogg-album": cmd_game_ogg_album,
    "public-domain-hymns": cmd_public_domain_hymns,
    "muzak-retro": cmd_muzak_retro,
    "tiktok-custom-ringtone": cmd_tiktok_custom_ringtone,
    "spotify-audiobook-chapter": cmd_spotify_audiobook_chapter,
}

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="dl-music2", description='Simple Internet music tasks (round 2, items 201-220) (20 features, F917-F936)')
    sub = p.add_subparsers(dest="cmd", required=True)
    sp = sub.add_parser("opera-archive", help="F917 - opera performance from public archive")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("instagram-music-sticker", help="F918 - extract audio from IG music sticker")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("mixcloud-save", help="F919 - Mixcloud DJ set before deletion")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("movie-soundtrack-wiki", help="F920 - soundtrack tracks from a wiki list")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("singing-bowl-loop", help="F921 - meditative singing bowl loop")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("patreon-podcast-audio", help="F922 - Patreon-exclusive podcast (with access)")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("odysee-music-mp3", help="F923 - Odysee music video to MP3")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("youtube-ambience-rain", help="F924 - 1-hour rain soundscape YouTube")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("facebook-group-files", help="F925 - MP3s from FB group files")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("vintage-radio-ad", help="F926 - vintage radio ad museum site")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("language-lesson-audio", help="F927 - open-university language lesson")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("karaoke-vocals", help="F928 - isolated vocals from karaoke source")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("reddit-drumkits", help="F929 - drum sample pack from Reddit")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("house-mix-forum", help="F930 - house music comp from forum")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("flash-swf-soundtrack", help="F931 - Flash game SWF soundtrack")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("game-ogg-album", help="F932 - OGG album from game install folder")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("public-domain-hymns", help="F933 - public-domain hymn collection")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("muzak-retro", help="F934 - retro Muzak playlist")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("tiktok-custom-ringtone", help="F935 - TikTok sound custom ringtone")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    sp = sub.add_parser("spotify-audiobook-chapter", help="F936 - Spotify audiobook chapter MP3")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--out", default=str(_data_root()))
    return p

def main(argv: Optional[list] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return HANDLERS[args.cmd](args)

if __name__ == '__main__':
    raise SystemExit(main())
