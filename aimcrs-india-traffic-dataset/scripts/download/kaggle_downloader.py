#!/usr/bin/env python3
# ============================================
# Step 4 — Kaggle Datasets Downloader
# ============================================
# File: scripts/download/kaggle_downloader.py
# What: Downloads Indian traffic datasets from Kaggle
# How to run: python scripts/download/kaggle_downloader.py
#
# ⚠️ REQUIRES: Free Kaggle account + API key
#
# HOW TO SET UP KAGGLE (one-time):
#   1. Go to kaggle.com — create a free account
#   2. Click your profile picture (top right) → Settings
#   3. Scroll down to "API" section
#   4. Click "Create New Token"
#   5. This downloads a file called kaggle.json
#   6. Open kaggle.json — it has your username and key
#   7. Add them to your .env file:
#      KAGGLE_USERNAME=your_username
#      KAGGLE_KEY=your_key
# ============================================

import os
import sys
import json
import time
import subprocess
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

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

# Load .env
load_dotenv(PROJECT_ROOT / ".env")

# ----- PATHS -----
RAW_KAGGLE_DIR = PROJECT_ROOT / "raw" / "kaggle"
LOGS_DIR = PROJECT_ROOT / "logs"
METADATA_FILE = RAW_KAGGLE_DIR / "metadata.json"

# ----- KAGGLE CREDENTIALS -----
KAGGLE_USERNAME = os.getenv("KAGGLE_USERNAME", "")
KAGGLE_KEY = os.getenv("KAGGLE_KEY", "")

# ----- SETTINGS -----
DELAY_BETWEEN_DOWNLOADS = 5

# ----- SEARCH TERMS AND RESULT LIMITS -----
# Each search term with how many results to download.
KAGGLE_SEARCHES = [
    {"term": "Indian traffic dataset", "max_results": 10},
    {"term": "India road accident", "max_results": 5},
    {"term": "vehicle detection India", "max_results": 5},
    {"term": "ambulance detection", "max_results": 10},
    {"term": "emergency vehicle detection", "max_results": 10},
    {"term": "traffic signal India", "max_results": 5},
    {"term": "Indian road segmentation", "max_results": 5},
]

# ----- KNOWN SPECIFIC DATASETS -----
# These are specific Kaggle datasets we know exist and want.
KNOWN_DATASETS = [
    "avikumart/indian-road-accident-data-2017-2022",
    "dataenthusiast99/indian-vehicle-type-classification",
    "meowmeowmeowmeowmeow/gtsrb-german-traffic-sign",
]


def setup_logging():
    """Set up logging."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    logger.add(
        str(LOGS_DIR / "kaggle_downloads.log"),
        rotation="10 MB",
        retention="30 days",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    )
    logger.info("=" * 60)
    logger.info("Kaggle Downloader Started")
    logger.info("=" * 60)


def load_metadata():
    if METADATA_FILE.exists():
        with open(METADATA_FILE, "r") as f:
            return json.load(f)
    return {"datasets": [], "downloaded_refs": []}


def save_metadata(metadata):
    METADATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(METADATA_FILE, "w") as f:
        json.dump(metadata, f, indent=2, default=str)


def check_kaggle_setup():
    """
    Check if Kaggle is properly configured.
    Returns True if ready, False if not.
    """
    if not KAGGLE_USERNAME or KAGGLE_USERNAME == "your_kaggle_username_here":
        print("\n  ⚠️  KAGGLE NOT SET UP")
        print("  You need a free Kaggle account to use this script.")
        print()
        print("  How to set up (5 minutes):")
        print("  1. Go to https://kaggle.com — create free account")
        print("  2. Click profile picture → Settings")
        print("  3. Scroll to 'API' → Click 'Create New Token'")
        print("  4. Open the downloaded kaggle.json file")
        print("  5. Edit your .env file and add:")
        print("     KAGGLE_USERNAME=your_actual_username")
        print("     KAGGLE_KEY=your_actual_api_key")
        print()
        return False

    # Set environment variables for kaggle CLI
    os.environ["KAGGLE_USERNAME"] = KAGGLE_USERNAME
    os.environ["KAGGLE_KEY"] = KAGGLE_KEY

    # Test if kaggle CLI works
    try:
        import kaggle  # noqa: F401
        return True
    except ImportError:
        print("  ⚠️  kaggle package not installed. Fix: pip install kaggle")
        return False
    except Exception as e:
        logger.error(f"Kaggle setup check failed: {e}")
        print(f"  ⚠️  Kaggle error: {e}")
        return False


def search_kaggle(search_term, max_results=5):
    """
    Search Kaggle for datasets matching a term.
    Returns a list of dataset references (owner/dataset-name).
    """
    try:
        from kaggle.api.kaggle_api_extended import KaggleApi

        api = KaggleApi()
        api.authenticate()

        results = api.dataset_list(search=search_term, page_size=max_results)

        dataset_refs = []
        for dataset in results:
            ref = str(dataset)
            dataset_refs.append(ref)

        return dataset_refs

    except Exception as e:
        logger.error(f"Kaggle search failed for '{search_term}': {e}")
        return []


def download_kaggle_dataset(dataset_ref, metadata):
    """
    Download one Kaggle dataset.

    dataset_ref is like "username/dataset-name".
    Example: "avikumart/indian-road-accident-data-2017-2022"
    """
    if dataset_ref in metadata.get("downloaded_refs", []):
        logger.info(f"SKIP (duplicate): {dataset_ref}")
        return False

    # Create folder for this dataset
    safe_name = dataset_ref.replace("/", "_")
    save_dir = RAW_KAGGLE_DIR / safe_name
    save_dir.mkdir(parents=True, exist_ok=True)

    try:
        from kaggle.api.kaggle_api_extended import KaggleApi

        api = KaggleApi()
        api.authenticate()

        logger.info(f"DOWNLOADING: {dataset_ref}")
        print(f"    Downloading: {dataset_ref}...")

        api.dataset_download_files(
            dataset_ref,
            path=str(save_dir),
            unzip=True,
        )

        # Calculate total size
        total_size = sum(
            f.stat().st_size for f in save_dir.rglob("*") if f.is_file()
        )
        size_mb = total_size / (1024 * 1024)

        logger.info(f"SUCCESS: {dataset_ref} ({size_mb:.1f} MB)")
        print(f"    SUCCESS: {dataset_ref} ({size_mb:.1f} MB)")

        metadata["datasets"].append({
            "ref": dataset_ref,
            "source": "kaggle",
            "save_directory": str(save_dir),
            "size_mb": round(size_mb, 1),
            "downloaded_at": datetime.now().isoformat(),
        })
        metadata["downloaded_refs"].append(dataset_ref)
        save_metadata(metadata)

        return True

    except Exception as e:
        logger.error(f"FAILED: {dataset_ref} — {e}")
        print(f"    FAILED: {dataset_ref} — {e}")
        return False


def print_summary(metadata):
    """Print summary."""
    datasets = metadata.get("datasets", [])
    total = len(datasets)
    total_size = sum(d.get("size_mb", 0) for d in datasets)

    print("\n" + "=" * 50)
    print("  AIMCRS Kaggle Download Summary")
    print("=" * 50)
    print(f"  Total datasets downloaded: {total}")
    print(f"  Total size: {total_size:.1f} MB")
    print()
    for d in datasets:
        print(f"    {d['ref']} ({d.get('size_mb', '?')} MB)")
    print("=" * 50)


def main():
    """
    Main function — searches Kaggle and downloads datasets.

    Order:
    1. Check Kaggle credentials
    2. Download known specific datasets
    3. Search and download for each search term
    """
    print("=" * 50)
    print("  AIMCRS Kaggle Dataset Downloader")
    print("  Indian traffic & vehicle datasets from Kaggle")
    print("=" * 50)

    setup_logging()
    RAW_KAGGLE_DIR.mkdir(parents=True, exist_ok=True)

    # Check setup
    if not check_kaggle_setup():
        logger.warning("Kaggle not configured — exiting")
        return

    metadata = load_metadata()
    already_have = len(metadata.get("datasets", []))
    print(f"Already have {already_have} datasets from previous runs")

    total = 0

    # Step 1: Download known specific datasets
    print("\n--- Downloading known datasets ---")
    for ref in KNOWN_DATASETS:
        if download_kaggle_dataset(ref, metadata):
            total += 1
        time.sleep(DELAY_BETWEEN_DOWNLOADS)

    # Step 2: Search and download
    print("\n--- Searching Kaggle ---")
    for search_config in KAGGLE_SEARCHES:
        term = search_config["term"]
        max_results = search_config["max_results"]

        print(f"\n  Searching: '{term}' (up to {max_results} results)")
        refs = search_kaggle(term, max_results)

        if not refs:
            print(f"    No results found")
            continue

        print(f"    Found {len(refs)} datasets")

        for ref in refs:
            if download_kaggle_dataset(ref, metadata):
                total += 1
            time.sleep(DELAY_BETWEEN_DOWNLOADS)

    print_summary(metadata)

    logger.info("Kaggle Downloader Finished")
    print("\nDone! Check logs/kaggle_downloads.log for details.")


if __name__ == "__main__":
    main()
