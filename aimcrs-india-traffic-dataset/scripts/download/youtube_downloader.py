#!/usr/bin/env python3
# ============================================
# FILE 2 OF 2 — YouTube Traffic Video Downloader
# ============================================
# File: scripts/download/youtube_downloader.py
# What: Downloads Indian traffic footage from YouTube
# How to run: python scripts/download/youtube_downloader.py
# ============================================

import os
import sys
import json
import time
import hashlib
from pathlib import Path
from datetime import datetime

# Add project root to path so imports work
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# We import yt_dlp for downloading videos.
# Install it with: pip install yt-dlp
try:
    import yt_dlp
except ImportError:
    print("ERROR: yt-dlp is not installed.")
    print("Fix: Run this command:")
    print("  pip install yt-dlp")
    sys.exit(1)

# We import loguru for nice logging.
# Install it with: pip install loguru
try:
    from loguru import logger
except ImportError:
    print("ERROR: loguru is not installed.")
    print("Fix: Run this command:")
    print("  pip install loguru")
    sys.exit(1)

# Import our configuration (search terms, city keywords, etc.)
from scripts.download.youtube_config import (
    SEARCH_TERMS,
    TARGET_CHANNELS,
    CITY_KEYWORDS,
    MAX_VIDEOS_PER_SEARCH,
    MAX_VIDEO_LENGTH_SECONDS,
    MIN_VIDEO_LENGTH_SECONDS,
    DELAY_BETWEEN_DOWNLOADS,
    MAX_TOTAL_DOWNLOADS,
    VIDEO_FORMAT,
    LICENSE_CREATIVE_COMMONS,
    LICENSE_STANDARD,
    LICENSE_UNKNOWN,
)

# ----- PATHS -----
RAW_YOUTUBE_DIR = PROJECT_ROOT / "raw" / "youtube"
LOGS_DIR = PROJECT_ROOT / "logs"
METADATA_FILE = PROJECT_ROOT / "raw" / "youtube" / "metadata.json"
DOWNLOAD_LOG = LOGS_DIR / "youtube_downloads.log"


def setup_logging():
    """Set up logging so we can track everything that happens."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    logger.add(
        str(DOWNLOAD_LOG),
        rotation="10 MB",
        retention="30 days",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    )
    logger.info("=" * 60)
    logger.info("YouTube Downloader Started")
    logger.info("=" * 60)


def load_metadata():
    """
    Load the metadata file.
    Metadata = a record of every video we have downloaded.
    This helps us skip videos we already have (no duplicates).
    """
    if METADATA_FILE.exists():
        with open(METADATA_FILE, "r") as f:
            return json.load(f)
    return {"videos": [], "downloaded_urls": []}


def save_metadata(metadata):
    """Save metadata to file after each download."""
    METADATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(METADATA_FILE, "w") as f:
        json.dump(metadata, f, indent=2, default=str)


def detect_city(title, description):
    """
    Figure out which Indian city a video is from.
    We look for city names and landmark names in the
    video title and description.

    Returns the city name, or "Other" if we can't tell.
    """
    text = f"{title} {description}".lower()
    for city, keywords in CITY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text:
                return city
    return "Other"


def detect_license(info_dict):
    """
    Check what license a YouTube video has.
    Creative Commons = safe for training.
    Standard YouTube = research use only.
    """
    license_str = info_dict.get("license", "")
    if license_str and "creative commons" in license_str.lower():
        return LICENSE_CREATIVE_COMMONS
    # YouTube API returns "Standard YouTube License" for most videos
    return LICENSE_STANDARD


def is_already_downloaded(video_url, metadata):
    """Check if we already downloaded this video (skip duplicates)."""
    return video_url in metadata.get("downloaded_urls", [])


def is_valid_duration(duration):
    """
    Check if video length is within our limits.
    Too short = probably not useful.
    Too long = uses too much disk space.
    """
    if duration is None:
        return True  # Allow if duration is unknown
    return MIN_VIDEO_LENGTH_SECONDS <= duration <= MAX_VIDEO_LENGTH_SECONDS


def get_city_folder(city):
    """
    Get (and create) the folder for a specific city.
    Videos are sorted by city automatically.
    """
    city_dir = RAW_YOUTUBE_DIR / city
    city_dir.mkdir(parents=True, exist_ok=True)
    return city_dir


def build_video_metadata(info_dict, city, license_type):
    """
    Build a metadata record for one video.
    This tracks where the video came from and what it contains.
    """
    return {
        "video_id": info_dict.get("id", "unknown"),
        "title": info_dict.get("title", "unknown"),
        "url": info_dict.get("webpage_url", ""),
        "channel": info_dict.get("channel", info_dict.get("uploader", "unknown")),
        "upload_date": info_dict.get("upload_date", "unknown"),
        "duration_seconds": info_dict.get("duration", 0),
        "description": (info_dict.get("description", "") or "")[:500],
        "city": city,
        "license_type": license_type,
        "copyright_safe": license_type == LICENSE_CREATIVE_COMMONS,
        "downloaded_at": datetime.now().isoformat(),
        "file_format": info_dict.get("ext", "mp4"),
        "resolution": info_dict.get("resolution", "unknown"),
        "source": "youtube",
    }


def download_video(video_url, output_dir, metadata):
    """
    Download one video from YouTube.

    Steps:
    1. Check if already downloaded (skip if yes)
    2. Get video info (title, length, etc.)
    3. Check duration is within limits
    4. Detect which city it's from
    5. Download to the right city folder
    6. Save metadata
    """
    # Step 1: Skip duplicates
    if is_already_downloaded(video_url, metadata):
        logger.info(f"SKIP (duplicate): {video_url}")
        return False

    # Step 2: Get video info without downloading
    info_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
    }

    try:
        with yt_dlp.YoutubeDL(info_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
    except Exception as e:
        logger.error(f"FAILED to get info: {video_url} — {e}")
        return False

    if info is None:
        logger.error(f"FAILED: No info returned for {video_url}")
        return False

    title = info.get("title", "unknown")
    duration = info.get("duration")

    # Step 3: Check duration
    if not is_valid_duration(duration):
        logger.info(
            f"SKIP (duration {duration}s out of range): {title}"
        )
        return False

    # Step 4: Detect city
    description = info.get("description", "") or ""
    city = detect_city(title, description)
    city_dir = get_city_folder(city)

    # Step 5: Detect license
    license_type = detect_license(info)
    if license_type == LICENSE_CREATIVE_COMMONS:
        logger.info(f"LICENSE: Creative Commons — safe for training")
    else:
        logger.info(f"LICENSE: Standard YouTube — research use only")

    # Step 6: Download the video
    download_opts = {
        "format": VIDEO_FORMAT,
        "outtmpl": str(city_dir / "%(id)s_%(title).50s.%(ext)s"),
        "quiet": False,
        "no_warnings": False,
        "restrictfilenames": True,  # Safe filenames (no special chars)
        "noplaylist": True,         # Download single video, not playlist
        "writesubtitles": False,
        "writeautomaticsub": False,
    }

    try:
        logger.info(f"DOWNLOADING: {title} → {city}/")
        with yt_dlp.YoutubeDL(download_opts) as ydl:
            ydl.download([video_url])
    except Exception as e:
        logger.error(f"DOWNLOAD FAILED: {title} — {e}")
        return False

    # Step 7: Save metadata
    video_meta = build_video_metadata(info, city, license_type)
    metadata["videos"].append(video_meta)
    metadata["downloaded_urls"].append(video_url)
    save_metadata(metadata)

    logger.info(f"SUCCESS: {title} → {city}/ (License: {license_type})")
    return True


def search_and_download(search_term, metadata, total_downloaded):
    """
    Search YouTube for a term and download matching videos.

    Returns how many new videos were downloaded.
    """
    logger.info(f"SEARCHING: '{search_term}'")
    count = 0

    search_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,       # Just get URLs, don't download yet
        "default_search": "ytsearch",
    }

    search_query = f"ytsearch{MAX_VIDEOS_PER_SEARCH}:{search_term}"

    try:
        with yt_dlp.YoutubeDL(search_opts) as ydl:
            results = ydl.extract_info(search_query, download=False)
    except Exception as e:
        logger.error(f"SEARCH FAILED: '{search_term}' — {e}")
        return 0

    if not results or "entries" not in results:
        logger.warning(f"NO RESULTS: '{search_term}'")
        return 0

    entries = results.get("entries", [])
    logger.info(f"FOUND {len(entries)} results for '{search_term}'")

    for entry in entries:
        if entry is None:
            continue

        # Check if we've hit the total limit
        if (total_downloaded + count) >= MAX_TOTAL_DOWNLOADS:
            logger.warning("HIT MAX TOTAL DOWNLOADS LIMIT — stopping")
            return count

        video_url = entry.get("url") or entry.get("webpage_url")
        if not video_url:
            video_id = entry.get("id")
            if video_id:
                video_url = f"https://www.youtube.com/watch?v={video_id}"
            else:
                continue

        success = download_video(video_url, RAW_YOUTUBE_DIR, metadata)
        if success:
            count += 1

        # Be polite — wait between downloads
        logger.info(f"Waiting {DELAY_BETWEEN_DOWNLOADS}s before next...")
        time.sleep(DELAY_BETWEEN_DOWNLOADS)

    return count


def download_channel_videos(channel_name, metadata, total_downloaded):
    """
    Download recent videos from a specific YouTube channel.
    """
    logger.info(f"CHANNEL: Downloading from @{channel_name}")

    channel_url = f"https://www.youtube.com/@{channel_name}/videos"
    count = 0

    channel_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "playlistend": MAX_VIDEOS_PER_SEARCH,
    }

    try:
        with yt_dlp.YoutubeDL(channel_opts) as ydl:
            results = ydl.extract_info(channel_url, download=False)
    except Exception as e:
        logger.error(f"CHANNEL FAILED: @{channel_name} — {e}")
        return 0

    if not results or "entries" not in results:
        logger.warning(f"NO VIDEOS FOUND: @{channel_name}")
        return 0

    entries = list(results.get("entries", []))
    logger.info(f"FOUND {len(entries)} videos from @{channel_name}")

    for entry in entries:
        if entry is None:
            continue

        if (total_downloaded + count) >= MAX_TOTAL_DOWNLOADS:
            logger.warning("HIT MAX TOTAL DOWNLOADS LIMIT — stopping")
            return count

        video_url = entry.get("url") or entry.get("webpage_url")
        if not video_url:
            video_id = entry.get("id")
            if video_id:
                video_url = f"https://www.youtube.com/watch?v={video_id}"
            else:
                continue

        success = download_video(video_url, RAW_YOUTUBE_DIR, metadata)
        if success:
            count += 1

        time.sleep(DELAY_BETWEEN_DOWNLOADS)

    return count


def print_summary(metadata):
    """Print a nice summary of what we have downloaded."""
    videos = metadata.get("videos", [])
    total = len(videos)

    # Count by city
    city_counts = {}
    for v in videos:
        city = v.get("city", "Other")
        city_counts[city] = city_counts.get(city, 0) + 1

    # Count by license
    cc_count = sum(1 for v in videos if v.get("copyright_safe", False))
    standard_count = total - cc_count

    print("\n" + "=" * 50)
    print("  AIMCRS YouTube Download Summary")
    print("=" * 50)
    print(f"  Total videos downloaded: {total}")
    print(f"  Creative Commons (safe): {cc_count}")
    print(f"  Standard YouTube (research only): {standard_count}")
    print()
    print("  Videos by city:")
    for city, count in sorted(city_counts.items()):
        print(f"    {city}: {count}")
    print("=" * 50)
    print()

    logger.info(f"SUMMARY: {total} videos downloaded across {len(city_counts)} cities")


def main():
    """
    Main function — runs the full YouTube download pipeline.

    Order of operations:
    1. Set up logging
    2. Load existing metadata (so we skip duplicates)
    3. Download from target channels first
    4. Then search each search term
    5. Print summary
    """
    print("=" * 50)
    print("  AIMCRS YouTube Traffic Video Downloader")
    print("  Collecting Indian traffic footage for AI training")
    print("=" * 50)
    print()

    # Step 1: Set up
    setup_logging()
    RAW_YOUTUBE_DIR.mkdir(parents=True, exist_ok=True)

    # Step 2: Load existing metadata
    metadata = load_metadata()
    already_have = len(metadata.get("videos", []))
    logger.info(f"Already have {already_have} videos from previous runs")
    print(f"Already have {already_have} videos from previous runs")

    total_downloaded = already_have

    # Step 3: Download from target channels
    print("\n--- Downloading from target channels ---")
    for channel in TARGET_CHANNELS:
        count = download_channel_videos(channel, metadata, total_downloaded)
        total_downloaded += count
        print(f"  @{channel}: downloaded {count} new videos")

    # Step 4: Search and download
    print("\n--- Searching and downloading ---")
    for search_term in SEARCH_TERMS:
        if total_downloaded >= MAX_TOTAL_DOWNLOADS:
            print(f"\nReached maximum of {MAX_TOTAL_DOWNLOADS} videos. Stopping.")
            break

        count = search_and_download(search_term, metadata, total_downloaded)
        total_downloaded += count
        print(f"  '{search_term}': downloaded {count} new videos")

    # Step 5: Summary
    print_summary(metadata)

    logger.info("YouTube Downloader Finished")
    print("Done! Check logs/youtube_downloads.log for full details.")


if __name__ == "__main__":
    main()
