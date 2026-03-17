"""
DEMO DATA — Used when live APIs can't connect.
================================================
This file contains realistic sample data so the dashboard
ALWAYS shows something, even without internet.

When live APIs work, the system uses real data.
When they fail, it falls back to this demo data.
The dashboard clearly labels which mode it's in.
"""

import random
import math
from datetime import datetime, timezone


def generate_demo_aircraft(count=150):
    """
    Generate realistic demo aircraft spread around the world.
    Each aircraft has position, altitude, speed, heading, callsign.
    Some have anomalies (emergency squawks, low altitude, high speed).
    """
    airlines = [
        ("AI", "India"), ("BA", "United Kingdom"), ("LH", "Germany"),
        ("EK", "United Arab Emirates"), ("SQ", "Singapore"),
        ("QF", "Australia"), ("AA", "United States"), ("AF", "France"),
        ("JL", "Japan"), ("CA", "China"), ("TK", "Turkey"),
        ("SU", "Russia"), ("KE", "South Korea"), ("TG", "Thailand"),
        ("9W", "India"), ("UK", "India"), ("6E", "India"),
        ("SG", "India"), ("G8", "India"),
    ]

    # Flight corridors — realistic routes
    corridors = [
        # India internal
        {"lat_range": (8, 35), "lon_range": (68, 97), "weight": 40},
        # India to Middle East
        {"lat_range": (12, 30), "lon_range": (45, 80), "weight": 15},
        # India to Southeast Asia
        {"lat_range": (0, 25), "lon_range": (75, 120), "weight": 15},
        # Europe
        {"lat_range": (35, 60), "lon_range": (-10, 40), "weight": 15},
        # North America
        {"lat_range": (25, 50), "lon_range": (-120, -70), "weight": 10},
        # Global scattered
        {"lat_range": (-40, 60), "lon_range": (-180, 180), "weight": 5},
    ]

    aircraft_list = []
    for i in range(count):
        # Pick a corridor based on weight
        total_weight = sum(c["weight"] for c in corridors)
        r = random.uniform(0, total_weight)
        cumulative = 0
        corridor = corridors[0]
        for c in corridors:
            cumulative += c["weight"]
            if r <= cumulative:
                corridor = c
                break

        lat = random.uniform(*corridor["lat_range"])
        lon = random.uniform(*corridor["lon_range"])
        airline_code, country = random.choice(airlines)
        flight_num = random.randint(100, 9999)
        callsign = f"{airline_code}{flight_num}"

        altitude = random.choice([
            random.randint(9000, 12000),   # Cruising
            random.randint(3000, 8000),    # Climbing/descending
            random.randint(500, 2500),     # Approach
        ])
        speed = random.uniform(100, 280)  # m/s
        heading = random.uniform(0, 360)
        vertical_rate = random.uniform(-5, 5)
        squawk = "1200"  # Normal

        # Add some anomalies (about 3% of aircraft)
        if random.random() < 0.01:
            squawk = random.choice(["7500", "7600", "7700"])
        elif random.random() < 0.02:
            altitude = random.randint(50, 250)  # Very low
        elif random.random() < 0.02:
            speed = random.uniform(310, 450)  # Military speed

        icao24 = format(random.randint(0, 0xFFFFFF), '06x')

        aircraft_list.append({
            "icao24": icao24,
            "callsign": callsign,
            "origin_country": country,
            "latitude": round(lat, 4),
            "longitude": round(lon, 4),
            "baro_altitude": altitude,
            "on_ground": False,
            "velocity": round(speed, 1),
            "true_track": round(heading, 1),
            "vertical_rate": round(vertical_rate, 1),
            "squawk": squawk,
            "time_position": None,
            "last_contact": None,
            "sensors": None,
            "geo_altitude": altitude,
            "spi": False,
            "position_source": 0,
        })

    return {
        "states": aircraft_list,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "count": len(aircraft_list),
    }


def generate_demo_earthquakes():
    """Generate realistic earthquake data around the world."""
    quake_zones = [
        # Ring of Fire
        (35.6, 139.7, "50km E of Tokyo, Japan"),
        (-8.5, 115.3, "80km S of Bali, Indonesia"),
        (37.5, 141.9, "100km E of Sendai, Japan"),
        (-33.4, -70.6, "60km S of Santiago, Chile"),
        (19.4, -155.3, "30km SW of Hilo, Hawaii"),
        # Mediterranean
        (38.3, 22.1, "40km W of Athens, Greece"),
        (37.9, 29.1, "90km E of Izmir, Turkey"),
        # South Asia
        (28.2, 84.7, "100km NW of Kathmandu, Nepal"),
        (34.5, 73.5, "70km N of Islamabad, Pakistan"),
        (25.0, 97.0, "Myanmar-China border region"),
    ]

    earthquakes = []
    # Pick 3-7 random earthquakes
    for _ in range(random.randint(3, 7)):
        lat, lon, place = random.choice(quake_zones)
        lat += random.uniform(-2, 2)
        lon += random.uniform(-2, 2)
        mag = round(random.uniform(1.5, 6.2), 1)
        depth = round(random.uniform(2, 50), 1)

        earthquakes.append({
            "magnitude": mag,
            "place": place,
            "latitude": round(lat, 2),
            "longitude": round(lon, 2),
            "depth_km": depth,
            "tsunami_warning": mag >= 6.0,
            "significance": int(mag * 100),
            "time": int(datetime.now(timezone.utc).timestamp() * 1000),
        })

    return {
        "earthquakes": earthquakes,
        "count": len(earthquakes),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def generate_demo_news():
    """Generate realistic defence-related news headlines."""
    headlines = [
        "Military exercises reported near Indo-Pacific border region",
        "NATO forces conduct joint naval drill in Mediterranean Sea",
        "Border tensions escalate between rival nations in Central Asia",
        "Satellite imagery shows new military installations in disputed territory",
        "Emergency evacuation ordered after chemical plant explosion",
        "Coast guard intercepts unidentified vessel in exclusive economic zone",
        "Air force scrambles jets after airspace violation reported",
        "UN peacekeeping forces deployed to conflict zone",
        "Cyber attack targets critical infrastructure in European capital",
        "Military convoy spotted moving towards disputed border region",
        "Submarine activity detected in strategic shipping lane",
        "Defence minister announces increased military readiness",
        "Missile test conducted by regional power draws international criticism",
        "Humanitarian corridor established in conflict-affected province",
        "Intelligence agencies warn of increased threat level",
        "Naval blockade threatens international shipping routes",
        "Special forces operation reported in remote mountain region",
        "Drone surveillance footage reveals military buildup near border",
        "Emergency summit called to address escalating regional tensions",
        "Arms shipment intercepted by coast guard patrol",
    ]

    sources = [
        "reuters.com", "bbc.co.uk", "aljazeera.com", "ndtv.com",
        "cnn.com", "theguardian.com", "hindustantimes.com",
        "timesofindia.indiatimes.com", "france24.com",
    ]

    articles = []
    selected = random.sample(headlines, min(10, len(headlines)))
    for title in selected:
        articles.append({
            "title": title,
            "source": random.choice(sources),
            "url": "",
            "date": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S"),
            "language": "English",
            "source_country": random.choice([
                "United States", "United Kingdom", "India",
                "France", "Qatar",
            ]),
        })

    return {
        "articles": articles,
        "count": len(articles),
        "query": "military conflict threat",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def get_all_demo_data():
    """
    Get a complete set of demo data for all feeds.
    Used when live APIs can't connect.
    """
    aircraft_data = generate_demo_aircraft(150)

    # Detect anomalies in demo data
    from data_feeds.opensky_feed import OpenSkyFeed
    opensky = OpenSkyFeed()
    anomalies = opensky.detect_anomalies(aircraft_data["states"])

    return {
        "air_traffic": aircraft_data,
        "air_anomalies": {
            "anomalies": anomalies,
            "count": len(anomalies),
        },
        "earthquakes": generate_demo_earthquakes(),
        "global_news": generate_demo_news(),
    }
