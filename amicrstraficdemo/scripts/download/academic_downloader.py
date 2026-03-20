#!/usr/bin/env python3
# ============================================
# Step 3 — Academic Datasets Downloader
# ============================================
# File: scripts/download/academic_downloader.py
# What: Downloads free traffic datasets from universities
# How to run: python scripts/download/academic_downloader.py
#
# Datasets:
#   1. IDD — India Driving Dataset (IIIT Hyderabad)
#   2. UA-DETRAC — Vehicle detection benchmark
#   3. IIT Bombay Traffic Dataset
#   4. VIRAT Dataset
#   5. IIIT Delhi Traffic Dataset
# ============================================

import os
import sys
import json
import time
import zipfile
import tarfile
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

# ----- PATHS -----
RAW_ACADEMIC_DIR = PROJECT_ROOT / "raw" / "academic"
LOGS_DIR = PROJECT_ROOT / "logs"
METADATA_FILE = RAW_ACADEMIC_DIR / "metadata.json"

# ----- SETTINGS -----
DELAY_BETWEEN_REQUESTS = 3
REQUEST_TIMEOUT = 60  # Academic servers can be slow


# ----- DATASET DEFINITIONS -----
# Each dataset we want to download.
# Some require registration — we flag those clearly.

ACADEMIC_DATASETS = [
    {
        "name": "IDD_India_Driving_Dataset",
        "source": "IIIT Hyderabad",
        "url": "https://idd.insaan.iiit.ac.in",
        "description": (
            "India Driving Dataset — Built specifically for Indian roads. "
            "Contains semantic segmentation (pixel-level labels) of Indian "
            "road scenes. Includes: cars, bikes, autos, trucks, buses, "
            "pedestrians, animals, road markings."
        ),
        "requires_registration": True,
        "registration_url": "https://idd.insaan.iiit.ac.in/accounts/login",
        "instructions": (
            "1. Go to https://idd.insaan.iiit.ac.in\n"
            "2. Click 'Register' and create a free account\n"
            "3. Once approved, download IDD-Detection and IDD-Segmentation\n"
            "4. Save files to: raw/academic/idd/"
        ),
        "auto_download": False,
    },
    {
        "name": "UA_DETRAC",
        "source": "SMU Singapore",
        "url": "https://detrac-db.rit.albany.edu",
        "description": (
            "UA-DETRAC — A large vehicle detection and tracking benchmark. "
            "Contains 100+ hours of video at 24 traffic locations. "
            "10+ vehicle types labelled. Free for research."
        ),
        "requires_registration": False,
        "auto_download": True,
        "download_urls": [
            {
                "url": "https://detrac-db.rit.albany.edu/Data/DETRAC-train-data.zip",
                "filename": "DETRAC-train-data.zip",
                "description": "UA-DETRAC Training Images",
            },
            {
                "url": "https://detrac-db.rit.albany.edu/Data/DETRAC-test-data.zip",
                "filename": "DETRAC-test-data.zip",
                "description": "UA-DETRAC Test Images",
            },
            {
                "url": "https://detrac-db.rit.albany.edu/Data/DETRAC-Train-Annotations-XML-v3.zip",
                "filename": "DETRAC-Train-Annotations.zip",
                "description": "UA-DETRAC Training Annotations (labels)",
            },
        ],
    },
    {
        "name": "IIT_Bombay_Traffic",
        "source": "IIT Bombay",
        "url": "https://www.cse.iitb.ac.in",
        "description": (
            "IIT Bombay Traffic Dataset — Specifically built for Indian "
            "chaotic traffic. Includes Mumbai traffic videos, acoustic "
            "sensing data, congestion detection."
        ),
        "requires_registration": True,
        "instructions": (
            "1. Search: 'IIT Bombay traffic dataset' on Google\n"
            "2. Or visit the CSE department research page\n"
            "3. Contact the research group if dataset is not public\n"
            "4. Save files to: raw/academic/iit_bombay/"
        ),
        "auto_download": False,
    },
    {
        "name": "VIRAT_Dataset",
        "source": "VIRAT Project",
        "url": "https://viratdata.org",
        "description": (
            "VIRAT Dataset — Vehicle and pedestrian detection in "
            "surveillance video. Contains real-world surveillance footage "
            "with labelled vehicles and people."
        ),
        "requires_registration": True,
        "registration_url": "https://viratdata.org",
        "instructions": (
            "1. Go to https://viratdata.org\n"
            "2. Register for access (free for research)\n"
            "3. Download available video clips and annotations\n"
            "4. Save files to: raw/academic/virat/"
        ),
        "auto_download": False,
    },
    {
        "name": "IIIT_Delhi_Traffic",
        "source": "IIIT Delhi",
        "url": "https://www.iiitd.ac.in",
        "description": (
            "IIIT Delhi Traffic Dataset — Search their research portal "
            "for available traffic and vehicle datasets."
        ),
        "requires_registration": True,
        "instructions": (
            "1. Search: 'IIIT Delhi traffic dataset'\n"
            "2. Check their research publications page\n"
            "3. Contact authors if dataset is not public\n"
            "4. Save files to: raw/academic/iiit_delhi/"
        ),
        "auto_download": False,
    },
]


def setup_logging():
    """Set up logging."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    logger.add(
        str(LOGS_DIR / "academic_downloads.log"),
        rotation="10 MB",
        retention="30 days",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    )
    logger.info("=" * 60)
    logger.info("Academic Dataset Downloader Started")
    logger.info("=" * 60)


def load_metadata():
    """Load metadata of previously downloaded files."""
    if METADATA_FILE.exists():
        with open(METADATA_FILE, "r") as f:
            return json.load(f)
    return {"datasets": [], "downloaded_urls": []}


def save_metadata(metadata):
    """Save metadata after each download."""
    METADATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(METADATA_FILE, "w") as f:
        json.dump(metadata, f, indent=2, default=str)


def download_file(url, save_path, description=""):
    """Download a single file with progress indication."""
    try:
        logger.info(f"DOWNLOADING: {description or url}")
        print(f"    Downloading: {description or save_path.name}...")

        response = requests.get(url, timeout=REQUEST_TIMEOUT, stream=True)
        response.raise_for_status()

        total_size = int(response.headers.get("content-length", 0))
        downloaded = 0

        save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    pct = (downloaded / total_size) * 100
                    print(f"\r    Progress: {pct:.0f}%", end="", flush=True)

        print()  # New line after progress
        size_mb = save_path.stat().st_size / (1024 * 1024)
        logger.info(f"SUCCESS: {save_path.name} ({size_mb:.1f} MB)")
        return True

    except Exception as e:
        logger.error(f"FAILED: {description or url} — {e}")
        print(f"    FAILED: {e}")
        return False


def extract_archive(archive_path, extract_dir):
    """
    Extract a zip or tar.gz file.
    After downloading, we unpack the archive so the
    images and labels are ready to use.
    """
    try:
        if archive_path.suffix == ".zip":
            logger.info(f"Extracting ZIP: {archive_path.name}")
            with zipfile.ZipFile(archive_path, "r") as z:
                z.extractall(extract_dir)
        elif archive_path.name.endswith(".tar.gz"):
            logger.info(f"Extracting TAR.GZ: {archive_path.name}")
            with tarfile.open(archive_path, "r:gz") as t:
                t.extractall(extract_dir)
        else:
            logger.info(f"Not an archive, keeping as-is: {archive_path.name}")
            return

        logger.info(f"Extracted to: {extract_dir}")

    except Exception as e:
        logger.error(f"Extraction failed for {archive_path.name}: {e}")


def process_dataset(dataset_info, metadata):
    """
    Process one academic dataset.
    Either download it automatically or print instructions
    for manual download.
    """
    name = dataset_info["name"]
    save_dir = RAW_ACADEMIC_DIR / name.lower().replace(" ", "_")
    save_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n  --- {name} ({dataset_info['source']}) ---")
    print(f"  {dataset_info['description'][:100]}...")

    if not dataset_info.get("auto_download", False):
        # This dataset needs manual steps
        print(f"\n  MANUAL DOWNLOAD REQUIRED:")
        if dataset_info.get("requires_registration"):
            print(f"  (Free registration needed)")
        if "instructions" in dataset_info:
            for line in dataset_info["instructions"].split("\n"):
                print(f"    {line}")
        if "registration_url" in dataset_info:
            print(f"  Register at: {dataset_info['registration_url']}")
        print(f"  Save to: {save_dir}")

        logger.info(
            f"{name} — requires manual download. "
            f"Folder created at {save_dir}"
        )

        metadata["datasets"].append({
            "name": name,
            "source": dataset_info["source"],
            "url": dataset_info["url"],
            "status": "manual_download_needed",
            "save_directory": str(save_dir),
            "logged_at": datetime.now().isoformat(),
        })
        save_metadata(metadata)
        return 0

    # Auto-download available
    count = 0
    download_urls = dataset_info.get("download_urls", [])

    for item in download_urls:
        url = item["url"]
        if url in metadata.get("downloaded_urls", []):
            logger.info(f"SKIP (duplicate): {item['filename']}")
            print(f"    SKIP (already have): {item['filename']}")
            continue

        save_path = save_dir / item["filename"]
        desc = item.get("description", item["filename"])

        if download_file(url, save_path, desc):
            # Try to extract if it's an archive
            extract_archive(save_path, save_dir)

            metadata["datasets"].append({
                "name": name,
                "source": dataset_info["source"],
                "url": url,
                "filename": item["filename"],
                "file_path": str(save_path),
                "status": "downloaded",
                "downloaded_at": datetime.now().isoformat(),
            })
            metadata["downloaded_urls"].append(url)
            save_metadata(metadata)
            count += 1

        time.sleep(DELAY_BETWEEN_REQUESTS)

    return count


def print_summary(metadata):
    """Print summary of academic dataset downloads."""
    datasets = metadata.get("datasets", [])

    downloaded = [d for d in datasets if d.get("status") == "downloaded"]
    manual = [d for d in datasets if d.get("status") == "manual_download_needed"]

    print("\n" + "=" * 50)
    print("  AIMCRS Academic Dataset Download Summary")
    print("=" * 50)
    print(f"  Auto-downloaded: {len(downloaded)} files")
    print(f"  Need manual download: {len(manual)} datasets")
    print()

    if manual:
        print("  Datasets needing manual download:")
        for d in manual:
            print(f"    - {d['name']} ({d['source']})")
            print(f"      URL: {d['url']}")
    print("=" * 50)


def main():
    """
    Main function — processes all academic datasets.
    Downloads what it can automatically, and prints
    instructions for datasets that need registration.
    """
    print("=" * 50)
    print("  AIMCRS Academic Dataset Downloader")
    print("  Traffic datasets from Indian universities & research")
    print("=" * 50)

    setup_logging()
    RAW_ACADEMIC_DIR.mkdir(parents=True, exist_ok=True)

    metadata = load_metadata()
    already_have = len(metadata.get("datasets", []))
    print(f"Already have {already_have} dataset records from previous runs")

    total = 0
    for dataset_info in ACADEMIC_DATASETS:
        count = process_dataset(dataset_info, metadata)
        total += count

    print_summary(metadata)

    logger.info("Academic Dataset Downloader Finished")
    print("\nDone! Check logs/academic_downloads.log for details.")


if __name__ == "__main__":
    main()
