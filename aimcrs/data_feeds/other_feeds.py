"""
LAYER 3 — OTHER DATA FEEDS (All Free, All Open Source)
=======================================================
Each class pulls live data from one free public source.
These are added one at a time — test before adding next.

SOURCES INCLUDED:
1. CelestrakFeed — Satellite orbital data
2. USGSEarthquakeFeed — Earthquake data worldwide
3. GDELTFeed — Global news event database
4. OpenWeatherFeed — Weather data (free API key needed)
5. NASAFirmsFeed — Fire and disaster monitoring

⚠️ SOURCES THAT NEED PAID API (not included):
- ADS-B Exchange (RapidAPI paid plan)
- MarineTraffic (paid API)
- VesselFinder (paid API)
- Twitter/X full API (paid)

All functions return dictionaries so agents can read them easily.
"""

import requests
import json
import time
from datetime import datetime, timezone
from config.settings import (
    CELESTRAK_URL,
    USGS_EARTHQUAKE_URL,
    GDELT_URL,
    OPENWEATHER_URL,
    OPENWEATHER_API_KEY,
    NASA_FIRMS_URL,
    NASA_FIRMS_API_KEY,
)


# ─────────────────────────────────────────────
# 1. CELESTRAK — Satellite Orbital Data
# ─────────────────────────────────────────────

class CelestrakFeed:
    """
    Pulls satellite position data from Celestrak.org.
    Completely free, no API key needed.

    What you get:
    - Satellite name
    - Orbit parameters (altitude, inclination, period)
    - TLE data (Two-Line Element — the math to track a satellite)

    Useful for: Knowing what's overhead, tracking military satellites.
    """

    def __init__(self):
        self.base_url = CELESTRAK_URL

    def get_satellites(self, group: str = "active") -> dict:
        """
        Get satellite data by group.

        Groups available (all free):
        - "active" — all active satellites
        - "stations" — space stations (ISS etc.)
        - "visual" — brightest satellites
        - "military" — known military satellites
        - "gps-ops" — GPS satellites
        - "starlink" — Starlink constellation

        Returns list of satellite data dictionaries.
        """
        params = {"GROUP": group, "FORMAT": "json"}

        try:
            response = requests.get(
                self.base_url, params=params, timeout=30
            )
            if response.status_code == 200:
                satellites = response.json()
                return {
                    "satellites": satellites,
                    "count": len(satellites),
                    "group": group,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            return {
                "satellites": [],
                "count": 0,
                "error": f"HTTP {response.status_code}",
            }
        except Exception as e:
            return {"satellites": [], "count": 0, "error": str(e)}


# ─────────────────────────────────────────────
# 2. USGS — Earthquake Data
# ─────────────────────────────────────────────

class USGSEarthquakeFeed:
    """
    Pulls earthquake data from US Geological Survey.
    Completely free, no API key needed.

    Why this matters for defence:
    - Earthquakes can disrupt military operations
    - Underground nuclear tests show as earthquakes
    - Infrastructure damage affects logistics
    """

    def __init__(self):
        self.base_url = USGS_EARTHQUAKE_URL

    def get_recent_earthquakes(self) -> dict:
        """
        Get earthquakes from the last hour.
        Returns GeoJSON format with magnitude, location, depth.
        """
        try:
            response = requests.get(self.base_url, timeout=30)
            if response.status_code == 200:
                data = response.json()
                features = data.get("features", [])
                parsed = []
                for f in features:
                    props = f.get("properties", {})
                    coords = f.get("geometry", {}).get("coordinates", [0, 0, 0])
                    parsed.append({
                        "magnitude": props.get("mag", 0),
                        "place": props.get("place", "Unknown"),
                        "time": props.get("time", 0),
                        "depth_km": coords[2] if len(coords) > 2 else 0,
                        "latitude": coords[1] if len(coords) > 1 else 0,
                        "longitude": coords[0],
                        "tsunami_warning": props.get("tsunami", 0) == 1,
                        "significance": props.get("sig", 0),
                    })
                return {
                    "earthquakes": parsed,
                    "count": len(parsed),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            return {
                "earthquakes": [],
                "count": 0,
                "error": f"HTTP {response.status_code}",
            }
        except Exception as e:
            return {"earthquakes": [], "count": 0, "error": str(e)}


# ─────────────────────────────────────────────
# 3. GDELT — Global Event Database
# ─────────────────────────────────────────────

class GDELTFeed:
    """
    Pulls global news events from the GDELT Project.
    Completely free, no API key needed.

    GDELT monitors news worldwide in 100+ languages and
    extracts events, people, locations, and themes.

    Why this matters for defence:
    - Monitors global conflicts and tensions
    - Tracks military movements reported in news
    - Detects emerging crises from news patterns
    """

    def __init__(self):
        self.base_url = GDELT_URL

    def get_recent_events(self, query: str = "military conflict",
                          max_records: int = 50) -> dict:
        """
        Search for recent global events matching a query.

        Parameters:
        - query: What to search for (e.g., "military", "missile", "border")
        - max_records: How many results to return (max 250)

        Returns list of news articles with titles, sources, dates.
        """
        params = {
            "query": query,
            "mode": "ArtList",
            "maxrecords": str(max_records),
            "format": "json",
            "sort": "DateDesc",
        }

        try:
            response = requests.get(
                self.base_url, params=params, timeout=30
            )
            if response.status_code == 200:
                data = response.json()
                articles = data.get("articles", [])
                parsed = []
                for article in articles:
                    parsed.append({
                        "title": article.get("title", ""),
                        "source": article.get("domain", ""),
                        "url": article.get("url", ""),
                        "date": article.get("seendate", ""),
                        "language": article.get("language", ""),
                        "source_country": article.get("sourcecountry", ""),
                    })
                return {
                    "articles": parsed,
                    "count": len(parsed),
                    "query": query,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            return {
                "articles": [],
                "count": 0,
                "error": f"HTTP {response.status_code}",
            }
        except Exception as e:
            return {"articles": [], "count": 0, "error": str(e)}


# ─────────────────────────────────────────────
# 4. OPENWEATHERMAP — Weather Data
# ─────────────────────────────────────────────

class OpenWeatherFeed:
    """
    Pulls weather data from OpenWeatherMap.

    ⚠️ NEEDS FREE API KEY:
    Sign up at https://openweathermap.org/api
    Free tier: 60 calls/minute, current weather + 5-day forecast.

    Why this matters for defence:
    - Weather affects military operations
    - Severe weather can mask movements
    - Weather events can be security-relevant
    """

    def __init__(self, api_key: str = ""):
        self.base_url = OPENWEATHER_URL
        self.api_key = api_key or OPENWEATHER_API_KEY

    def get_weather(self, lat: float, lon: float) -> dict:
        """
        Get current weather at a specific location.

        Parameters:
        - lat: Latitude (e.g., 13.0827 for Chennai)
        - lon: Longitude (e.g., 80.2707 for Chennai)
        """
        if not self.api_key:
            return {
                "error": "No API key. Sign up free at openweathermap.org",
                "data": {},
            }

        params = {
            "lat": lat,
            "lon": lon,
            "appid": self.api_key,
            "units": "metric",
        }

        try:
            response = requests.get(
                f"{self.base_url}/weather", params=params, timeout=30
            )
            if response.status_code == 200:
                data = response.json()
                return {
                    "location": data.get("name", "Unknown"),
                    "temperature_c": data.get("main", {}).get("temp"),
                    "humidity": data.get("main", {}).get("humidity"),
                    "wind_speed_mps": data.get("wind", {}).get("speed"),
                    "wind_direction": data.get("wind", {}).get("deg"),
                    "visibility_m": data.get("visibility"),
                    "conditions": data.get("weather", [{}])[0].get(
                        "description", ""
                    ),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            return {"error": f"HTTP {response.status_code}", "data": {}}
        except Exception as e:
            return {"error": str(e), "data": {}}


# ─────────────────────────────────────────────
# 5. NASA FIRMS — Fire & Disaster Monitoring
# ─────────────────────────────────────────────

class NASAFirmsFeed:
    """
    Pulls active fire data from NASA FIRMS.

    ⚠️ NEEDS FREE API KEY:
    Sign up at https://firms.modaps.eosdis.nasa.gov/api/area/
    Create account at https://urs.earthdata.nasa.gov/

    Why this matters for defence:
    - Fires can indicate bombings or attacks
    - Wildfire smoke affects air operations
    - Industrial fires may signal sabotage
    """

    def __init__(self, api_key: str = ""):
        self.api_key = api_key or NASA_FIRMS_API_KEY

    def get_active_fires(self, country: str = "IND",
                         days: int = 1) -> dict:
        """
        Get active fire hotspots.

        Parameters:
        - country: ISO country code (IND=India, USA, CHN, etc.)
        - days: How many days back to look (1-10)

        Returns list of fire locations with coordinates and intensity.
        """
        if not self.api_key:
            return {
                "error": "No API key. Sign up free at earthdata.nasa.gov",
                "fires": [],
            }

        url = (
            f"{NASA_FIRMS_URL}"
            f"/{self.api_key}/VIIRS_SNPP_NRT/{country}/{days}"
        )

        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                # CSV response — parse it
                lines = response.text.strip().split("\n")
                if len(lines) < 2:
                    return {"fires": [], "count": 0}

                headers = lines[0].split(",")
                fires = []
                for line in lines[1:]:
                    values = line.split(",")
                    if len(values) >= len(headers):
                        fire = dict(zip(headers, values))
                        fires.append({
                            "latitude": float(fire.get("latitude", 0)),
                            "longitude": float(fire.get("longitude", 0)),
                            "brightness": float(
                                fire.get("bright_ti4", 0)
                            ),
                            "confidence": fire.get("confidence", ""),
                            "date": fire.get("acq_date", ""),
                            "time": fire.get("acq_time", ""),
                        })

                return {
                    "fires": fires,
                    "count": len(fires),
                    "country": country,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            return {
                "fires": [],
                "count": 0,
                "error": f"HTTP {response.status_code}",
            }
        except Exception as e:
            return {"fires": [], "count": 0, "error": str(e)}


# ─────────────────────────────────────────────
# MASTER DATA COLLECTOR
# Pulls from all sources at once
# ─────────────────────────────────────────────

class DataCollector:
    """
    Pulls data from ALL free sources in one call.

    How to use:
        collector = DataCollector()
        all_data = collector.collect_all()
        # all_data is a dictionary with data from every source

    You can then feed this into the simulation engine:
        for source_name, data in all_data.items():
            engine.feed_data(source_name, data)
    """

    def __init__(self):
        self.opensky = None  # Imported separately to avoid circular import
        self.celestrak = CelestrakFeed()
        self.usgs = USGSEarthquakeFeed()
        self.gdelt = GDELTFeed()
        self.weather = OpenWeatherFeed()
        self.nasa_firms = NASAFirmsFeed()

    def collect_all(self, bbox: tuple = None,
                    weather_location: tuple = None) -> dict:
        """
        Pull data from all available free sources.

        Parameters:
        - bbox: Bounding box for aircraft data (lat_min, lat_max, lon_min, lon_max)
        - weather_location: (latitude, longitude) for weather data

        Returns a dictionary where each key is a data source name
        and each value is the data from that source.
        """
        results = {}

        # 1. OpenSky flights
        from data_feeds.opensky_feed import OpenSkyFeed
        try:
            opensky = OpenSkyFeed()
            flight_data = opensky.get_live_aircraft(bbox=bbox)
            results["air_traffic"] = flight_data

            # Also detect anomalies
            if flight_data.get("states"):
                anomalies = opensky.detect_anomalies(flight_data["states"])
                results["air_anomalies"] = {
                    "anomalies": anomalies,
                    "count": len(anomalies),
                }
        except Exception as e:
            results["air_traffic"] = {"error": str(e), "states": []}

        # 2. Satellite data
        try:
            sat_data = self.celestrak.get_satellites("active")
            results["satellite_orbits"] = sat_data
        except Exception as e:
            results["satellite_orbits"] = {"error": str(e)}

        # 3. Earthquakes
        try:
            quake_data = self.usgs.get_recent_earthquakes()
            results["earthquakes"] = quake_data
        except Exception as e:
            results["earthquakes"] = {"error": str(e)}

        # 4. Global news events
        try:
            news_data = self.gdelt.get_recent_events(
                query="military conflict threat", max_records=25
            )
            results["global_news"] = news_data
        except Exception as e:
            results["global_news"] = {"error": str(e)}

        # 5. Weather (if location provided)
        if weather_location:
            try:
                lat, lon = weather_location
                weather_data = self.weather.get_weather(lat, lon)
                results["weather"] = weather_data
            except Exception as e:
                results["weather"] = {"error": str(e)}

        # 6. Fires (if NASA key available)
        if NASA_FIRMS_API_KEY:
            try:
                fire_data = self.nasa_firms.get_active_fires()
                results["fires"] = fire_data
            except Exception as e:
                results["fires"] = {"error": str(e)}

        return results
