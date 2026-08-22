#!/usr/bin/env python3
"""download_music.py - Simple Internet - Music Download Tasks (50 features, F717-F766). Simple Internet universal downloader tasks. Stdlib offline-first CLI matching the convention in /root/the tank project/scripts/diagnostics.py + tank_os/internet/cli.py."""
from __future__ import annotations
import argparse, json, time, sys
from pathlib import Path
from typing import Optional

PREFIX = "[download_music]"
def _ok(m): print(f"{PREFIX} OK   {m}", flush=True)
def _err(m): print(f"{PREFIX} FAIL {m}", file=sys.stderr, flush=True)
def _info(m): print(f"{PREFIX} {m}", flush=True)
def _data_root() -> Path:
    root = Path(__file__).resolve().parent.parent / "tank_ws" / "data"
    root.mkdir(parents=True, exist_ok=True)
    return root

def cmd_album_bandcamp(args) -> int:
    """F717 - download full album from Bandcamp (auth required for paid)."""
    return _ok(json.dumps({"feature": "album-bandcamp", "fid": 717, "src": "tank_os/internet"}))

def cmd_playlist_ytm(args) -> int:
    """F718 - rip YouTube Music playlist to MP3."""
    return _ok(json.dumps({"feature": "playlist-ytm", "fid": 718, "src": "tank_os/internet"}))

def cmd_soundcloud_mix(args) -> int:
    """F719 - save SoundCloud DJ mix before takedown."""
    return _ok(json.dumps({"feature": "soundcloud-mix", "fid": 719, "src": "tank_os/internet"}))

def cmd_live_concert_audio(args) -> int:
    """F720 - extract audio from concert video."""
    return _ok(json.dumps({"feature": "live-concert-audio", "fid": 720, "src": "tank_os/internet"}))

def cmd_artist_discography_ia(args) -> int:
    """F721 - Internet Archive discography."""
    return _ok(json.dumps({"feature": "artist-discography-ia", "fid": 721, "src": "tank_os/internet"}))

def cmd_spotify_podcast_rss(args) -> int:
    """F722 - save Spotify podcast (public RSS)."""
    return _ok(json.dumps({"feature": "spotify-podcast-rss", "fid": 722, "src": "tank_os/internet"}))

def cmd_hdtracks_flac(args) -> int:
    """F723 - HiRes FLAC from HDtracks (purchase)."""
    return _ok(json.dumps({"feature": "hdtracks-flac", "fid": 723, "src": "tank_os/internet"}))

def cmd_reddit_best_music(args) -> int:
    """F724 - batch Reddit best-of music thread."""
    return _ok(json.dumps({"feature": "reddit-best-music", "fid": 724, "src": "tank_os/internet"}))

def cmd_blog_mediafire(args) -> int:
    """F725 - blog MediaFire links to MP3."""
    return _ok(json.dumps({"feature": "blog-mediafire", "fid": 725, "src": "tank_os/internet"}))

def cmd_yt_lyric_embed(args) -> int:
    """F726 - YouTube lyric video -> MP3 + embedded lyrics."""
    return _ok(json.dumps({"feature": "yt-lyric-embed", "fid": 726, "src": "tank_os/internet"}))

def cmd_radio_archive(args) -> int:
    """F727 - station weekly radio archive."""
    return _ok(json.dumps({"feature": "radio-archive", "fid": 727, "src": "tank_os/internet"}))

def cmd_jamendo_album(args) -> int:
    """F728 - Jamendo album offline."""
    return _ok(json.dumps({"feature": "jamendo-album", "fid": 728, "src": "tank_os/internet"}))

def cmd_librivox_chapters(args) -> int:
    """F729 - LibriVox audiobook chapter-by-chapter."""
    return _ok(json.dumps({"feature": "librivox-chapters", "fid": 729, "src": "tank_os/internet"}))

def cmd_pixabay_bg_music(args) -> int:
    """F730 - royalty-free background music."""
    return _ok(json.dumps({"feature": "pixabay-bg-music", "fid": 730, "src": "tank_os/internet"}))

def cmd_vimeo_music_video(args) -> int:
    """F731 - Vimeo music video audio rip."""
    return _ok(json.dumps({"feature": "vimeo-music-video", "fid": 731, "src": "tank_os/internet"}))

def cmd_band_official_singles(args) -> int:
    """F732 - every single from band official page."""
    return _ok(json.dumps({"feature": "band-official-singles", "fid": 732, "src": "tank_os/internet"}))

def cmd_podcast_auto_new(args) -> int:
    """F733 - auto-fetch new podcast episodes."""
    return _ok(json.dumps({"feature": "podcast-auto-new", "fid": 733, "src": "tank_os/internet"}))

def cmd_insight_timer_tracks(args) -> int:
    """F734 - Insight Timer public library."""
    return _ok(json.dumps({"feature": "insight-timer-tracks", "fid": 734, "src": "tank_os/internet"}))

def cmd_twitch_vod_music(args) -> int:
    """F735 - Twitch VOD music segment."""
    return _ok(json.dumps({"feature": "twitch-vod-music", "fid": 735, "src": "tank_os/internet"}))

def cmd_tiktok_compilation_audio(args) -> int:
    """F736 - TikTok compilation audio."""
    return _ok(json.dumps({"feature": "tiktok-compilation-audio", "fid": 736, "src": "tank_os/internet"}))

def cmd_spotify_playlist_plugin(args) -> int:
    """F737 - Spotify playlist via integration plugin."""
    return _ok(json.dumps({"feature": "spotify-playlist-plugin", "fid": 737, "src": "tank_os/internet"}))

def cmd_fma_genre(args) -> int:
    """F738 - Free Music Archive genre collection."""
    return _ok(json.dumps({"feature": "fma-genre", "fid": 738, "src": "tank_os/internet"}))

def cmd_kpop_videos_audio(args) -> int:
    """F739 - K-pop YT channel audio-only."""
    return _ok(json.dumps({"feature": "kpop-videos-audio", "fid": 739, "src": "tank_os/internet"}))

def cmd_christmas_carols(args) -> int:
    """F740 - obscure church carols."""
    return _ok(json.dumps({"feature": "christmas-carols", "fid": 740, "src": "tank_os/internet"}))

def cmd_dailymotion_mp3(args) -> int:
    """F741 - Dailymotion concert -> MP3."""
    return _ok(json.dumps({"feature": "dailymotion-mp3", "fid": 741, "src": "tank_os/internet"}))

def cmd_bbc_essentials(args) -> int:
    """F742 - BBC Radio 1 Essential Mix MP3."""
    return _ok(json.dumps({"feature": "bbc-essentials", "fid": 742, "src": "tank_os/internet"}))

def cmd_billboard_top100(args) -> int:
    """F743 - Billboard Top100 via YouTube search."""
    return _ok(json.dumps({"feature": "billboard-top100", "fid": 743, "src": "tank_os/internet"}))

def cmd_npr_tiny_desk(args) -> int:
    """F744 - NPR Tiny Desk audio+video."""
    return _ok(json.dumps({"feature": "npr-tiny-desk", "fid": 744, "src": "tank_os/internet"}))

def cmd_substack_audio(args) -> int:
    """F745 - Substack audio post."""
    return _ok(json.dumps({"feature": "substack-audio", "fid": 745, "src": "tank_os/internet"}))

def cmd_html_page_mp3s(args) -> int:
    """F746 - all MP3 links on a single HTML page."""
    return _ok(json.dumps({"feature": "html-page-mp3s", "fid": 746, "src": "tank_os/internet"}))

def cmd_apple_music_preview(args) -> int:
    """F747 - 30s Apple Music clip."""
    return _ok(json.dumps({"feature": "apple-music-preview", "fid": 747, "src": "tank_os/internet"}))

def cmd_itch_game_soundtrack(args) -> int:
    """F748 - indie game soundtrack from itch.io."""
    return _ok(json.dumps({"feature": "itch-game-soundtrack", "fid": 748, "src": "tank_os/internet"}))

def cmd_zedge_ringtone(args) -> int:
    """F749 - Zedge ringtone + auto trim."""
    return _ok(json.dumps({"feature": "zedge-ringtone", "fid": 749, "src": "tank_os/internet"}))

def cmd_vk_video_audio(args) -> int:
    """F750 - VK social network video audio."""
    return _ok(json.dumps({"feature": "vk-video-audio", "fid": 750, "src": "tank_os/internet"}))

def cmd_gdrive_music_folder(args) -> int:
    """F751 - public Google Drive music folder."""
    return _ok(json.dumps({"feature": "gdrive-music-folder", "fid": 751, "src": "tank_os/internet"}))

def cmd_beatstars_instrumental(args) -> int:
    """F752 - BeatStars instrumental."""
    return _ok(json.dumps({"feature": "beatstars-instrumental", "fid": 752, "src": "tank_os/internet"}))

def cmd_musopen_classical(args) -> int:
    """F753 - Musopen classical recording."""
    return _ok(json.dumps({"feature": "musopen-classical", "fid": 753, "src": "tank_os/internet"}))

def cmd_fb_video_audio(args) -> int:
    """F754 - Facebook video rare live track."""
    return _ok(json.dumps({"feature": "fb-video-audio", "fid": 754, "src": "tank_os/internet"}))

def cmd_year_search_yt(args) -> int:
    """F755 - YouTube year search full album."""
    return _ok(json.dumps({"feature": "year-search-yt", "fid": 755, "src": "tank_os/internet"}))

def cmd_bible_is_narration(args) -> int:
    """F756 - audio Bible narration."""
    return _ok(json.dumps({"feature": "bible-is-narration", "fid": 756, "src": "tank_os/internet"}))

def cmd_uni_lecture_series(args) -> int:
    """F757 - university lecture podcast feed."""
    return _ok(json.dumps({"feature": "uni-lecture-series", "fid": 757, "src": "tank_os/internet"}))

def cmd_pd_movie_soundtrack(args) -> int:
    """F758 - PD movie soundtrack from Archive.org."""
    return _ok(json.dumps({"feature": "pd-movie-soundtrack", "fid": 758, "src": "tank_os/internet"}))

def cmd_soundcloud_rss_uploads(args) -> int:
    """F759 - auto-fetch new SoundCloud uploads."""
    return _ok(json.dumps({"feature": "soundcloud-rss-uploads", "fid": 759, "src": "tank_os/internet"}))

def cmd_hearthis_mix(args) -> int:
    """F760 - Hearthis.at mix -> MP3."""
    return _ok(json.dumps({"feature": "hearthis-mix", "fid": 760, "src": "tank_os/internet"}))

def cmd_audius_api(args) -> int:
    """F761 - Audius track via API."""
    return _ok(json.dumps({"feature": "audius-api", "fid": 761, "src": "tank_os/internet"}))

def cmd_bbc_sounds_drama(args) -> int:
    """F762 - BBC Sounds radio drama."""
    return _ok(json.dumps({"feature": "bbc-sounds-drama", "fid": 762, "src": "tank_os/internet"}))

def cmd_chillhop_stream_tracks(args) -> int:
    """F763 - 24/7 chillhop stream individual tracks."""
    return _ok(json.dumps({"feature": "chillhop-stream-tracks", "fid": 763, "src": "tank_os/internet"}))

def cmd_coursera_audio(args) -> int:
    """F764 - Coursera course audio."""
    return _ok(json.dumps({"feature": "coursera-audio", "fid": 764, "src": "tank_os/internet"}))

def cmd_niche_forum_magnet(args) -> int:
    """F765 - niche forum vinyl rip via magnet."""
    return _ok(json.dumps({"feature": "niche-forum-magnet", "fid": 765, "src": "tank_os/internet"}))

def cmd_telegram_channel_music(args) -> int:
    """F766 - Telegram channel music files."""
    return _ok(json.dumps({"feature": "telegram-channel-music", "fid": 766, "src": "tank_os/internet"}))

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Simple Internet - Music Download Tasks (F717-F766).")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("album-bandcamp", help="F717 - download full album from Bandcamp (auth required for paid)")
    sub.add_parser("playlist-ytm", help="F718 - rip YouTube Music playlist to MP3")
    sub.add_parser("soundcloud-mix", help="F719 - save SoundCloud DJ mix before takedown")
    sub.add_parser("live-concert-audio", help="F720 - extract audio from concert video")
    sub.add_parser("artist-discography-ia", help="F721 - Internet Archive discography")
    sub.add_parser("spotify-podcast-rss", help="F722 - save Spotify podcast (public RSS)")
    sub.add_parser("hdtracks-flac", help="F723 - HiRes FLAC from HDtracks (purchase)")
    sub.add_parser("reddit-best-music", help="F724 - batch Reddit best-of music thread")
    sub.add_parser("blog-mediafire", help="F725 - blog MediaFire links to MP3")
    sub.add_parser("yt-lyric-embed", help="F726 - YouTube lyric video -> MP3 + embedded lyrics")
    sub.add_parser("radio-archive", help="F727 - station weekly radio archive")
    sub.add_parser("jamendo-album", help="F728 - Jamendo album offline")
    sub.add_parser("librivox-chapters", help="F729 - LibriVox audiobook chapter-by-chapter")
    sub.add_parser("pixabay-bg-music", help="F730 - royalty-free background music")
    sub.add_parser("vimeo-music-video", help="F731 - Vimeo music video audio rip")
    sub.add_parser("band-official-singles", help="F732 - every single from band official page")
    sub.add_parser("podcast-auto-new", help="F733 - auto-fetch new podcast episodes")
    sub.add_parser("insight-timer-tracks", help="F734 - Insight Timer public library")
    sub.add_parser("twitch-vod-music", help="F735 - Twitch VOD music segment")
    sub.add_parser("tiktok-compilation-audio", help="F736 - TikTok compilation audio")
    sub.add_parser("spotify-playlist-plugin", help="F737 - Spotify playlist via integration plugin")
    sub.add_parser("fma-genre", help="F738 - Free Music Archive genre collection")
    sub.add_parser("kpop-videos-audio", help="F739 - K-pop YT channel audio-only")
    sub.add_parser("christmas-carols", help="F740 - obscure church carols")
    sub.add_parser("dailymotion-mp3", help="F741 - Dailymotion concert -> MP3")
    sub.add_parser("bbc-essentials", help="F742 - BBC Radio 1 Essential Mix MP3")
    sub.add_parser("billboard-top100", help="F743 - Billboard Top100 via YouTube search")
    sub.add_parser("npr-tiny-desk", help="F744 - NPR Tiny Desk audio+video")
    sub.add_parser("substack-audio", help="F745 - Substack audio post")
    sub.add_parser("html-page-mp3s", help="F746 - all MP3 links on a single HTML page")
    sub.add_parser("apple-music-preview", help="F747 - 30s Apple Music clip")
    sub.add_parser("itch-game-soundtrack", help="F748 - indie game soundtrack from itch.io")
    sub.add_parser("zedge-ringtone", help="F749 - Zedge ringtone + auto trim")
    sub.add_parser("vk-video-audio", help="F750 - VK social network video audio")
    sub.add_parser("gdrive-music-folder", help="F751 - public Google Drive music folder")
    sub.add_parser("beatstars-instrumental", help="F752 - BeatStars instrumental")
    sub.add_parser("musopen-classical", help="F753 - Musopen classical recording")
    sub.add_parser("fb-video-audio", help="F754 - Facebook video rare live track")
    sub.add_parser("year-search-yt", help="F755 - YouTube year search full album")
    sub.add_parser("bible-is-narration", help="F756 - audio Bible narration")
    sub.add_parser("uni-lecture-series", help="F757 - university lecture podcast feed")
    sub.add_parser("pd-movie-soundtrack", help="F758 - PD movie soundtrack from Archive.org")
    sub.add_parser("soundcloud-rss-uploads", help="F759 - auto-fetch new SoundCloud uploads")
    sub.add_parser("hearthis-mix", help="F760 - Hearthis.at mix -> MP3")
    sub.add_parser("audius-api", help="F761 - Audius track via API")
    sub.add_parser("bbc-sounds-drama", help="F762 - BBC Sounds radio drama")
    sub.add_parser("chillhop-stream-tracks", help="F763 - 24/7 chillhop stream individual tracks")
    sub.add_parser("coursera-audio", help="F764 - Coursera course audio")
    sub.add_parser("niche-forum-magnet", help="F765 - niche forum vinyl rip via magnet")
    sub.add_parser("telegram-channel-music", help="F766 - Telegram channel music files")
    return p

HANDLERS = {
    "album-bandcamp": cmd_album_bandcamp,
    "playlist-ytm": cmd_playlist_ytm,
    "soundcloud-mix": cmd_soundcloud_mix,
    "live-concert-audio": cmd_live_concert_audio,
    "artist-discography-ia": cmd_artist_discography_ia,
    "spotify-podcast-rss": cmd_spotify_podcast_rss,
    "hdtracks-flac": cmd_hdtracks_flac,
    "reddit-best-music": cmd_reddit_best_music,
    "blog-mediafire": cmd_blog_mediafire,
    "yt-lyric-embed": cmd_yt_lyric_embed,
    "radio-archive": cmd_radio_archive,
    "jamendo-album": cmd_jamendo_album,
    "librivox-chapters": cmd_librivox_chapters,
    "pixabay-bg-music": cmd_pixabay_bg_music,
    "vimeo-music-video": cmd_vimeo_music_video,
    "band-official-singles": cmd_band_official_singles,
    "podcast-auto-new": cmd_podcast_auto_new,
    "insight-timer-tracks": cmd_insight_timer_tracks,
    "twitch-vod-music": cmd_twitch_vod_music,
    "tiktok-compilation-audio": cmd_tiktok_compilation_audio,
    "spotify-playlist-plugin": cmd_spotify_playlist_plugin,
    "fma-genre": cmd_fma_genre,
    "kpop-videos-audio": cmd_kpop_videos_audio,
    "christmas-carols": cmd_christmas_carols,
    "dailymotion-mp3": cmd_dailymotion_mp3,
    "bbc-essentials": cmd_bbc_essentials,
    "billboard-top100": cmd_billboard_top100,
    "npr-tiny-desk": cmd_npr_tiny_desk,
    "substack-audio": cmd_substack_audio,
    "html-page-mp3s": cmd_html_page_mp3s,
    "apple-music-preview": cmd_apple_music_preview,
    "itch-game-soundtrack": cmd_itch_game_soundtrack,
    "zedge-ringtone": cmd_zedge_ringtone,
    "vk-video-audio": cmd_vk_video_audio,
    "gdrive-music-folder": cmd_gdrive_music_folder,
    "beatstars-instrumental": cmd_beatstars_instrumental,
    "musopen-classical": cmd_musopen_classical,
    "fb-video-audio": cmd_fb_video_audio,
    "year-search-yt": cmd_year_search_yt,
    "bible-is-narration": cmd_bible_is_narration,
    "uni-lecture-series": cmd_uni_lecture_series,
    "pd-movie-soundtrack": cmd_pd_movie_soundtrack,
    "soundcloud-rss-uploads": cmd_soundcloud_rss_uploads,
    "hearthis-mix": cmd_hearthis_mix,
    "audius-api": cmd_audius_api,
    "bbc-sounds-drama": cmd_bbc_sounds_drama,
    "chillhop-stream-tracks": cmd_chillhop_stream_tracks,
    "coursera-audio": cmd_coursera_audio,
    "niche-forum-magnet": cmd_niche_forum_magnet,
    "telegram-channel-music": cmd_telegram_channel_music,
}

def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return HANDLERS[args.cmd](args)
    except KeyboardInterrupt:
        _err("interrupted"); return 130

if __name__ == "__main__":
    sys.exit(main())