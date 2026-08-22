#!/usr/bin/env python3
"""
TankOS — Download Everything Script.

Downloads ALL items from the PreloadManager manifest that have download URLs.
Runs with resume support, progress logging, and retry logic.

Usage:
    python3 tank_os/scripts/download_everything.py              # Full download
    python3 tank_os/scripts/download_everything.py --llm-only   # Only LLM models
    python3 tank_os/scripts/download_everything.py --check      # Just check what's needed
"""

import argparse
import json
import logging
import os
import shutil
import sys
import time
from pathlib import Path

# Ensure tank_os is importable
# Resolve project root: tank_os/scripts/download_everything.py -> tank_os/ -> project root
_PROJECT_ROOT = str(Path(__file__).resolve().parents[2])
sys.path.insert(0, _PROJECT_ROOT)

from tank_os.preload.manifest import MANIFEST, downloadable_items, summary
from tank_os.preload.downloader import DownloadEngine, DownloadStatus


def setup_logging():
    log_dir = Path("/var/log/tank_os")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "download.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return logging.getLogger("tank_os.download_all")


def progress_printer(logger):
    """Create a progress callback function."""
    last_pct = {}

    def on_progress(progress):
        item_id = progress.item_id
        pct = int(progress.percent)

        # Only log every 10% or on status change
        if item_id not in last_pct or abs(pct - last_pct.get(item_id, 0)) >= 10:
            last_pct[item_id] = pct
            mb = progress.bytes_downloaded / 1_048_576
            total_mb = progress.bytes_total / 1_048_576
            speed = progress.speed_bps / 1_048_576  # MB/s
            status = progress.status.value

            if progress.status == DownloadStatus.FAILED:
                logger.error(f"  ✗ {item_id}: {progress.error}")
            elif progress.status == DownloadStatus.COMPLETED:
                logger.info(f"  ✅ {item_id}: {mb:.0f} MB — DONE")
            elif progress.status == DownloadStatus.DOWNLOADING and total_mb > 0:
                logger.info(f"  ↓ {item_id}: {pct}% ({mb:.0f}/{total_mb:.0f} MB @ {speed:.1f} MB/s)")
            elif progress.status == DownloadStatus.VERIFYING:
                logger.info(f"  ✓ {item_id}: verifying checksum...")
            elif progress.status == DownloadStatus.INSTALLING:
                logger.info(f"  📦 {item_id}: installing...")
            elif progress.status == DownloadStatus.SKIPPED:
                logger.info(f"  ⏭ {item_id}: skipped ({progress.error or 'no URL'})")

    return on_progress


def print_manifest_summary(logger):
    """Print a summary of the manifest."""
    s = summary()
    logger.info("=" * 60)
    logger.info("  🤖 TankOS Preload Manifest Summary")
    logger.info("=" * 60)
    logger.info(f"  Total items:    {s['total_items']}")
    logger.info(f"  Total size:     {s['total_size_mb']:.1f} MB")
    logger.info(f"  Required items: {s['required_items']}")
    logger.info(f"  Downloadable:   {len(downloadable_items())} items with URLs")
    logger.info("-" * 60)

    for cat, count in sorted(s['categories'].items()):
        size = sum(i.size_mb for i in MANIFEST.values() if i.category == cat)
        dl = sum(1 for i in MANIFEST.values() if i.category == cat and i.url and not i.verify_only)
        logger.info(f"  {cat:25s} : {count:2d} items, {size:7.1f} MB ({dl} downloadable)")
    logger.info("=" * 60)


def print_download_plan(logger):
    """Print which items will be downloaded."""
    items = downloadable_items()
    logger.info(f"\n📋 Download plan: {len(items)} items ({sum(i.size_mb for i in items):.0f} MB total)")
    logger.info("-" * 60)
    
    for item in sorted(items, key=lambda x: -x.size_mb):
        url_short = item.url.split("/")[-1] if item.url else "N/A"
        flag = "⬛ REQUIRED" if item.required else "⬜ optional"
        logger.info(f"  {flag} {item.name:45s} {item.size_mb:7.1f} MB  → {url_short[:40]}")
    
    logger.info("-" * 60)
    logger.info(f"  Total: {sum(i.size_mb for i in items):.0f} MB across {len(items)} files")
    logger.info("")


def run_download(args, logger):
    """Run the full download process."""
    logger.info("🚀 Starting TankOS download process...")
    print_manifest_summary(logger)

    # Get items to download
    items = downloadable_items()

    if args.llm_only:
        items = [i for i in items if i.category == "llm"]
        logger.info(f"🔤 LLM-only mode: {len(items)} items")
    elif args.category:
        items = [i for i in items if i.category == args.category]
        logger.info(f"📁 Category '{args.category}': {len(items)} items")

    if not items:
        logger.warning("⚠️  No items to download!")
        return

    print_download_plan(logger)

    # Check disk space
    total_needed = sum(i.size_mb for i in items) * 1.2  # 20% buffer
    _, _, free = shutil.disk_usage("/")
    free_mb = free / 1_048_576

    logger.info(f"💾 Disk: {free_mb:.0f} MB free, need ~{total_needed:.0f} MB")
    if free_mb < total_needed:
        logger.error(f"❌ Not enough disk space! Need {total_needed:.0f} MB, only {free_mb:.0f} MB free")
        return

    # Create engine and start download
    engine = DownloadEngine(
        max_concurrent=args.concurrent,
        cache_dir="/var/cache/tank_os/preload",
    )
    engine.on_progress(progress_printer(logger))

    logger.info(f"\n{'='*60}")
    logger.info(f"  📥 Starting download of {len(items)} items ({sum(i.size_mb for i in items):.0f} MB)")
    logger.info(f"  Concurrent downloads: {args.concurrent}")
    logger.info(f"{'='*60}\n")

    start_time = time.time()
    results = engine.download_all(items, max_concurrent=args.concurrent)
    elapsed = time.time() - start_time

    # Summary
    logger.info(f"\n{'='*60}")
    logger.info(f"  📊 Download Complete!")
    logger.info(f"{'='*60}")
    
    completed = sum(1 for p in results.values() if p.status == DownloadStatus.COMPLETED)
    failed = sum(1 for p in results.values() if p.status == DownloadStatus.FAILED)
    skipped = sum(1 for p in results.values() if p.status == DownloadStatus.SKIPPED)
    total_mb = engine.total_bytes_downloaded / 1_048_576
    
    logger.info(f"  ✅ Completed: {completed}")
    logger.info(f"  ❌ Failed:    {failed}")
    logger.info(f"  ⏭ Skipped:   {skipped}")
    logger.info(f"  📦 Downloaded: {total_mb:.0f} MB")
    logger.info(f"  ⏱ Time:      {elapsed:.0f}s ({elapsed/60:.1f} min)")
    
    if failed > 0:
        logger.info(f"\n  ❌ Failed items:")
        for item_id, p in results.items():
            if p.status == DownloadStatus.FAILED:
                logger.info(f"     ✗ {item_id}: {p.error}")
    
    logger.info(f"\n{'='*60}\n")
    logger.info("💡 Next steps:")
    logger.info("   Run the full daily cycle:   python3 -c \"from tank_os.ai.self_coding import SelfCodingSystem; SelfCodingSystem().run_daily_cycle()\"")
    logger.info("   Check preload status:       python3 -c \"from tank_os.core.preload_manager import PreloadManager; PreloadManager().print_report()\"")
    logger.info("")


def main():
    parser = argparse.ArgumentParser(
        description="TankOS — Download Everything",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                        # Download all items
  %(prog)s --llm-only             # Only LLM models
  %(prog)s --category llm         # Only a specific category
  %(prog)s --check                # Check what needs downloading
  %(prog)s --concurrent 2         # Limit to 2 concurrent downloads
        """,
    )
    parser.add_argument("--llm-only", action="store_true", help="Download only LLM models")
    parser.add_argument("--category", type=str, help="Download only a specific category")
    parser.add_argument("--check", action="store_true", help="Just check what's needed, don't download")
    parser.add_argument("--concurrent", type=int, default=3, help="Max concurrent downloads (default: 3)")
    parser.add_argument("--status", action="store_true", help="Check current download status")
    args = parser.parse_args()

    logger = setup_logging()

    if args.status:
        engine = DownloadEngine(cache_dir="/var/cache/tank_os/preload")
        progress = engine.all_progress()
        if progress:
            logger.info("Current download status:")
            for item_id, p in progress.items():
                logger.info(f"  {item_id}: {p.status.value} ({p.percent:.0f}%)")
        else:
            logger.info("No active downloads")
        return

    if args.check:
        print_manifest_summary(logger)
        print_download_plan(logger)
        return

    run_download(args, logger)


if __name__ == "__main__":
    main()
