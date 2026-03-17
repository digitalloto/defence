"""
LAYER 5 — DASHBOARD SERVER (with Continuous Agentic Simulation)
================================================================
This is the server that runs everything.

What it does:
1. Starts a web server for the 3D globe dashboard
2. Runs a CONTINUOUS simulation loop in the background
   (like MiroFish — agents keep running, not just once)
3. Pulls live data every 60 seconds
4. If live APIs fail, uses demo data (dashboard always works)
5. Updates the dashboard in real-time

How to run:
    cd /path/to/defence
    python3 -m aimcrs.dashboard.server

Then open http://localhost:8080 in your browser.

WORKS IN ANY BROWSER: Chrome, Firefox, Safari, Edge, Opera.
WORKS ON ANY DEVICE: Laptop, desktop, tablet, phone.
"""

import sys
import os
import json
import asyncio
import threading
import time
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Make sure Python can find our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.simulation_engine import SimulationEngine
from agents.defence_agent import create_default_agent_team
from data_feeds.opensky_feed import OpenSkyFeed
from data_feeds.other_feeds import (
    USGSEarthquakeFeed,
    GDELTFeed,
    CelestrakFeed,
)
from data_feeds.demo_data import get_all_demo_data
from defence_layer.threat_engine import ThreatEngine
from config.settings import REPORTS_DIR, REFRESH_INTERVAL_SECONDS


# ─────────────────────────────────────────────
# GLOBAL STATE
# Shared between the web server and simulation.
# The web server READS this.
# The simulation loop WRITES to this.
# ─────────────────────────────────────────────

_engine_state = {
    "latest_report": None,
    "latest_aircraft": [],
    "latest_earthquakes": [],
    "latest_news": [],
    "latest_anomalies": [],
    "simulation_status": "IDLE",
    "round": 0,
    "cycle": 0,
    "data_mode": "STARTING",  # "LIVE" or "DEMO"
    "data_sources_active": [],
    "last_data_pull": "",
    "total_actions": 0,
}


# ─────────────────────────────────────────────
# WEB SERVER
# ─────────────────────────────────────────────

class DashboardHandler(SimpleHTTPRequestHandler):
    """
    Handles HTTP requests for the dashboard.

    Routes:
    - GET /               Serves the HTML dashboard page
    - GET /api/status     Current simulation status + all metadata
    - GET /api/report     Latest threat report with scenarios
    - GET /api/aircraft   Latest aircraft positions (for globe dots)
    - GET /api/earthquakes Latest earthquake data (for globe circles)
    - GET /api/news       Latest news events
    - GET /api/anomalies  Detected anomalies
    """

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            self._serve_dashboard()
        elif path == "/api/status":
            self._json_response({
                "simulation_status": _engine_state["simulation_status"],
                "round": _engine_state["round"],
                "cycle": _engine_state["cycle"],
                "data_mode": _engine_state["data_mode"],
                "data_sources_active": _engine_state["data_sources_active"],
                "last_data_pull": _engine_state["last_data_pull"],
                "total_actions": _engine_state["total_actions"],
                "aircraft_count": len(_engine_state["latest_aircraft"]),
                "anomaly_count": len(_engine_state["latest_anomalies"]),
                "earthquake_count": len(_engine_state["latest_earthquakes"]),
                "news_count": len(_engine_state["latest_news"]),
            })
        elif path == "/api/report":
            self._json_response(
                _engine_state.get("latest_report") or
                {"message": "Simulation starting... first report in ~10 seconds."}
            )
        elif path == "/api/aircraft":
            self._json_response({
                "aircraft": _engine_state.get("latest_aircraft", []),
                "count": len(_engine_state.get("latest_aircraft", [])),
            })
        elif path == "/api/earthquakes":
            self._json_response({
                "earthquakes": _engine_state.get("latest_earthquakes", []),
            })
        elif path == "/api/news":
            self._json_response({
                "articles": _engine_state.get("latest_news", []),
            })
        elif path == "/api/anomalies":
            self._json_response({
                "anomalies": _engine_state.get("latest_anomalies", []),
            })
        else:
            self.send_error(404, "Not found")

    def _serve_dashboard(self):
        """Serve the main HTML dashboard page."""
        dashboard_path = Path(__file__).parent / "index.html"
        if dashboard_path.exists():
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(dashboard_path.read_bytes())
        else:
            self.send_response(500)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Dashboard HTML file not found.")

    def _json_response(self, data):
        """Send a JSON response."""
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(
            json.dumps(data, default=str).encode("utf-8")
        )

    def log_message(self, format, *args):
        """Suppress noisy HTTP logs."""
        pass


# ─────────────────────────────────────────────
# DATA PULLING — Live APIs with Demo Fallback
# ─────────────────────────────────────────────

def pull_live_data():
    """
    Try to pull from live APIs.
    If ANY fail, fall back to demo data for those feeds.
    Returns a dict of all data + what mode we're in.
    """
    global _engine_state
    live_sources = []
    demo_sources = []

    from datetime import datetime, timezone
    _engine_state["last_data_pull"] = datetime.now(timezone.utc).isoformat()

    # ── Aircraft ──
    try:
        opensky = OpenSkyFeed()
        flight_data = opensky.get_live_aircraft()
        states = flight_data.get("states", [])
        if states and not flight_data.get("error"):
            _engine_state["latest_aircraft"] = states
            anomalies = opensky.detect_anomalies(states)
            _engine_state["latest_anomalies"] = anomalies
            live_sources.append("OpenSky Aircraft")
        else:
            raise Exception(flight_data.get("error", "No data"))
    except Exception:
        demo = get_all_demo_data()
        _engine_state["latest_aircraft"] = demo["air_traffic"]["states"]
        _engine_state["latest_anomalies"] = demo["air_anomalies"]["anomalies"]
        demo_sources.append("Aircraft (DEMO)")

    # ── Earthquakes ──
    try:
        usgs = USGSEarthquakeFeed()
        quake_data = usgs.get_recent_earthquakes()
        quakes = quake_data.get("earthquakes", [])
        if quakes and not quake_data.get("error"):
            _engine_state["latest_earthquakes"] = quakes
            live_sources.append("USGS Earthquakes")
        else:
            raise Exception(quake_data.get("error", "No data"))
    except Exception:
        demo = get_all_demo_data()
        _engine_state["latest_earthquakes"] = demo["earthquakes"]["earthquakes"]
        demo_sources.append("Earthquakes (DEMO)")

    # ── News ──
    try:
        gdelt = GDELTFeed()
        news_data = gdelt.get_recent_events(
            query="military conflict threat", max_records=10
        )
        articles = news_data.get("articles", [])
        if articles and not news_data.get("error"):
            _engine_state["latest_news"] = articles
            live_sources.append("GDELT News")
        else:
            raise Exception(news_data.get("error", "No data"))
    except Exception:
        demo = get_all_demo_data()
        _engine_state["latest_news"] = demo["global_news"]["articles"]
        demo_sources.append("News (DEMO)")

    # Set data mode
    _engine_state["data_sources_active"] = live_sources + demo_sources
    if live_sources and not demo_sources:
        _engine_state["data_mode"] = "LIVE"
    elif demo_sources and not live_sources:
        _engine_state["data_mode"] = "DEMO"
    else:
        _engine_state["data_mode"] = "MIXED"


# ─────────────────────────────────────────────
# CONTINUOUS AGENTIC SIMULATION LOOP
# This is the MiroFish-style continuous engine.
# It never stops — runs cycle after cycle.
# ─────────────────────────────────────────────

async def run_continuous_simulation():
    """
    Run the simulation CONTINUOUSLY in a loop.

    Like MiroFish:
    - Creates agents that persist across cycles
    - Agents keep their memory from previous cycles
    - New data is fed in every cycle
    - Reports update every cycle
    - The loop runs until the server is stopped

    Each CYCLE:
    1. Pull fresh data (live or demo)
    2. Feed data into the engine
    3. Run 5 rounds of agent simulation
    4. Generate threat report
    5. Wait 60 seconds
    6. Repeat from step 1
    """
    global _engine_state

    cycle = 0
    # Create agents ONCE — they persist across cycles (like MiroFish)
    agents = create_default_agent_team()
    threat_engine = ThreatEngine()

    print("  [AGENTS] 8 defence agents spawned:")
    for a in agents:
        print(f"    - {a.name} ({a.role_key})")
    print()

    while True:
        cycle += 1
        _engine_state["cycle"] = cycle
        _engine_state["simulation_status"] = "PULLING_DATA"
        print(f"  [CYCLE {cycle}] Pulling data...")

        # Step 1: Pull fresh data
        pull_live_data()
        mode = _engine_state["data_mode"]
        print(f"    Data mode: {mode}")
        print(f"    Sources: {', '.join(_engine_state['data_sources_active'])}")

        # Step 2: Create a new simulation for this cycle
        engine = SimulationEngine()
        state = engine.create_simulation(agent_count=len(agents))
        engine.register_agents(agents)

        # Step 3: Feed data into the engine
        if _engine_state["latest_aircraft"]:
            engine.feed_data("air_traffic", {
                "states": _engine_state["latest_aircraft"]
            })
        if _engine_state["latest_earthquakes"]:
            engine.feed_data("earthquakes", {
                "features": [
                    {
                        "properties": {
                            "mag": q.get("magnitude", 0),
                            "place": q.get("place", "Unknown"),
                        },
                        "geometry": {
                            "coordinates": [
                                q.get("longitude", 0),
                                q.get("latitude", 0),
                                q.get("depth_km", 0),
                            ]
                        },
                    }
                    for q in _engine_state["latest_earthquakes"]
                ]
            })
        if _engine_state["latest_news"]:
            engine.feed_data("global_news", {
                "articles": _engine_state["latest_news"]
            })

        # Step 4: Run the simulation rounds
        _engine_state["simulation_status"] = "RUNNING"

        def on_round(round_num, actions):
            _engine_state["round"] = round_num
            _engine_state["total_actions"] += len(actions)

            # Generate threat report after each round
            report = threat_engine.analyse_round(actions, round_num)
            _engine_state["latest_report"] = {
                "report_id": report.report_id,
                "generated_at": report.generated_at,
                "overall_threat_level": report.overall_threat_level,
                "scenarios": report.scenarios,
                "agent_count": report.agent_count,
                "round": report.simulation_round,
                "cycle": cycle,
                "data_mode": _engine_state["data_mode"],
            }

        await engine.run_simulation(on_round_complete=on_round)
        engine.close()

        # Print summary
        report = _engine_state.get("latest_report", {})
        level = report.get("overall_threat_level", "?")
        scenarios = report.get("scenarios", [])
        print(f"    Threat level: {level}")
        print(f"    Scenarios: {len(scenarios)}")
        if scenarios:
            top = scenarios[0]
            if isinstance(top, dict):
                print(f"    Top threat: {top.get('title', '?')} "
                      f"({top.get('combined_score', 0):.0%})")
        print(f"    Agent memory grows — agents remember across cycles")
        print()

        _engine_state["simulation_status"] = "WAITING"
        print(f"  [CYCLE {cycle}] Complete. Next cycle in "
              f"{REFRESH_INTERVAL_SECONDS} seconds...")
        print()

        # Step 5: Wait before next cycle
        # (during this time the dashboard keeps serving the latest data)
        await asyncio.sleep(REFRESH_INTERVAL_SECONDS)


def start_simulation_thread():
    """Start the continuous simulation in a background thread."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_continuous_simulation())


# ─────────────────────────────────────────────
# MAIN — Start everything
# ─────────────────────────────────────────────

def main():
    """Start the dashboard server and continuous simulation."""
    port = int(os.environ.get("PORT", 8080))

    print(f"""
================================================================
   AIMCRS APINDRA — Defence Intelligence Engine
================================================================

   Dashboard: http://localhost:{port}
   (or http://0.0.0.0:{port})

   Works in ANY browser: Chrome, Firefox, Safari, Edge

   What's happening:
   - 8 defence agents are running continuously
   - Agents keep memory across cycles (like MiroFish)
   - New data pulled every {REFRESH_INTERVAL_SECONDS} seconds
   - If live APIs fail, demo data is used instead
   - Dashboard auto-refreshes in your browser

   Press Ctrl+C to stop
================================================================
    """)

    # Start the continuous simulation in background
    sim_thread = threading.Thread(
        target=start_simulation_thread, daemon=True
    )
    sim_thread.start()

    # Start web server (this blocks until Ctrl+C)
    server = HTTPServer(("0.0.0.0", port), DashboardHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Server stopped by operator.")
        server.server_close()


if __name__ == "__main__":
    main()
