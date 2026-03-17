"""
LAYER 3 — DATA FEED: OpenSky Network (Live Aircraft Tracking)
==============================================================
This pulls LIVE aircraft position data from the OpenSky Network.

What you get:
- Aircraft position (latitude, longitude)
- Altitude in metres
- Speed in metres per second
- Heading (direction of travel)
- Callsign (flight number like "BA123")
- Whether it's on the ground
- Squawk code (emergency codes: 7500=hijack, 7600=radio fail, 7700=emergency)
- Aircraft type category

⚠️ FREE TIER LIMITS:
- Anonymous: 1 request every 10 seconds, 400/day
- With free account: 1 request every 5 seconds, 4000/day
- Sign up free at: https://opensky-network.org/index.php/-en/data/register

⚠️ IMPORTANT: As of March 2026, OpenSky requires OAuth2 for authenticated
access. Anonymous access still works but with lower limits.
"""

import requests
import time
import json
from datetime import datetime, timezone
from config.settings import (
    OPENSKY_API_URL,
    OPENSKY_USERNAME,
    OPENSKY_PASSWORD,
)


class OpenSkyFeed:
    """
    Pulls live aircraft data from OpenSky Network.

    How to use:
        feed = OpenSkyFeed()
        data = feed.get_live_aircraft()
        # data is a list of dictionaries, one per aircraft
    """

    def __init__(self, username: str = "", password: str = ""):
        self.base_url = OPENSKY_API_URL
        self.username = username or OPENSKY_USERNAME
        self.password = password or OPENSKY_PASSWORD
        self.last_request_time = 0
        self.min_interval = 10  # seconds between requests (anonymous)

        if self.username and self.password:
            self.min_interval = 5  # authenticated users get faster access

    def _rate_limit(self):
        """Wait if needed to respect API rate limits."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_interval:
            wait = self.min_interval - elapsed
            time.sleep(wait)
        self.last_request_time = time.time()

    def get_live_aircraft(self, bbox: tuple = None) -> dict:
        """
        Get all aircraft currently in the sky.

        Parameters:
        - bbox: Optional bounding box to filter by area.
          Format: (min_latitude, max_latitude, min_longitude, max_longitude)
          Example for India: (6.0, 37.0, 68.0, 97.0)
          Example for all of Asia: (0.0, 55.0, 60.0, 150.0)
          Leave empty for worldwide.

        Returns a dictionary with:
        - "states": list of aircraft, each as a dictionary
        - "timestamp": when this data was captured
        - "count": how many aircraft
        """
        self._rate_limit()

        url = f"{self.base_url}/states/all"
        params = {}

        if bbox:
            min_lat, max_lat, min_lon, max_lon = bbox
            params["lamin"] = min_lat
            params["lamax"] = max_lat
            params["lomin"] = min_lon
            params["lomax"] = max_lon

        try:
            auth = None
            if self.username and self.password:
                auth = (self.username, self.password)

            response = requests.get(
                url, params=params, auth=auth, timeout=30
            )

            if response.status_code == 200:
                raw = response.json()
                return self._parse_states(raw)
            elif response.status_code == 429:
                return {
                    "states": [],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "count": 0,
                    "error": "Rate limited — too many requests. Wait 10 seconds.",
                }
            else:
                return {
                    "states": [],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "count": 0,
                    "error": f"HTTP {response.status_code}: {response.text[:200]}",
                }

        except requests.exceptions.Timeout:
            return {
                "states": [],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "count": 0,
                "error": "Request timed out. OpenSky may be slow.",
            }
        except requests.exceptions.ConnectionError:
            return {
                "states": [],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "count": 0,
                "error": "Cannot connect to OpenSky. Check internet.",
            }
        except Exception as e:
            return {
                "states": [],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "count": 0,
                "error": f"Unexpected error: {str(e)}",
            }

    def get_aircraft_by_id(self, icao24: str) -> dict:
        """
        Track a specific aircraft by its ICAO24 address.
        The ICAO24 is a unique hex code for each aircraft transponder.
        """
        self._rate_limit()

        url = f"{self.base_url}/states/all"
        params = {"icao24": icao24.lower()}

        try:
            response = requests.get(url, params=params, timeout=30)
            if response.status_code == 200:
                return self._parse_states(response.json())
            return {"states": [], "error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"states": [], "error": str(e)}

    def detect_anomalies(self, states: list) -> list:
        """
        Scan aircraft data for anomalies that might indicate threats.

        Checks for:
        1. Emergency squawk codes (7500, 7600, 7700)
        2. Very low altitude (under 300m) when not on ground
        3. Very high speed (over 300 m/s ≈ military jet)
        4. No callsign (transponder on but no identification)
        5. Unusual vertical rate (rapid climb/descent)

        Returns a list of anomaly dictionaries.
        """
        anomalies = []

        for ac in states:
            callsign = ac.get("callsign", "UNKNOWN").strip()
            squawk = ac.get("squawk", "")
            altitude = ac.get("baro_altitude", 0) or 0
            speed = ac.get("velocity", 0) or 0
            on_ground = ac.get("on_ground", False)
            vertical_rate = ac.get("vertical_rate", 0) or 0

            # Emergency squawk codes
            if squawk in ("7500", "7600", "7700"):
                meanings = {
                    "7500": "HIJACK IN PROGRESS",
                    "7600": "RADIO FAILURE",
                    "7700": "GENERAL EMERGENCY",
                }
                anomalies.append({
                    "type": "EMERGENCY_SQUAWK",
                    "severity": "CRITICAL",
                    "aircraft": callsign,
                    "icao24": ac.get("icao24", ""),
                    "detail": f"Squawk {squawk}: {meanings[squawk]}",
                    "position": {
                        "lat": ac.get("latitude"),
                        "lon": ac.get("longitude"),
                    },
                    "altitude": altitude,
                })

            # Very low altitude (not on ground)
            if 0 < altitude < 300 and not on_ground:
                anomalies.append({
                    "type": "LOW_ALTITUDE",
                    "severity": "HIGH",
                    "aircraft": callsign,
                    "icao24": ac.get("icao24", ""),
                    "detail": f"Flying at {altitude}m — abnormally low",
                    "position": {
                        "lat": ac.get("latitude"),
                        "lon": ac.get("longitude"),
                    },
                    "altitude": altitude,
                })

            # High speed (possible military)
            if speed > 300:
                anomalies.append({
                    "type": "HIGH_SPEED",
                    "severity": "MEDIUM",
                    "aircraft": callsign,
                    "icao24": ac.get("icao24", ""),
                    "detail": f"Speed {speed:.0f} m/s ({speed * 1.944:.0f} knots)",
                    "position": {
                        "lat": ac.get("latitude"),
                        "lon": ac.get("longitude"),
                    },
                    "altitude": altitude,
                })

            # No callsign
            if not callsign or callsign == "UNKNOWN":
                anomalies.append({
                    "type": "NO_CALLSIGN",
                    "severity": "LOW",
                    "aircraft": "UNIDENTIFIED",
                    "icao24": ac.get("icao24", ""),
                    "detail": "Transponder active but no callsign broadcast",
                    "position": {
                        "lat": ac.get("latitude"),
                        "lon": ac.get("longitude"),
                    },
                    "altitude": altitude,
                })

            # Rapid vertical movement
            if abs(vertical_rate) > 30:  # 30 m/s = ~6000 ft/min
                direction = "CLIMBING" if vertical_rate > 0 else "DESCENDING"
                anomalies.append({
                    "type": "RAPID_VERTICAL",
                    "severity": "MEDIUM",
                    "aircraft": callsign,
                    "icao24": ac.get("icao24", ""),
                    "detail": (
                        f"{direction} at {abs(vertical_rate):.0f} m/s "
                        f"({abs(vertical_rate) * 196.85:.0f} ft/min)"
                    ),
                    "position": {
                        "lat": ac.get("latitude"),
                        "lon": ac.get("longitude"),
                    },
                    "altitude": altitude,
                })

        return anomalies

    def _parse_states(self, raw_data: dict) -> dict:
        """
        Convert OpenSky's raw array format into readable dictionaries.

        OpenSky returns data as arrays like [icao24, callsign, country, ...].
        We convert each to a labelled dictionary for easy reading.
        """
        timestamp = raw_data.get("time", 0)
        raw_states = raw_data.get("states", []) or []

        parsed = []
        for state in raw_states:
            if len(state) < 17:
                continue

            parsed.append({
                "icao24": state[0],
                "callsign": (state[1] or "").strip(),
                "origin_country": state[2],
                "time_position": state[3],
                "last_contact": state[4],
                "longitude": state[5],
                "latitude": state[6],
                "baro_altitude": state[7],
                "on_ground": state[8],
                "velocity": state[9],
                "true_track": state[10],
                "vertical_rate": state[11],
                "sensors": state[12],
                "geo_altitude": state[13],
                "squawk": state[14],
                "spi": state[15],
                "position_source": state[16],
            })

        return {
            "states": parsed,
            "timestamp": datetime.fromtimestamp(
                timestamp, tz=timezone.utc
            ).isoformat() if timestamp else datetime.now(timezone.utc).isoformat(),
            "count": len(parsed),
        }
