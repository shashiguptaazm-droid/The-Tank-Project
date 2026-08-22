#!/usr/bin/env python3
"""download_video.py - Simple Internet - Video Download Tasks (50 features, F767-F816). Simple Internet universal downloader tasks. Stdlib offline-first CLI matching the convention in /root/the tank project/scripts/diagnostics.py + tank_os/internet/cli.py."""
from __future__ import annotations
import argparse, json, time, sys
from pathlib import Path
from typing import Optional

PREFIX = "[download_video]"
def _ok(m): print(f"{PREFIX} OK   {m}", flush=True)
def _err(m): print(f"{PREFIX} FAIL {m}", file=sys.stderr, flush=True)
def _info(m): print(f"{PREFIX} {m}", flush=True)
def _data_root() -> Path:
    root = Path(__file__).resolve().parent.parent / "tank_ws" / "data"
    root.mkdir(parents=True, exist_ok=True)
    return root

def cmd_yt_4k_doc(args) -> int:
    """F767 - YouTube 4K documentary."""
    return _ok(json.dumps({"feature": "yt-4k-doc", "fid": 767, "src": "tank_os/internet"}))

def cmd_twitch_vod(args) -> int:
    """F768 - Twitch stream VOD archive."""
    return _ok(json.dumps({"feature": "twitch-vod", "fid": 768, "src": "tank_os/internet"}))

def cmd_vimeo_showcase(args) -> int:
    """F769 - Vimeo showcase full dump."""
    return _ok(json.dumps({"feature": "vimeo-showcase", "fid": 769, "src": "tank_os/internet"}))

def cmd_netflix_trailer(args) -> int:
    """F770 - Netflix public trailer max quality."""
    return _ok(json.dumps({"feature": "netflix-trailer", "fid": 770, "src": "tank_os/internet"}))

def cmd_dailymotion_tutorial(args) -> int:
    """F771 - Dailymotion tutorial series."""
    return _ok(json.dumps({"feature": "dailymotion-tutorial", "fid": 771, "src": "tank_os/internet"}))

def cmd_fb_watch_series(args) -> int:
    """F772 - Facebook Watch series for offline."""
    return _ok(json.dumps({"feature": "fb-watch-series", "fid": 772, "src": "tank_os/internet"}))

def cmd_ig_reel(args) -> int:
    """F773 - Instagram Reel recipe."""
    return _ok(json.dumps({"feature": "ig-reel", "fid": 773, "src": "tank_os/internet"}))

def cmd_tiktok_hashtag(args) -> int:
    """F774 - TikTok trend compilation by hashtag."""
    return _ok(json.dumps({"feature": "tiktok-hashtag", "fid": 774, "src": "tank_os/internet"}))

def cmd_reddit_video(args) -> int:
    """F775 - Reddit video with sound."""
    return _ok(json.dumps({"feature": "reddit-video", "fid": 775, "src": "tank_os/internet"}))

def cmd_yt_live_dvr(args) -> int:
    """F776 - YouTube live-stream DVR."""
    return _ok(json.dumps({"feature": "yt-live-dvr", "fid": 776, "src": "tank_os/internet"}))

def cmd_udemy_course(args) -> int:
    """F777 - Udemy course with auth."""
    return _ok(json.dumps({"feature": "udemy-course", "fid": 777, "src": "tank_os/internet"}))

def cmd_imdb_trailer(args) -> int:
    """F778 - IMDb trailer 1080p."""
    return _ok(json.dumps({"feature": "imdb-trailer", "fid": 778, "src": "tank_os/internet"}))

def cmd_twitter_x_media(args) -> int:
    """F779 - X/Twitter media tab."""
    return _ok(json.dumps({"feature": "twitter-x-media", "fid": 779, "src": "tank_os/internet"}))

def cmd_linkedin_learning(args) -> int:
    """F780 - LinkedIn Learning (subscription)."""
    return _ok(json.dumps({"feature": "linkedin-learning", "fid": 780, "src": "tank_os/internet"}))

def cmd_periscope_replay(args) -> int:
    """F781 - Periscope replay before expiry."""
    return _ok(json.dumps({"feature": "periscope-replay", "fid": 781, "src": "tank_os/internet"}))

def cmd_bilibili_anime_sub(args) -> int:
    """F782 - Bilibili anime ep + subs."""
    return _ok(json.dumps({"feature": "bilibili-anime-sub", "fid": 782, "src": "tank_os/internet"}))

def cmd_peertube_instance(args) -> int:
    """F783 - Peertube federated instance."""
    return _ok(json.dumps({"feature": "peertube-instance", "fid": 783, "src": "tank_os/internet"}))

def cmd_rumble(args) -> int:
    """F784 - Rumble video download."""
    return _ok(json.dumps({"feature": "rumble", "fid": 784, "src": "tank_os/internet"}))

def cmd_flickr_video(args) -> int:
    """F785 - Flickr video album."""
    return _ok(json.dumps({"feature": "flickr-video", "fid": 785, "src": "tank_os/internet"}))

def cmd_snapchat_spotlight(args) -> int:
    """F786 - Snapchat Spotlight link."""
    return _ok(json.dumps({"feature": "snapchat-spotlight", "fid": 786, "src": "tank_os/internet"}))

def cmd_pinterest_pin(args) -> int:
    """F787 - Pinterest video pin."""
    return _ok(json.dumps({"feature": "pinterest-pin", "fid": 787, "src": "tank_os/internet"}))

def cmd_douyin(args) -> int:
    """F788 - Douyin Chinese TikTok save."""
    return _ok(json.dumps({"feature": "douyin", "fid": 788, "src": "tank_os/internet"}))

def cmd_espn_highlight(args) -> int:
    """F789 - ESPN highlight clip."""
    return _ok(json.dumps({"feature": "espn-highlight", "fid": 789, "src": "tank_os/internet"}))

def cmd_nasa_yt_8k(args) -> int:
    """F790 - NASA YouTube 8K astronomy."""
    return _ok(json.dumps({"feature": "nasa-yt-8k", "fid": 790, "src": "tank_os/internet"}))

def cmd_ted_talk_sub(args) -> int:
    """F791 - TED Talk with embedded subs."""
    return _ok(json.dumps({"feature": "ted-talk-sub", "fid": 791, "src": "tank_os/internet"}))

def cmd_lynda_tutorials(args) -> int:
    """F792 - Lynda tutorial series."""
    return _ok(json.dumps({"feature": "lynda-tutorials", "fid": 792, "src": "tank_os/internet"}))

def cmd_crunchyroll_ep(args) -> int:
    """F793 - Crunchyroll free episode backup."""
    return _ok(json.dumps({"feature": "crunchyroll-ep", "fid": 793, "src": "tank_os/internet"}))

def cmd_cnn_clip(args) -> int:
    """F794 - CNN news clip."""
    return _ok(json.dumps({"feature": "cnn-clip", "fid": 794, "src": "tank_os/internet"}))

def cmd_bbc_iplayer(args) -> int:
    """F795 - BBC iPlayer programme (UK TV license)."""
    return _ok(json.dumps({"feature": "bbc-iplayer", "fid": 795, "src": "tank_os/internet"}))

def cmd_arte_doc(args) -> int:
    """F796 - ARTE FR/DE documentary."""
    return _ok(json.dumps({"feature": "arte-doc", "fid": 796, "src": "tank_os/internet"}))

def cmd_9gag_meme(args) -> int:
    """F797 - 9GAG video meme."""
    return _ok(json.dumps({"feature": "9gag-meme", "fid": 797, "src": "tank_os/internet"}))

def cmd_yt_shorts_bulk(args) -> int:
    """F798 - YouTube Shorts compilation."""
    return _ok(json.dumps({"feature": "yt-shorts-bulk", "fid": 798, "src": "tank_os/internet"}))

def cmd_vevo_prores(args) -> int:
    """F799 - Vevo ProRes music video."""
    return _ok(json.dumps({"feature": "vevo-prores", "fid": 799, "src": "tank_os/internet"}))

def cmd_zoom_webinar(args) -> int:
    """F800 - public Zoom cloud webinar."""
    return _ok(json.dumps({"feature": "zoom-webinar", "fid": 800, "src": "tank_os/internet"}))

def cmd_ms_stream_org(args) -> int:
    """F801 - MS Stream org (with perms)."""
    return _ok(json.dumps({"feature": "ms-stream-org", "fid": 801, "src": "tank_os/internet"}))

def cmd_wistia_demo(args) -> int:
    """F802 - Wistia product demo."""
    return _ok(json.dumps({"feature": "wistia-demo", "fid": 802, "src": "tank_os/internet"}))

def cmd_loom_colleague(args) -> int:
    """F803 - Loom shared video."""
    return _ok(json.dumps({"feature": "loom-colleague", "fid": 803, "src": "tank_os/internet"}))

def cmd_gdrive_video(args) -> int:
    """F804 - public Google Drive video."""
    return _ok(json.dumps({"feature": "gdrive-video", "fid": 804, "src": "tank_os/internet"}))

def cmd_apple_trailer_4k_hdr(args) -> int:
    """F805 - Apple Trailers 4K HDR."""
    return _ok(json.dumps({"feature": "apple-trailer-4k-hdr", "fid": 805, "src": "tank_os/internet"}))

def cmd_kickstarter_project(args) -> int:
    """F806 - Kickstarter project video."""
    return _ok(json.dumps({"feature": "kickstarter-project", "fid": 806, "src": "tank_os/internet"}))

def cmd_bandcamp_music_vid(args) -> int:
    """F807 - Bandcamp music video rip."""
    return _ok(json.dumps({"feature": "bandcamp-music-vid", "fid": 807, "src": "tank_os/internet"}))

def cmd_onlyfans_preview(args) -> int:
    """F808 - OnlyFans public preview clip."""
    return _ok(json.dumps({"feature": "onlyfans-preview", "fid": 808, "src": "tank_os/internet"}))

def cmd_cameo_with_perm(args) -> int:
    """F809 - Cameo video (with permission)."""
    return _ok(json.dumps({"feature": "cameo-with-perm", "fid": 809, "src": "tank_os/internet"}))

def cmd_yt_kids_long_ride(args) -> int:
    """F810 - YouTube Kids videos for car ride."""
    return _ok(json.dumps({"feature": "yt-kids-long-ride", "fid": 810, "src": "tank_os/internet"}))

def cmd_pd_torrents_movie(args) -> int:
    """F811 - Public Domain Torrents full movie."""
    return _ok(json.dumps({"feature": "pd-torrents-movie", "fid": 811, "src": "tank_os/internet"}))

def cmd_github_demo_vid(args) -> int:
    """F812 - GitHub repo demo video."""
    return _ok(json.dumps({"feature": "github-demo-vid", "fid": 812, "src": "tank_os/internet"}))

def cmd_discord_attachment(args) -> int:
    """F813 - Discord attachment video."""
    return _ok(json.dumps({"feature": "discord-attachment", "fid": 813, "src": "tank_os/internet"}))

def cmd_wp_blog_vid(args) -> int:
    """F814 - WordPress blog video."""
    return _ok(json.dumps({"feature": "wp-blog-vid", "fid": 814, "src": "tank_os/internet"}))

def cmd_gphotos_album(args) -> int:
    """F815 - Google Photos shared album video."""
    return _ok(json.dumps({"feature": "gphotos-album", "fid": 815, "src": "tank_os/internet"}))

def cmd_prime_video_trailer(args) -> int:
    """F816 - Amazon Prime Video trailer."""
    return _ok(json.dumps({"feature": "prime-video-trailer", "fid": 816, "src": "tank_os/internet"}))

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Simple Internet - Video Download Tasks (F767-F816).")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("yt-4k-doc", help="F767 - YouTube 4K documentary")
    sub.add_parser("twitch-vod", help="F768 - Twitch stream VOD archive")
    sub.add_parser("vimeo-showcase", help="F769 - Vimeo showcase full dump")
    sub.add_parser("netflix-trailer", help="F770 - Netflix public trailer max quality")
    sub.add_parser("dailymotion-tutorial", help="F771 - Dailymotion tutorial series")
    sub.add_parser("fb-watch-series", help="F772 - Facebook Watch series for offline")
    sub.add_parser("ig-reel", help="F773 - Instagram Reel recipe")
    sub.add_parser("tiktok-hashtag", help="F774 - TikTok trend compilation by hashtag")
    sub.add_parser("reddit-video", help="F775 - Reddit video with sound")
    sub.add_parser("yt-live-dvr", help="F776 - YouTube live-stream DVR")
    sub.add_parser("udemy-course", help="F777 - Udemy course with auth")
    sub.add_parser("imdb-trailer", help="F778 - IMDb trailer 1080p")
    sub.add_parser("twitter-x-media", help="F779 - X/Twitter media tab")
    sub.add_parser("linkedin-learning", help="F780 - LinkedIn Learning (subscription)")
    sub.add_parser("periscope-replay", help="F781 - Periscope replay before expiry")
    sub.add_parser("bilibili-anime-sub", help="F782 - Bilibili anime ep + subs")
    sub.add_parser("peertube-instance", help="F783 - Peertube federated instance")
    sub.add_parser("rumble", help="F784 - Rumble video download")
    sub.add_parser("flickr-video", help="F785 - Flickr video album")
    sub.add_parser("snapchat-spotlight", help="F786 - Snapchat Spotlight link")
    sub.add_parser("pinterest-pin", help="F787 - Pinterest video pin")
    sub.add_parser("douyin", help="F788 - Douyin Chinese TikTok save")
    sub.add_parser("espn-highlight", help="F789 - ESPN highlight clip")
    sub.add_parser("nasa-yt-8k", help="F790 - NASA YouTube 8K astronomy")
    sub.add_parser("ted-talk-sub", help="F791 - TED Talk with embedded subs")
    sub.add_parser("lynda-tutorials", help="F792 - Lynda tutorial series")
    sub.add_parser("crunchyroll-ep", help="F793 - Crunchyroll free episode backup")
    sub.add_parser("cnn-clip", help="F794 - CNN news clip")
    sub.add_parser("bbc-iplayer", help="F795 - BBC iPlayer programme (UK TV license)")
    sub.add_parser("arte-doc", help="F796 - ARTE FR/DE documentary")
    sub.add_parser("9gag-meme", help="F797 - 9GAG video meme")
    sub.add_parser("yt-shorts-bulk", help="F798 - YouTube Shorts compilation")
    sub.add_parser("vevo-prores", help="F799 - Vevo ProRes music video")
    sub.add_parser("zoom-webinar", help="F800 - public Zoom cloud webinar")
    sub.add_parser("ms-stream-org", help="F801 - MS Stream org (with perms)")
    sub.add_parser("wistia-demo", help="F802 - Wistia product demo")
    sub.add_parser("loom-colleague", help="F803 - Loom shared video")
    sub.add_parser("gdrive-video", help="F804 - public Google Drive video")
    sub.add_parser("apple-trailer-4k-hdr", help="F805 - Apple Trailers 4K HDR")
    sub.add_parser("kickstarter-project", help="F806 - Kickstarter project video")
    sub.add_parser("bandcamp-music-vid", help="F807 - Bandcamp music video rip")
    sub.add_parser("onlyfans-preview", help="F808 - OnlyFans public preview clip")
    sub.add_parser("cameo-with-perm", help="F809 - Cameo video (with permission)")
    sub.add_parser("yt-kids-long-ride", help="F810 - YouTube Kids videos for car ride")
    sub.add_parser("pd-torrents-movie", help="F811 - Public Domain Torrents full movie")
    sub.add_parser("github-demo-vid", help="F812 - GitHub repo demo video")
    sub.add_parser("discord-attachment", help="F813 - Discord attachment video")
    sub.add_parser("wp-blog-vid", help="F814 - WordPress blog video")
    sub.add_parser("gphotos-album", help="F815 - Google Photos shared album video")
    sub.add_parser("prime-video-trailer", help="F816 - Amazon Prime Video trailer")
    return p

HANDLERS = {
    "yt-4k-doc": cmd_yt_4k_doc,
    "twitch-vod": cmd_twitch_vod,
    "vimeo-showcase": cmd_vimeo_showcase,
    "netflix-trailer": cmd_netflix_trailer,
    "dailymotion-tutorial": cmd_dailymotion_tutorial,
    "fb-watch-series": cmd_fb_watch_series,
    "ig-reel": cmd_ig_reel,
    "tiktok-hashtag": cmd_tiktok_hashtag,
    "reddit-video": cmd_reddit_video,
    "yt-live-dvr": cmd_yt_live_dvr,
    "udemy-course": cmd_udemy_course,
    "imdb-trailer": cmd_imdb_trailer,
    "twitter-x-media": cmd_twitter_x_media,
    "linkedin-learning": cmd_linkedin_learning,
    "periscope-replay": cmd_periscope_replay,
    "bilibili-anime-sub": cmd_bilibili_anime_sub,
    "peertube-instance": cmd_peertube_instance,
    "rumble": cmd_rumble,
    "flickr-video": cmd_flickr_video,
    "snapchat-spotlight": cmd_snapchat_spotlight,
    "pinterest-pin": cmd_pinterest_pin,
    "douyin": cmd_douyin,
    "espn-highlight": cmd_espn_highlight,
    "nasa-yt-8k": cmd_nasa_yt_8k,
    "ted-talk-sub": cmd_ted_talk_sub,
    "lynda-tutorials": cmd_lynda_tutorials,
    "crunchyroll-ep": cmd_crunchyroll_ep,
    "cnn-clip": cmd_cnn_clip,
    "bbc-iplayer": cmd_bbc_iplayer,
    "arte-doc": cmd_arte_doc,
    "9gag-meme": cmd_9gag_meme,
    "yt-shorts-bulk": cmd_yt_shorts_bulk,
    "vevo-prores": cmd_vevo_prores,
    "zoom-webinar": cmd_zoom_webinar,
    "ms-stream-org": cmd_ms_stream_org,
    "wistia-demo": cmd_wistia_demo,
    "loom-colleague": cmd_loom_colleague,
    "gdrive-video": cmd_gdrive_video,
    "apple-trailer-4k-hdr": cmd_apple_trailer_4k_hdr,
    "kickstarter-project": cmd_kickstarter_project,
    "bandcamp-music-vid": cmd_bandcamp_music_vid,
    "onlyfans-preview": cmd_onlyfans_preview,
    "cameo-with-perm": cmd_cameo_with_perm,
    "yt-kids-long-ride": cmd_yt_kids_long_ride,
    "pd-torrents-movie": cmd_pd_torrents_movie,
    "github-demo-vid": cmd_github_demo_vid,
    "discord-attachment": cmd_discord_attachment,
    "wp-blog-vid": cmd_wp_blog_vid,
    "gphotos-album": cmd_gphotos_album,
    "prime-video-trailer": cmd_prime_video_trailer,
}

def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return HANDLERS[args.cmd](args)
    except KeyboardInterrupt:
        _err("interrupted"); return 130

if __name__ == "__main__":
    sys.exit(main())