"""
AIMCRS APINDRA Defence Intelligence Engine — Settings
=====================================================
This file holds all configuration for the entire system.
Think of it as the "control panel" where you set API keys,
timing, and thresholds.

⚠️ FREE TIER LIMITS:
- OpenSky: 10 seconds between requests (anonymous), 400 calls/day
- OpenWeatherMap: 60 calls/minute (free key required)
- USGS Earthquake: No limit (public)
- NASA FIRMS: Free with NASA Earthdata account
- GDELT: No limit (public)
- Celestrak: No limit (public)

⚠️ PAID APIs (not used unless you approve):
- ADS-B Exchange: Paid RapidAPI plan
- MarineTraffic: Paid API
- Twitter/X API: Paid for full access
- VesselFinder: Paid API
"""

import os

# ─────────────────────────────────────────────
# TIMING — How often the system refreshes
# ─────────────────────────────────────────────
REFRESH_INTERVAL_SECONDS = 60  # Update every 60 seconds
AGENT_SIMULATION_ROUNDS = 5   # How many rounds agents interact per cycle
AGENT_COUNT_DEFAULT = 20      # Start with 20 agents (scale up later)

# ─────────────────────────────────────────────
# THREAT SCORING — How threats are ranked
# ─────────────────────────────────────────────
THREAT_LEVEL_LOW = 0.0
THREAT_LEVEL_MEDIUM = 0.4
THREAT_LEVEL_HIGH = 0.7
THREAT_LEVEL_CRITICAL = 0.9
TOP_SCENARIOS_TO_SHOW = 5  # Show top 5 threats on dashboard

# ─────────────────────────────────────────────
# DATA SOURCE API KEYS
# Set these as environment variables or paste here
# ─────────────────────────────────────────────

# OpenSky Network — FREE, no key needed for anonymous
OPENSKY_USERNAME = os.environ.get("OPENSKY_USERNAME", "")
OPENSKY_PASSWORD = os.environ.get("OPENSKY_PASSWORD", "")

# OpenWeatherMap — FREE tier, needs signup at openweathermap.org
OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY", "")

# NASA Earthdata — FREE, needs signup at earthdata.nasa.gov
NASA_FIRMS_API_KEY = os.environ.get("NASA_FIRMS_API_KEY", "")

# ─────────────────────────────────────────────
# DATA SOURCE URLs — All free and open
# ─────────────────────────────────────────────
OPENSKY_API_URL = "https://opensky-network.org/api"
CELESTRAK_URL = "https://celestrak.org/NORAD/elements/gp.php"
USGS_EARTHQUAKE_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson"
NASA_FIRMS_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
GDELT_URL = "http://api.gdeltproject.org/api/v2/doc/doc"
OVERPASS_API_URL = "https://overpass-api.de/api/interpreter"
OPENWEATHER_URL = "https://api.openweathermap.org/data/2.5"

# ─────────────────────────────────────────────
# FILE PATHS
# ─────────────────────────────────────────────
import pathlib

PROJECT_ROOT = pathlib.Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data_store"
REPORTS_DIR = PROJECT_ROOT / "reports"
LOGS_DIR = PROJECT_ROOT / "logs"
DB_PATH = PROJECT_ROOT / "data_store" / "simulation.db"

# Create directories if they don't exist
for d in [DATA_DIR, REPORTS_DIR, LOGS_DIR]:
    d.mkdir(parents=True, exist_ok=True)
