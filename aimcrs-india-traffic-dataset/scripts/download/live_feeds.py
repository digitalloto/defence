#!/usr/bin/env python3
# ============================================
# Step 6 — Live Data Feeds Connector
# ============================================
# File: scripts/download/live_feeds.py
# What: Connects to live traffic APIs for real-time data
# How to run: python scripts/download/live_feeds.py
#
# Sources:
#   1. OpenStreetMap Overpass API (FREE — no key needed)
#   2. TomTom Traffic API (FREE tier — 2500 req/day)
#   3. HERE Maps Traffic API (FREE tier — 250K req/month)
#   4. MapMyIndia/Mappls API (FREE tier — limited)
#
# ⚠️ PAID FLAGS:
#   - TomTom: Free tier is 2,500 requests/day. Paid after.
#   - HERE: Free tier is 250,000 requests/month. Paid after.
#   - Mappls: Limited free tier. Check their pricing.
#   - Google Maps: Check ToS before scraping. NOT implemented.
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
RAW_GOV_DIR = PROJECT_ROOT / "raw" / "government"
LIVE_DATA_DIR = RAW_GOV_DIR / "live_feeds"
LOGS_DIR = PROJECT_ROOT / "logs"

# ----- API KEYS -----
TOMTOM_API_KEY = os.getenv("TOMTOM_API_KEY", "")
HERE_API_KEY = os.getenv("HERE_API_KEY", "")
MAPPLS_CLIENT_ID = os.getenv("MAPPLS_CLIENT_ID", "")
MAPPLS_CLIENT_SECRET = os.getenv("MAPPLS_CLIENT_SECRET", "")

# ----- SETTINGS -----
REQUEST_TIMEOUT = 30
DELAY_BETWEEN_REQUESTS = 2

# ----- INDIAN CITY COORDINATES -----
# Latitude and longitude of major Indian cities.
# We use these to query traffic data for specific areas.

INDIAN_CITIES = {
    "Chennai": {"lat": 13.0827, "lon": 80.2707},
    "Mumbai": {"lat": 19.0760, "lon": 72.8777},
    "Delhi": {"lat": 28.6139, "lon": 77.2090},
    "Bengaluru": {"lat": 12.9716, "lon": 77.5946},
    "Hyderabad": {"lat": 17.3850, "lon": 78.4867},
    "Kolkata": {"lat": 22.5726, "lon": 88.3639},
    "Pune": {"lat": 18.5204, "lon": 73.8567},
    "Raipur": {"lat": 21.2514, "lon": 81.6296},
}


def setup_logging():
    """Set up logging."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    logger.add(
        str(LOGS_DIR / "live_feeds.log"),
        rotation="10 MB",
        retention="30 days",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    )
    logger.info("=" * 60)
    logger.info("Live Data Feeds Started")
    logger.info("=" * 60)


def save_json(data, filepath):
    """Save data as JSON file."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, default=str)


# ============================================
# SOURCE 1: OpenStreetMap Overpass API (FREE)
# ============================================

def fetch_osm_traffic_data(city_name, lat, lon):
    """
    Query OpenStreetMap for road and traffic infrastructure data.

    What is Overpass API?
    It lets you search OpenStreetMap's database. We query for:
    - Traffic signals
    - Road types and names
    - Speed limits
    - Intersections

    This is FREE and needs NO API key.
    """
    logger.info(f"OSM: Fetching data for {city_name}")

    # Overpass API endpoint
    overpass_url = "https://overpass-api.de/api/interpreter"

    # Search in a box around the city center (roughly 5km radius)
    # bbox format: south, west, north, east
    bbox = f"{lat - 0.05},{lon - 0.05},{lat + 0.05},{lon + 0.05}"

    # Overpass QL query: find traffic signals and main roads
    query = f"""
    [out:json][timeout:60];
    (
      node["highway"="traffic_signals"]({bbox});
      way["highway"~"primary|secondary|tertiary|trunk"]({bbox});
      node["amenity"="hospital"]({bbox});
    );
    out body;
    >;
    out skel qt;
    """

    try:
        response = requests.post(
            overpass_url,
            data={"data": query},
            timeout=REQUEST_TIMEOUT * 2,
        )
        response.raise_for_status()
        data = response.json()

        elements = data.get("elements", [])

        # Count what we found
        signals = sum(
            1 for e in elements
            if e.get("tags", {}).get("highway") == "traffic_signals"
        )
        roads = sum(
            1 for e in elements if e.get("type") == "way"
        )
        hospitals = sum(
            1 for e in elements
            if e.get("tags", {}).get("amenity") == "hospital"
        )

        # Save raw data
        save_path = LIVE_DATA_DIR / "osm" / f"{city_name}_traffic.json"
        save_json(data, save_path)

        logger.info(
            f"OSM {city_name}: {signals} signals, "
            f"{roads} roads, {hospitals} hospitals"
        )
        print(
            f"    {city_name}: {signals} traffic signals, "
            f"{roads} roads, {hospitals} hospitals"
        )

        return {
            "city": city_name,
            "source": "openstreetmap",
            "signals": signals,
            "roads": roads,
            "hospitals": hospitals,
            "total_elements": len(elements),
            "file_path": str(save_path),
            "fetched_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"OSM {city_name} failed: {e}")
        print(f"    {city_name}: FAILED — {e}")
        return None


# ============================================
# SOURCE 2: TomTom Traffic API
# ⚠️ FREE TIER: 2,500 requests/day
# ============================================

def fetch_tomtom_traffic(city_name, lat, lon):
    """
    Get real-time traffic flow data from TomTom.

    What does this give us?
    - Current traffic speed on roads
    - Free flow speed (speed with no traffic)
    - Congestion level
    - Road closure info

    ⚠️ FREE TIER: 2,500 requests per day. After that it costs money.
    """
    if not TOMTOM_API_KEY or TOMTOM_API_KEY == "your_tomtom_api_key_here":
        logger.info("TomTom: Skipped — no API key")
        return None

    logger.info(f"TomTom: Fetching traffic for {city_name}")

    # TomTom Traffic Flow API
    url = (
        f"https://api.tomtom.com/traffic/services/4/flowSegmentData"
        f"/absolute/10/json"
    )
    params = {
        "point": f"{lat},{lon}",
        "key": TOMTOM_API_KEY,
        "unit": "KMPH",
    }

    try:
        response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        flow = data.get("flowSegmentData", {})
        current_speed = flow.get("currentSpeed", 0)
        free_flow_speed = flow.get("freeFlowSpeed", 0)
        confidence = flow.get("confidence", 0)

        # Calculate congestion level
        if free_flow_speed > 0:
            ratio = current_speed / free_flow_speed
            if ratio > 0.8:
                congestion = "low"
            elif ratio > 0.5:
                congestion = "medium"
            elif ratio > 0.25:
                congestion = "high"
            else:
                congestion = "severe"
        else:
            congestion = "unknown"

        save_path = LIVE_DATA_DIR / "tomtom" / f"{city_name}_traffic.json"
        save_json(data, save_path)

        logger.info(
            f"TomTom {city_name}: {current_speed} km/h "
            f"(free flow: {free_flow_speed}), congestion: {congestion}"
        )
        print(
            f"    {city_name}: {current_speed} km/h "
            f"(congestion: {congestion})"
        )

        return {
            "city": city_name,
            "source": "tomtom",
            "current_speed_kmph": current_speed,
            "free_flow_speed_kmph": free_flow_speed,
            "congestion": congestion,
            "confidence": confidence,
            "file_path": str(save_path),
            "fetched_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"TomTom {city_name} failed: {e}")
        print(f"    {city_name}: FAILED — {e}")
        return None


# ============================================
# SOURCE 3: HERE Maps Traffic API
# ⚠️ FREE TIER: 250,000 requests/month
# ============================================

def fetch_here_traffic(city_name, lat, lon):
    """
    Get real-time traffic data from HERE Maps.

    ⚠️ FREE TIER: 250,000 requests per month. Paid after.
    """
    if not HERE_API_KEY or HERE_API_KEY == "your_here_api_key_here":
        logger.info("HERE: Skipped — no API key")
        return None

    logger.info(f"HERE: Fetching traffic for {city_name}")

    url = "https://data.traffic.hereapi.com/v7/flow"
    params = {
        "in": f"circle:{lat},{lon};r=5000",
        "apiKey": HERE_API_KEY,
        "locationReferencing": "shape",
    }

    try:
        response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        results = data.get("results", [])

        save_path = LIVE_DATA_DIR / "here" / f"{city_name}_traffic.json"
        save_json(data, save_path)

        logger.info(f"HERE {city_name}: {len(results)} road segments")
        print(f"    {city_name}: {len(results)} road segments")

        return {
            "city": city_name,
            "source": "here_maps",
            "road_segments": len(results),
            "file_path": str(save_path),
            "fetched_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"HERE {city_name} failed: {e}")
        print(f"    {city_name}: FAILED — {e}")
        return None


def print_api_status():
    """Print which APIs are configured."""
    print("\n  API Status:")
    print(f"    OpenStreetMap: READY (no key needed)")

    if TOMTOM_API_KEY and TOMTOM_API_KEY != "your_tomtom_api_key_here":
        print(f"    TomTom: READY (⚠️ 2,500 free requests/day)")
    else:
        print(f"    TomTom: NOT CONFIGURED (add key to .env)")

    if HERE_API_KEY and HERE_API_KEY != "your_here_api_key_here":
        print(f"    HERE Maps: READY (⚠️ 250K free requests/month)")
    else:
        print(f"    HERE Maps: NOT CONFIGURED (add key to .env)")

    if MAPPLS_CLIENT_ID and MAPPLS_CLIENT_ID != "your_mappls_client_id_here":
        print(f"    Mappls: READY (⚠️ limited free tier)")
    else:
        print(f"    Mappls: NOT CONFIGURED (add key to .env)")

    # Google Maps note
    print(f"    Google Maps: NOT IMPLEMENTED (⚠️ check ToS first)")
    print()


def main():
    """
    Main function — fetches live traffic data from all sources.
    """
    print("=" * 50)
    print("  AIMCRS Live Traffic Data Feeds")
    print("  Real-time Indian city traffic data")
    print("=" * 50)

    setup_logging()
    LIVE_DATA_DIR.mkdir(parents=True, exist_ok=True)

    print_api_status()

    all_results = []

    # Source 1: OpenStreetMap (always works — no key needed)
    print("--- Source 1: OpenStreetMap (FREE) ---")
    for city, coords in INDIAN_CITIES.items():
        result = fetch_osm_traffic_data(city, coords["lat"], coords["lon"])
        if result:
            all_results.append(result)
        time.sleep(DELAY_BETWEEN_REQUESTS)

    # Source 2: TomTom
    print("\n--- Source 2: TomTom (⚠️ 2,500 free/day) ---")
    for city, coords in INDIAN_CITIES.items():
        result = fetch_tomtom_traffic(city, coords["lat"], coords["lon"])
        if result:
            all_results.append(result)
        time.sleep(DELAY_BETWEEN_REQUESTS)

    # Source 3: HERE Maps
    print("\n--- Source 3: HERE Maps (⚠️ 250K free/month) ---")
    for city, coords in INDIAN_CITIES.items():
        result = fetch_here_traffic(city, coords["lat"], coords["lon"])
        if result:
            all_results.append(result)
        time.sleep(DELAY_BETWEEN_REQUESTS)

    # Save combined results
    summary_path = LIVE_DATA_DIR / "latest_summary.json"
    save_json({
        "fetched_at": datetime.now().isoformat(),
        "cities": list(INDIAN_CITIES.keys()),
        "results": all_results,
    }, summary_path)

    # Summary
    print("\n" + "=" * 50)
    print("  Live Data Feed Summary")
    print("=" * 50)
    print(f"  Total data points: {len(all_results)}")
    print(f"  Cities covered: {len(INDIAN_CITIES)}")
    print(f"  Summary saved: {summary_path}")
    print("=" * 50)

    logger.info("Live Data Feeds Finished")
    print("\nDone! Check logs/live_feeds.log for details.")
    print("TIP: Run this script regularly (daily) to build")
    print("     up historical traffic pattern data.")


if __name__ == "__main__":
    main()
