"""
LAYER 5 — DASHBOARD SERVER
============================
A simple web server that serves the 3D globe dashboard.

How to run:
    cd /home/user/defence
    python3 -m aimcrs.dashboard.server

Then open http://localhost:8080 in your browser.

What it does:
- Serves the HTML dashboard page
- Provides API endpoints for the dashboard to pull data from
- Runs the simulation in the background and sends updates

⚠️ This uses Python's built-in HTTP server — no extra packages needed.
"""

import sys
import os
import json
import asyncio
import threading
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
from defence_layer.threat_engine import ThreatEngine
from config.settings import REPORTS_DIR


# Global state — shared between web server and simulation
_engine_state = {
    "latest_report": None,
    "latest_aircraft": [],
    "latest_earthquakes": [],
    "latest_news": [],
    "latest_anomalies": [],
    "simulation_status": "IDLE",
    "round": 0,
}


class DashboardHandler(SimpleHTTPRequestHandler):
    """
    Handles HTTP requests for the dashboard.

    Routes:
    - GET /             → Serves the HTML dashboard page
    - GET /api/status   → Current simulation status
    - GET /api/report   → Latest threat report
    - GET /api/aircraft → Latest aircraft positions
    - GET /api/earthquakes → Latest earthquake data
    - GET /api/news     → Latest news events
    - GET /api/anomalies → Detected anomalies
    """

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            self._serve_dashboard()
        elif path == "/api/status":
            self._json_response(_engine_state)
        elif path == "/api/report":
            self._json_response(
                _engine_state.get("latest_report") or
                {"message": "No report yet. Run the simulation first."}
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
        """Suppress default logging to keep console clean."""
        pass


def pull_live_data():
    """Pull fresh data from all sources and update global state."""
    global _engine_state

    # Aircraft
    try:
        opensky = OpenSkyFeed()
        flight_data = opensky.get_live_aircraft()
        states = flight_data.get("states", [])
        _engine_state["latest_aircraft"] = states

        anomalies = opensky.detect_anomalies(states)
        _engine_state["latest_anomalies"] = anomalies
    except Exception:
        pass

    # Earthquakes
    try:
        usgs = USGSEarthquakeFeed()
        quake_data = usgs.get_recent_earthquakes()
        _engine_state["latest_earthquakes"] = quake_data.get(
            "earthquakes", []
        )
    except Exception:
        pass

    # News
    try:
        gdelt = GDELTFeed()
        news_data = gdelt.get_recent_events(
            query="military conflict threat", max_records=10
        )
        _engine_state["latest_news"] = news_data.get("articles", [])
    except Exception:
        pass


async def run_background_simulation():
    """Run the simulation and update the dashboard data."""
    global _engine_state

    _engine_state["simulation_status"] = "STARTING"

    engine = SimulationEngine()
    state = engine.create_simulation(agent_count=8)
    agents = create_default_agent_team()
    engine.register_agents(agents)

    _engine_state["simulation_status"] = "PULLING_DATA"
    pull_live_data()

    # Feed data into engine
    if _engine_state["latest_aircraft"]:
        engine.feed_data("air_traffic", {
            "states": _engine_state["latest_aircraft"]
        })
    if _engine_state["latest_earthquakes"]:
        engine.feed_data("earthquakes", {
            "features": [
                {
                    "properties": {"mag": q["magnitude"], "place": q["place"]},
                    "geometry": {
                        "coordinates": [
                            q["longitude"], q["latitude"], q["depth_km"]
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

    _engine_state["simulation_status"] = "RUNNING"
    threat_engine = ThreatEngine()

    def on_round(round_num, actions):
        _engine_state["round"] = round_num
        report = threat_engine.analyse_round(actions, round_num)
        _engine_state["latest_report"] = {
            "report_id": report.report_id,
            "generated_at": report.generated_at,
            "overall_threat_level": report.overall_threat_level,
            "scenarios": report.scenarios,
            "agent_count": report.agent_count,
            "round": report.simulation_round,
        }

    await engine.run_simulation(on_round_complete=on_round)

    _engine_state["simulation_status"] = "COMPLETED"
    engine.close()


def start_simulation_thread():
    """Start the simulation in a background thread."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_background_simulation())


def main():
    """Start the dashboard server."""
    port = 8080

    print(f"""
╔══════════════════════════════════════════════════╗
║   AIMCRS APINDRA — Dashboard Server              ║
║                                                  ║
║   Open in browser: http://localhost:{port}         ║
║                                                  ║
║   Press Ctrl+C to stop                           ║
╚══════════════════════════════════════════════════╝
    """)

    # Start simulation in background
    sim_thread = threading.Thread(
        target=start_simulation_thread, daemon=True
    )
    sim_thread.start()
    print("  Simulation started in background...")

    # Start web server
    server = HTTPServer(("0.0.0.0", port), DashboardHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.server_close()


if __name__ == "__main__":
    main()
