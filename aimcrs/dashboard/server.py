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
import cgi
import io
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timezone

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
    # ── New: Operator Console, God Mode, File Upload ──
    "god_mode": False,
    "god_mode_overrides": {},      # scenario_id -> {score, notes, dismissed}
    "paused_agents": set(),        # agent role_keys that are paused
    "operator_messages": [],       # chat history
    "uploaded_files": [],          # uploaded intel files metadata
    "manual_threat_level": None,   # god mode manual override of overall threat
}

# Directory for uploaded intel files
UPLOAD_DIR = Path(__file__).parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)


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
                "god_mode": _engine_state["god_mode"],
                "paused_agents": list(_engine_state["paused_agents"]),
                "manual_threat_level": _engine_state["manual_threat_level"],
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
        elif path == "/api/chat/history":
            self._json_response({
                "messages": _engine_state["operator_messages"][-100:],
            })
        elif path == "/api/files":
            self._json_response({
                "files": _engine_state["uploaded_files"],
            })
        elif path == "/api/godmode":
            self._json_response({
                "god_mode": _engine_state["god_mode"],
                "paused_agents": list(_engine_state["paused_agents"]),
                "overrides": {k: v for k, v in _engine_state["god_mode_overrides"].items()},
                "manual_threat_level": _engine_state["manual_threat_level"],
            })
        else:
            self.send_error(404, "Not found")

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/chat":
            self._handle_chat()
        elif path == "/api/godmode/toggle":
            self._handle_godmode_toggle()
        elif path == "/api/godmode/override":
            self._handle_godmode_override()
        elif path == "/api/godmode/agent":
            self._handle_godmode_agent()
        elif path == "/api/godmode/threat-level":
            self._handle_godmode_threat_level()
        elif path == "/api/upload":
            self._handle_file_upload()
        else:
            self.send_error(404, "Not found")

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _read_json_body(self):
        """Read and parse JSON from request body."""
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        body = self.rfile.read(length)
        return json.loads(body.decode("utf-8"))

    # ── CHAT ──

    def _handle_chat(self):
        """Operator sends a message, gets an AI-style response from agents."""
        data = self._read_json_body()
        message = data.get("message", "").strip()
        if not message:
            self._json_response({"error": "Empty message"})
            return

        now = datetime.now(timezone.utc).isoformat()

        # Store operator message
        _engine_state["operator_messages"].append({
            "role": "operator",
            "text": message,
            "time": now,
        })

        # Generate agent response based on current state
        response = self._generate_agent_response(message)

        _engine_state["operator_messages"].append({
            "role": "system",
            "text": response,
            "time": now,
        })

        self._json_response({
            "reply": response,
            "time": now,
        })

    def _generate_agent_response(self, question):
        """
        Generate a response to operator questions using current system state.
        Uses rule-based logic (no LLM needed).
        """
        q = question.lower()
        report = _engine_state.get("latest_report") or {}
        scenarios = report.get("scenarios", [])
        level = report.get("overall_threat_level", "UNKNOWN")
        cycle = _engine_state.get("cycle", 0)
        mode = _engine_state.get("data_mode", "STARTING")
        aircraft_count = len(_engine_state.get("latest_aircraft", []))
        quake_count = len(_engine_state.get("latest_earthquakes", []))
        anomaly_count = len(_engine_state.get("latest_anomalies", []))
        news_count = len(_engine_state.get("latest_news", []))
        files = _engine_state.get("uploaded_files", [])

        # Threat status questions
        if any(kw in q for kw in ["threat", "status", "level", "how bad", "situation"]):
            if scenarios:
                top = scenarios[0]
                title = top.get("title", "Unknown") if isinstance(top, dict) else "Unknown"
                score = top.get("combined_score", 0) if isinstance(top, dict) else 0
                return (
                    f"CURRENT THREAT LEVEL: {level}\n"
                    f"Cycle: {cycle} | Data Mode: {mode}\n"
                    f"Top scenario: {title} (score: {score:.0%})\n"
                    f"Total scenarios: {len(scenarios)}\n"
                    f"Tracking: {aircraft_count} aircraft, {quake_count} quakes, "
                    f"{anomaly_count} anomalies, {news_count} news signals.\n"
                    f"All assessments require human verification."
                )
            return f"CURRENT THREAT LEVEL: {level}. No active threat scenarios. System is monitoring."

        # Aircraft / air questions
        if any(kw in q for kw in ["aircraft", "air", "flight", "plane", "aviation"]):
            anomalies = [a for a in _engine_state.get("latest_aircraft", [])
                         if isinstance(a, dict) and a.get("squawk") in ("7500", "7600", "7700")]
            return (
                f"AIR DOMAIN STATUS:\n"
                f"Aircraft tracked: {aircraft_count}\n"
                f"Anomalies detected: {anomaly_count}\n"
                f"Emergency squawks active: {len(anomalies)}\n"
                f"Data source: {'LIVE OpenSky' if 'OpenSky' in str(_engine_state.get('data_sources_active', [])) else 'DEMO data'}"
            )

        # Earthquake / environment questions
        if any(kw in q for kw in ["earthquake", "quake", "seismic", "environment", "weather"]):
            return (
                f"ENVIRONMENT STATUS:\n"
                f"Earthquakes monitored: {quake_count}\n"
                f"Data source: {'LIVE USGS' if 'USGS' in str(_engine_state.get('data_sources_active', [])) else 'DEMO data'}"
            )

        # News / signals questions
        if any(kw in q for kw in ["news", "signal", "intel", "intelligence"]):
            return (
                f"SIGNALS STATUS:\n"
                f"News articles monitored: {news_count}\n"
                f"Data source: {'LIVE GDELT' if 'GDELT' in str(_engine_state.get('data_sources_active', [])) else 'DEMO data'}"
            )

        # Agent questions
        if any(kw in q for kw in ["agent", "team", "who"]):
            paused = _engine_state.get("paused_agents", set())
            lines = ["AGENT STATUS:"]
            for role, info in [
                ("AIR_WATCH", "Air Domain Watcher"),
                ("GROUND_WATCH", "Ground Movement Analyst"),
                ("SIGNALS_WATCH", "Signals & News Analyst"),
                ("MARITIME_WATCH", "Maritime Domain Watcher"),
                ("ENVIRONMENT_WATCH", "Environmental Monitor"),
                ("CORRELATOR", "Cross-Domain Correlator"),
                ("RED_TEAM", "Red Team Adversary"),
                ("REPORT_AGENT", "Report Synthesiser"),
            ]:
                status = "PAUSED" if role in paused else "ACTIVE"
                lines.append(f"  {info}: {status}")
            return "\n".join(lines)

        # File questions
        if any(kw in q for kw in ["file", "upload", "document"]):
            if files:
                lines = [f"UPLOADED FILES ({len(files)}):"]
                for f in files[-10:]:
                    lines.append(f"  - {f['name']} ({f['size_kb']:.1f} KB) uploaded {f['time']}")
                return "\n".join(lines)
            return "No files uploaded yet. Use the FILE UPLOAD panel to add intel documents."

        # God mode questions
        if any(kw in q for kw in ["god mode", "override", "manual"]):
            gm = _engine_state.get("god_mode", False)
            return (
                f"GOD MODE: {'ENABLED' if gm else 'DISABLED'}\n"
                f"Manual threat level: {_engine_state.get('manual_threat_level', 'AUTO')}\n"
                f"Paused agents: {len(_engine_state.get('paused_agents', set()))}\n"
                f"Scenario overrides: {len(_engine_state.get('god_mode_overrides', {}))}"
            )

        # Help
        if any(kw in q for kw in ["help", "what can", "how do", "command"]):
            return (
                "OPERATOR CONSOLE — Available queries:\n"
                "  'threat status' — Current threat assessment\n"
                "  'aircraft status' — Air domain report\n"
                "  'earthquake status' — Environment report\n"
                "  'news status' — Signals intelligence\n"
                "  'agent status' — All 8 agents\n"
                "  'file status' — Uploaded documents\n"
                "  'god mode status' — Override controls\n"
                "  Or ask any question about the current situation."
            )

        # Default: summarize current state
        return (
            f"SYSTEM SUMMARY (Cycle {cycle}):\n"
            f"Threat Level: {level} | Data: {mode}\n"
            f"Tracking: {aircraft_count} aircraft, {quake_count} quakes, "
            f"{news_count} news signals\n"
            f"Active scenarios: {len(scenarios)}\n"
            f"Type 'help' for available queries."
        )

    # ── GOD MODE ──

    def _handle_godmode_toggle(self):
        """Toggle god mode on/off."""
        data = self._read_json_body()
        _engine_state["god_mode"] = data.get("enabled", not _engine_state["god_mode"])
        now = datetime.now(timezone.utc).isoformat()
        status = "ENABLED" if _engine_state["god_mode"] else "DISABLED"
        _engine_state["operator_messages"].append({
            "role": "system",
            "text": f"GOD MODE {status} by operator.",
            "time": now,
        })
        self._json_response({"god_mode": _engine_state["god_mode"]})

    def _handle_godmode_override(self):
        """Override a scenario's threat score."""
        if not _engine_state["god_mode"]:
            self._json_response({"error": "God mode not enabled"})
            return
        data = self._read_json_body()
        scenario_id = data.get("scenario_id", "")
        new_score = data.get("score")
        notes = data.get("notes", "")
        dismiss = data.get("dismiss", False)

        _engine_state["god_mode_overrides"][scenario_id] = {
            "score": new_score,
            "notes": notes,
            "dismissed": dismiss,
            "time": datetime.now(timezone.utc).isoformat(),
        }

        # Apply to current report
        report = _engine_state.get("latest_report")
        if report and "scenarios" in report:
            for s in report["scenarios"]:
                if isinstance(s, dict) and s.get("scenario_id") == scenario_id:
                    if dismiss:
                        s["combined_score"] = 0.0
                        s["threat_level"] = "DISMISSED"
                    elif new_score is not None:
                        s["combined_score"] = float(new_score)
                        if new_score >= 0.9: s["threat_level"] = "CRITICAL"
                        elif new_score >= 0.7: s["threat_level"] = "HIGH"
                        elif new_score >= 0.4: s["threat_level"] = "MEDIUM"
                        else: s["threat_level"] = "LOW"
                    s["human_override"] = True
                    s["human_notes"] = notes

        self._json_response({"ok": True, "scenario_id": scenario_id})

    def _handle_godmode_agent(self):
        """Pause or resume an agent."""
        if not _engine_state["god_mode"]:
            self._json_response({"error": "God mode not enabled"})
            return
        data = self._read_json_body()
        agent_role = data.get("agent_role", "")
        action = data.get("action", "toggle")

        if action == "pause":
            _engine_state["paused_agents"].add(agent_role)
        elif action == "resume":
            _engine_state["paused_agents"].discard(agent_role)
        else:
            if agent_role in _engine_state["paused_agents"]:
                _engine_state["paused_agents"].discard(agent_role)
            else:
                _engine_state["paused_agents"].add(agent_role)

        self._json_response({
            "agent_role": agent_role,
            "paused": agent_role in _engine_state["paused_agents"],
            "all_paused": list(_engine_state["paused_agents"]),
        })

    def _handle_godmode_threat_level(self):
        """Manually set the overall threat level."""
        if not _engine_state["god_mode"]:
            self._json_response({"error": "God mode not enabled"})
            return
        data = self._read_json_body()
        level = data.get("level")  # None means auto
        _engine_state["manual_threat_level"] = level

        # Apply to current report
        report = _engine_state.get("latest_report")
        if report and level:
            report["overall_threat_level"] = level

        now = datetime.now(timezone.utc).isoformat()
        _engine_state["operator_messages"].append({
            "role": "system",
            "text": f"Threat level manually set to {level or 'AUTO'} by operator.",
            "time": now,
        })

        self._json_response({"manual_threat_level": level})

    # ── FILE UPLOAD ──

    def _handle_file_upload(self):
        """Handle intel file uploads."""
        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            self._json_response({"error": "Expected multipart/form-data"})
            return

        # Parse the multipart form data
        boundary = content_type.split("boundary=")[-1].encode()
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        # Simple multipart parser
        files_saved = []
        parts = body.split(b"--" + boundary)
        for part in parts:
            if b"filename=" not in part:
                continue
            # Extract filename
            header_end = part.find(b"\r\n\r\n")
            if header_end == -1:
                continue
            header = part[:header_end].decode("utf-8", errors="replace")
            file_data = part[header_end + 4:]
            # Trim trailing \r\n--
            if file_data.endswith(b"\r\n"):
                file_data = file_data[:-2]
            if file_data.endswith(b"--"):
                file_data = file_data[:-2]
            if file_data.endswith(b"\r\n"):
                file_data = file_data[:-2]

            # Get filename from header
            fname = "unknown"
            for line in header.split("\r\n"):
                if "filename=" in line:
                    start = line.find('filename="') + 10
                    end = line.find('"', start)
                    if end > start:
                        fname = line[start:end]
                        # Sanitize filename
                        fname = fname.replace("/", "_").replace("\\", "_").replace("..", "_")

            if not file_data or len(file_data) < 2:
                continue

            # Save file
            save_path = UPLOAD_DIR / fname
            save_path.write_bytes(file_data)

            now = datetime.now(timezone.utc).isoformat()
            file_meta = {
                "name": fname,
                "size_kb": len(file_data) / 1024,
                "path": str(save_path),
                "time": now,
            }
            _engine_state["uploaded_files"].append(file_meta)
            files_saved.append(file_meta)

            # Log to chat
            _engine_state["operator_messages"].append({
                "role": "system",
                "text": f"File uploaded: {fname} ({len(file_data)/1024:.1f} KB)",
                "time": now,
            })

        self._json_response({
            "ok": True,
            "files": files_saved,
            "total_uploaded": len(_engine_state["uploaded_files"]),
        })

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
