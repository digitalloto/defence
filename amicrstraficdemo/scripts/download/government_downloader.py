#!/usr/bin/env python3
# ============================================
# Step 2 — Government Open Data Downloader
# ============================================
# File: scripts/download/government_downloader.py
# What: Downloads Indian traffic data from government sources
# How to run: python scripts/download/government_downloader.py
#
# Sources:
#   1. data.gov.in — India Open Government Data Portal
#   2. Smart Cities Mission — smartcities.gov.in
#   3. MoRTH — Ministry of Road Transport & Highways
#   4. NCRB — National Crime Records Bureau
#   5. Delhi Traffic Police
#   6. iRAD — Integrated Road Accident Database
# ============================================

import os
import sys
import json
import time
import csv
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import requests
except ImportError:
    print("ERROR: requests is not installed.")
    print("Fix: pip install requests")
    sys.exit(1)

try:
    from loguru import logger
except ImportError:
    print("ERROR: loguru is not installed.")
    print("Fix: pip install loguru")
    sys.exit(1)

try:
    from dotenv import load_dotenv
except ImportError:
    print("ERROR: python-dotenv is not installed.")
    print("Fix: pip install python-dotenv")
    sys.exit(1)

# Load API keys from .env file
load_dotenv(PROJECT_ROOT / ".env")

# ----- PATHS -----
RAW_GOV_DIR = PROJECT_ROOT / "raw" / "government"
LOGS_DIR = PROJECT_ROOT / "logs"
METADATA_FILE = RAW_GOV_DIR / "metadata.json"

# ----- API KEYS -----
DATA_GOV_IN_API_KEY = os.getenv("DATA_GOV_IN_API_KEY", "")

# ----- SETTINGS -----
DELAY_BETWEEN_REQUESTS = 3  # seconds — be polite to government servers
REQUEST_TIMEOUT = 30         # seconds before giving up on a request


def setup_logging():
    """Set up logging."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    logger.add(
        str(LOGS_DIR / "government_downloads.log"),
        rotation="10 MB",
        retention="30 days",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    )
    logger.info("=" * 60)
    logger.info("Government Data Downloader Started")
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


def safe_download(url, save_path, description=""):
    """
    Download a file safely with error handling.
    Returns True if successful, False if failed.
    """
    try:
        logger.info(f"DOWNLOADING: {description or url}")
        response = requests.get(url, timeout=REQUEST_TIMEOUT, stream=True)
        response.raise_for_status()

        save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        size_mb = save_path.stat().st_size / (1024 * 1024)
        logger.info(f"SUCCESS: {save_path.name} ({size_mb:.1f} MB)")
        return True

    except requests.exceptions.RequestException as e:
        logger.error(f"FAILED: {description or url} — {e}")
        return False


def download_data_gov_in(metadata):
    """
    Source 1: data.gov.in — India Open Government Data Portal

    What is this?
    The Indian government puts lots of data on this website
    for free. We search for traffic-related data.

    API docs: https://data.gov.in/apis
    """
    print("\n--- Source 1: data.gov.in ---")
    logger.info("Querying data.gov.in for traffic datasets")

    save_dir = RAW_GOV_DIR / "data_gov_in"
    save_dir.mkdir(parents=True, exist_ok=True)

    # Search terms to find traffic data
    search_terms = [
        "traffic",
        "road accident",
        "vehicle registration",
        "road safety",
        "traffic signal",
        "highway traffic",
        "motor vehicle",
    ]

    # The data.gov.in API endpoint
    base_url = "https://data.gov.in/backend/dmspublic/v1/resources"
    count = 0

    for term in search_terms:
        logger.info(f"Searching data.gov.in for: '{term}'")

        params = {
            "filters[search]": term,
            "limit": 20,
            "offset": 0,
        }

        # Add API key if available
        if DATA_GOV_IN_API_KEY and DATA_GOV_IN_API_KEY != "your_data_gov_in_key_here":
            params["api_key"] = DATA_GOV_IN_API_KEY

        try:
            response = requests.get(
                base_url, params=params, timeout=REQUEST_TIMEOUT
            )

            if response.status_code == 200:
                data = response.json()
                results = data.get("data", data.get("records", []))

                if isinstance(results, list):
                    for item in results:
                        resource_url = item.get("datafile", item.get("url", ""))
                        title = item.get("title", "unknown")

                        if not resource_url:
                            continue
                        if resource_url in metadata.get("downloaded_urls", []):
                            logger.info(f"SKIP (duplicate): {title}")
                            continue

                        # Figure out file extension
                        ext = ".csv"
                        if ".json" in resource_url.lower():
                            ext = ".json"
                        elif ".xlsx" in resource_url.lower():
                            ext = ".xlsx"
                        elif ".pdf" in resource_url.lower():
                            ext = ".pdf"

                        safe_name = "".join(
                            c if c.isalnum() or c in "._-" else "_"
                            for c in title[:80]
                        )
                        save_path = save_dir / f"{safe_name}{ext}"

                        if safe_download(resource_url, save_path, title):
                            metadata["datasets"].append({
                                "title": title,
                                "url": resource_url,
                                "source": "data.gov.in",
                                "search_term": term,
                                "file_path": str(save_path),
                                "downloaded_at": datetime.now().isoformat(),
                            })
                            metadata["downloaded_urls"].append(resource_url)
                            save_metadata(metadata)
                            count += 1

                        time.sleep(DELAY_BETWEEN_REQUESTS)
            else:
                logger.warning(
                    f"data.gov.in returned status {response.status_code} "
                    f"for '{term}'"
                )

        except Exception as e:
            logger.error(f"data.gov.in search failed for '{term}': {e}")

        time.sleep(DELAY_BETWEEN_REQUESTS)

    print(f"  data.gov.in: downloaded {count} datasets")
    return count


def download_morth_reports(metadata):
    """
    Source 3: MoRTH — Ministry of Road Transport & Highways

    What is this?
    The government ministry that handles roads and transport.
    They publish reports on road accidents every year.
    These are usually PDF files.

    URL: https://morth.nic.in
    """
    print("\n--- Source 3: MoRTH (Road Transport Ministry) ---")
    logger.info("Downloading MoRTH reports")

    save_dir = RAW_GOV_DIR / "morth"
    save_dir.mkdir(parents=True, exist_ok=True)

    # Known report URLs — MoRTH publishes annual road accident reports
    # These URLs may change; the script logs failures so you know
    # which ones need manual download.
    known_reports = [
        {
            "name": "Road_Accidents_India_2022",
            "url": "https://morth.nic.in/sites/default/files/RA_2022_Uploads.pdf",
            "description": "Road Accidents in India 2022 — Annual Report",
        },
        {
            "name": "Road_Accidents_India_2021",
            "url": "https://morth.nic.in/sites/default/files/RA_Uploading.pdf",
            "description": "Road Accidents in India 2021 — Annual Report",
        },
    ]

    count = 0
    for report in known_reports:
        url = report["url"]
        if url in metadata.get("downloaded_urls", []):
            logger.info(f"SKIP (duplicate): {report['name']}")
            continue

        save_path = save_dir / f"{report['name']}.pdf"
        if safe_download(url, save_path, report["description"]):
            metadata["datasets"].append({
                "title": report["description"],
                "url": url,
                "source": "morth.nic.in",
                "file_path": str(save_path),
                "downloaded_at": datetime.now().isoformat(),
            })
            metadata["downloaded_urls"].append(url)
            save_metadata(metadata)
            count += 1
        else:
            logger.warning(
                f"MoRTH report failed to download: {report['name']}. "
                f"You may need to download manually from: {url}"
            )

        time.sleep(DELAY_BETWEEN_REQUESTS)

    print(f"  MoRTH: downloaded {count} reports")
    return count


def download_ncrb_data(metadata):
    """
    Source 4: NCRB — National Crime Records Bureau

    What is this?
    NCRB tracks crime and accident data across India.
    They publish "Accidental Deaths & Suicides in India" reports
    which include detailed road accident statistics.

    URL: https://ncrb.gov.in
    """
    print("\n--- Source 4: NCRB (Crime Records Bureau) ---")
    logger.info("Downloading NCRB accident data")

    save_dir = RAW_GOV_DIR / "ncrb"
    save_dir.mkdir(parents=True, exist_ok=True)

    known_reports = [
        {
            "name": "ADSI_2022",
            "url": "https://ncrb.gov.in/uploads/nationalcrimerecordsbureau/custom/1701607577ADSI2022FullReport.pdf",
            "description": "Accidental Deaths & Suicides in India 2022",
        },
        {
            "name": "ADSI_2021",
            "url": "https://ncrb.gov.in/uploads/nationalcrimerecordsbureau/custom/1662091384Chapter-1A-2021.pdf",
            "description": "Accidental Deaths Report 2021 — Chapter 1A Traffic",
        },
    ]

    count = 0
    for report in known_reports:
        url = report["url"]
        if url in metadata.get("downloaded_urls", []):
            logger.info(f"SKIP (duplicate): {report['name']}")
            continue

        save_path = save_dir / f"{report['name']}.pdf"
        if safe_download(url, save_path, report["description"]):
            metadata["datasets"].append({
                "title": report["description"],
                "url": url,
                "source": "ncrb.gov.in",
                "file_path": str(save_path),
                "downloaded_at": datetime.now().isoformat(),
            })
            metadata["downloaded_urls"].append(url)
            save_metadata(metadata)
            count += 1
        else:
            logger.warning(
                f"NCRB report failed: {report['name']}. "
                f"May need manual download from ncrb.gov.in"
            )

        time.sleep(DELAY_BETWEEN_REQUESTS)

    print(f"  NCRB: downloaded {count} reports")
    return count


def create_master_index(metadata):
    """
    Create a master index CSV file listing every dataset downloaded.
    This makes it easy to see everything at a glance.
    """
    index_path = RAW_GOV_DIR / "master_index.csv"
    datasets = metadata.get("datasets", [])

    if not datasets:
        logger.info("No datasets to index")
        return

    fieldnames = [
        "title", "source", "url", "file_path",
        "downloaded_at", "search_term",
    ]

    with open(index_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for dataset in datasets:
            writer.writerow(dataset)

    logger.info(f"Master index saved: {index_path} ({len(datasets)} entries)")
    print(f"\nMaster index: {index_path} ({len(datasets)} datasets)")


def print_summary(metadata):
    """Print summary of all government data downloaded."""
    datasets = metadata.get("datasets", [])
    total = len(datasets)

    source_counts = {}
    for d in datasets:
        source = d.get("source", "unknown")
        source_counts[source] = source_counts.get(source, 0) + 1

    print("\n" + "=" * 50)
    print("  AIMCRS Government Data Download Summary")
    print("=" * 50)
    print(f"  Total datasets downloaded: {total}")
    print()
    print("  By source:")
    for source, count in sorted(source_counts.items()):
        print(f"    {source}: {count}")
    print("=" * 50)

    # Sources that need manual checking
    print("\n  NOTE: Some government sites change their URLs often.")
    print("  If any downloads failed, check the log file:")
    print(f"    {LOGS_DIR / 'government_downloads.log'}")
    print()
    print("  You may need to manually visit these sites:")
    print("    - https://smartcities.gov.in (Smart Cities data)")
    print("    - https://delhitrafficpolice.nic.in (Delhi traffic)")
    print("    - https://irad.nic.in (Accident database)")
    print("  and download available datasets by hand.")
    print()


def main():
    """
    Main function — downloads from all government sources.

    Order:
    1. data.gov.in (has API — automated)
    2. Smart Cities (manual note — site structure varies)
    3. MoRTH reports (direct PDF downloads)
    4. NCRB reports (direct PDF downloads)
    5. Delhi Traffic Police (manual note)
    6. iRAD (manual note)
    7. Create master index
    """
    print("=" * 50)
    print("  AIMCRS Government Data Downloader")
    print("  Indian traffic & accident data from official sources")
    print("=" * 50)

    setup_logging()
    RAW_GOV_DIR.mkdir(parents=True, exist_ok=True)

    metadata = load_metadata()
    already_have = len(metadata.get("datasets", []))
    print(f"Already have {already_have} datasets from previous runs")

    total = 0

    # Source 1: data.gov.in (API-based)
    total += download_data_gov_in(metadata)

    # Source 2: Smart Cities Mission
    # NOTE: smartcities.gov.in does not have a consistent API.
    # The data is spread across individual city dashboards.
    print("\n--- Source 2: Smart Cities Mission ---")
    print("  NOTE: smartcities.gov.in requires manual browsing.")
    print("  Visit https://smartcities.gov.in and download traffic")
    print("  datasets for: Chennai, Mumbai, Delhi, Pune, Surat,")
    print("  Ahmedabad, Bengaluru")
    print("  Save files to: raw/government/smart_cities/")
    smart_cities_dir = RAW_GOV_DIR / "smart_cities"
    smart_cities_dir.mkdir(parents=True, exist_ok=True)
    logger.info(
        "Smart Cities Mission — requires manual download. "
        "Folder created at raw/government/smart_cities/"
    )

    # Source 3: MoRTH
    total += download_morth_reports(metadata)

    # Source 4: NCRB
    total += download_ncrb_data(metadata)

    # Source 5: Delhi Traffic Police
    print("\n--- Source 5: Delhi Traffic Police ---")
    print("  NOTE: delhitrafficpolice.nic.in requires manual browsing.")
    print("  Look for: traffic flow data, signal timing data")
    print("  Save files to: raw/government/delhi_traffic_police/")
    delhi_dir = RAW_GOV_DIR / "delhi_traffic_police"
    delhi_dir.mkdir(parents=True, exist_ok=True)
    logger.info(
        "Delhi Traffic Police — requires manual download. "
        "Folder created."
    )

    # Source 6: iRAD
    print("\n--- Source 6: iRAD (Accident Database) ---")
    print("  NOTE: irad.nic.in may require registration.")
    print("  Visit https://irad.nic.in and download available data.")
    print("  Save files to: raw/government/irad/")
    irad_dir = RAW_GOV_DIR / "irad"
    irad_dir.mkdir(parents=True, exist_ok=True)
    logger.info(
        "iRAD — requires manual download / registration. "
        "Folder created."
    )

    # Create master index
    create_master_index(metadata)

    # Summary
    print_summary(metadata)

    logger.info("Government Data Downloader Finished")
    print("Done! Check logs/government_downloads.log for details.")


if __name__ == "__main__":
    main()
