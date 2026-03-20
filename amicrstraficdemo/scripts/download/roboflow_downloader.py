#!/usr/bin/env python3
# ============================================
# Step 5 — Roboflow Universe Downloader
# ============================================
# File: scripts/download/roboflow_downloader.py
# What: Downloads labelled image datasets from Roboflow
# How to run: python scripts/download/roboflow_downloader.py
#
# ⚠️ Some datasets need a free Roboflow account.
#
# Roboflow Universe is the largest open computer vision
# dataset repository. We search for Indian traffic and
# vehicle detection datasets.
# ============================================

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import requests
except ImportError:
    print("ERROR: requests is not installed. Fix: pip install requests")
    sys.exit(1)

try:
    from loguru import logger
except ImportError:
    print("ERROR: loguru is not installed. Fix: pip install loguru")
    sys.exit(1)

try:
    from dotenv import load_dotenv
except ImportError:
    print("ERROR: python-dotenv is not installed. Fix: pip install python-dotenv")
    sys.exit(1)

load_dotenv(PROJECT_ROOT / ".env")

# ----- PATHS -----
RAW_KAGGLE_DIR = PROJECT_ROOT / "raw" / "kaggle"  # Roboflow goes here too
ROBOFLOW_DIR = PROJECT_ROOT / "raw" / "kaggle" / "roboflow"
LOGS_DIR = PROJECT_ROOT / "logs"
METADATA_FILE = ROBOFLOW_DIR / "metadata.json"

# ----- API KEY -----
ROBOFLOW_API_KEY = os.getenv("ROBOFLOW_API_KEY", "")

# ----- SETTINGS -----
DELAY_BETWEEN_DOWNLOADS = 3

# ----- SEARCH TERMS -----
# What we search for on Roboflow Universe.
ROBOFLOW_SEARCHES = [
    "ambulance detection",
    "emergency vehicle",
    "Indian traffic",
    "vehicle detection India",
    "traffic signal",
    "two wheeler detection",
    "auto rickshaw detection",
    "pedestrian India",
    "motorcycle detection",
    "truck detection",
]

# Download formats — YOLO is most compatible for training
DOWNLOAD_FORMAT_PRIMARY = "yolov8"   # YOLO format
DOWNLOAD_FORMAT_BACKUP = "coco"      # COCO format as backup


def setup_logging():
    """Set up logging."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    logger.add(
        str(LOGS_DIR / "roboflow_downloads.log"),
        rotation="10 MB",
        retention="30 days",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    )
    logger.info("=" * 60)
    logger.info("Roboflow Downloader Started")
    logger.info("=" * 60)


def load_metadata():
    if METADATA_FILE.exists():
        with open(METADATA_FILE, "r") as f:
            return json.load(f)
    return {"datasets": [], "downloaded_ids": []}


def save_metadata(metadata):
    METADATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(METADATA_FILE, "w") as f:
        json.dump(metadata, f, indent=2, default=str)


def check_roboflow_setup():
    """Check if Roboflow API key is configured."""
    if not ROBOFLOW_API_KEY or ROBOFLOW_API_KEY == "your_roboflow_api_key_here":
        print("\n  ⚠️  ROBOFLOW API KEY NOT SET")
        print("  Some datasets need a free Roboflow account.")
        print()
        print("  How to set up (3 minutes):")
        print("  1. Go to https://roboflow.com — create free account")
        print("  2. Go to Settings → API Keys")
        print("  3. Copy your API key")
        print("  4. Edit .env file and add:")
        print("     ROBOFLOW_API_KEY=your_actual_key")
        print()
        print("  Continuing without API key — will search Universe only...")
        return False
    return True


def search_roboflow_universe(search_term):
    """
    Search Roboflow Universe for datasets.
    Uses the public universe search API.
    Returns list of dataset info dicts.
    """
    logger.info(f"Searching Roboflow Universe: '{search_term}'")

    # Roboflow Universe public search
    url = "https://universe.roboflow.com/api/search"
    params = {"q": search_term, "limit": 10}

    try:
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            return results
        else:
            logger.warning(
                f"Roboflow search returned {response.status_code}"
            )
            return []
    except Exception as e:
        logger.error(f"Roboflow search failed: {e}")
        return []


def download_roboflow_dataset(workspace, project, version, save_dir, fmt):
    """
    Download a dataset from Roboflow using the API.
    Requires ROBOFLOW_API_KEY to be set.
    """
    if not ROBOFLOW_API_KEY or ROBOFLOW_API_KEY == "your_roboflow_api_key_here":
        logger.warning("Cannot download — no API key")
        return False

    try:
        from roboflow import Roboflow

        rf = Roboflow(api_key=ROBOFLOW_API_KEY)
        proj = rf.workspace(workspace).project(project)
        ds = proj.version(version)
        ds.download(fmt, location=str(save_dir))

        logger.info(f"SUCCESS: Downloaded {workspace}/{project} v{version}")
        return True

    except ImportError:
        logger.error("roboflow package not installed. Fix: pip install roboflow")
        print("    ⚠️ pip install roboflow to enable downloads")
        return False
    except Exception as e:
        logger.error(f"Download failed: {workspace}/{project} — {e}")
        return False


def process_search_results(search_term, results, metadata):
    """
    Process search results from Roboflow Universe.
    Download each dataset in YOLO format.
    """
    count = 0

    for result in results:
        # Extract dataset info
        dataset_id = result.get("id", "")
        name = result.get("name", "unknown")
        workspace = result.get("workspace", "")
        project = result.get("project", "")
        universe_url = result.get("url", "")
        image_count = result.get("images", 0)

        if not workspace or not project:
            continue

        # Skip if already downloaded
        unique_id = f"{workspace}/{project}"
        if unique_id in metadata.get("downloaded_ids", []):
            logger.info(f"SKIP (duplicate): {unique_id}")
            continue

        print(f"    Found: {name} ({image_count} images)")

        # Try to find the latest version
        version = 1  # Default to version 1

        save_dir = ROBOFLOW_DIR / search_term.replace(" ", "_") / project
        save_dir.mkdir(parents=True, exist_ok=True)

        # Try YOLO format first
        success = download_roboflow_dataset(
            workspace, project, version, save_dir, DOWNLOAD_FORMAT_PRIMARY
        )

        if success:
            metadata["datasets"].append({
                "name": name,
                "workspace": workspace,
                "project": project,
                "version": version,
                "format": DOWNLOAD_FORMAT_PRIMARY,
                "image_count": image_count,
                "search_term": search_term,
                "save_directory": str(save_dir),
                "source": "roboflow_universe",
                "downloaded_at": datetime.now().isoformat(),
            })
            metadata["downloaded_ids"].append(unique_id)
            save_metadata(metadata)
            count += 1
        else:
            # Log for manual download
            metadata["datasets"].append({
                "name": name,
                "workspace": workspace,
                "project": project,
                "url": universe_url,
                "image_count": image_count,
                "search_term": search_term,
                "status": "manual_download_needed",
                "source": "roboflow_universe",
                "logged_at": datetime.now().isoformat(),
            })
            save_metadata(metadata)

        time.sleep(DELAY_BETWEEN_DOWNLOADS)

    return count


def print_summary(metadata):
    """Print summary."""
    datasets = metadata.get("datasets", [])
    downloaded = [d for d in datasets if d.get("format")]
    manual = [d for d in datasets if d.get("status") == "manual_download_needed"]

    total_images = sum(d.get("image_count", 0) for d in downloaded)

    print("\n" + "=" * 50)
    print("  AIMCRS Roboflow Download Summary")
    print("=" * 50)
    print(f"  Datasets downloaded: {len(downloaded)}")
    print(f"  Total images: {total_images}")
    print(f"  Need manual download: {len(manual)}")
    print()

    if downloaded:
        print("  Downloaded datasets:")
        for d in downloaded:
            print(f"    {d['name']} ({d.get('image_count', '?')} images)")

    if manual:
        print("\n  Datasets needing manual download:")
        for d in manual:
            print(f"    {d['name']}: {d.get('url', 'search on universe.roboflow.com')}")

    print("=" * 50)


def main():
    """Main function."""
    print("=" * 50)
    print("  AIMCRS Roboflow Universe Downloader")
    print("  Labelled vehicle & traffic image datasets")
    print("=" * 50)

    setup_logging()
    ROBOFLOW_DIR.mkdir(parents=True, exist_ok=True)

    has_api_key = check_roboflow_setup()

    metadata = load_metadata()
    already_have = len(metadata.get("datasets", []))
    print(f"Already have {already_have} dataset records from previous runs")

    total = 0

    for search_term in ROBOFLOW_SEARCHES:
        print(f"\n  Searching: '{search_term}'")
        results = search_roboflow_universe(search_term)

        if not results:
            print(f"    No results found")
            continue

        print(f"    Found {len(results)} datasets")

        if has_api_key:
            count = process_search_results(search_term, results, metadata)
            total += count
        else:
            # Just log what we found for later manual download
            for r in results:
                name = r.get("name", "unknown")
                url = r.get("url", "")
                images = r.get("images", 0)
                print(f"    - {name} ({images} images)")
                if url:
                    print(f"      URL: {url}")

        time.sleep(DELAY_BETWEEN_DOWNLOADS)

    print_summary(metadata)

    logger.info("Roboflow Downloader Finished")
    print("\nDone! Check logs/roboflow_downloads.log for details.")


if __name__ == "__main__":
    main()
