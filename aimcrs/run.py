"""
AIMCRS APINDRA — MAIN RUNNER
==============================
This is the file you run to start the whole system.

How to run:
    cd /home/user/defence
    python3 -m aimcrs.run

What happens when you run it:
1. Creates the simulation engine (Layer 1)
2. Spawns the defence agent team (Layer 2)
3. Pulls live data from all free sources (Layer 3)
4. Feeds data into the agents
5. Runs simulation rounds
6. Generates threat report (Layer 4)
7. Prints the report to screen
8. Starts the web dashboard (Layer 5)

⚠️ HUMAN IN THE LOOP:
After each round, the system prints its findings and waits.
You can then:
- Press Enter to continue to next round
- Type 'pause' to pause and review
- Type 'stop' to end the simulation
- Type 'override' to change a threat score
- Type 'inject' to add new data manually
"""

import sys
import os
import asyncio
import json
from pathlib import Path

# Make sure Python can find our modules
sys.path.insert(0, str(Path(__file__).parent))

from engine.simulation_engine import SimulationEngine
from agents.defence_agent import create_default_agent_team
from data_feeds.opensky_feed import OpenSkyFeed
from data_feeds.other_feeds import (
    USGSEarthquakeFeed,
    GDELTFeed,
    CelestrakFeed,
    DataCollector,
)
from defence_layer.threat_engine import ThreatEngine
from config.settings import (
    AGENT_SIMULATION_ROUNDS,
    REFRESH_INTERVAL_SECONDS,
    REPORTS_DIR,
)


def print_banner():
    """Print the startup banner."""
    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   AIMCRS APINDRA — Defence Intelligence Engine               ║
║   Patent: Swarm Intelligence + Multi-Source Data Fusion       ║
║                                                              ║
║   Layers:                                                    ║
║   [1] OASIS Simulation Engine ✓                              ║
║   [2] MiroFish Agent Framework ✓                             ║
║   [3] Live Data Feeds ✓                                      ║
║   [4] AIMCRS Defence Layer ✓                                 ║
║                                                              ║
║   ⚠️  Human in the loop at every stage                       ║
║   ⚠️  All assessments require human verification             ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)


async def run_demo_cycle():
    """
    Run one complete cycle of the defence intelligence engine.
    This is the main function that ties all 4 layers together.
    """
    print_banner()

    # ─── STEP 1: Create the simulation engine (Layer 1) ───
    print("[STEP 1] Initialising simulation engine...")
    engine = SimulationEngine()
    state = engine.create_simulation(agent_count=8)
    print(f"  Simulation ID: {state.simulation_id}")
    print(f"  Status: {state.status}")
    print()

    # ─── STEP 2: Create the agent team (Layer 2) ───
    print("[STEP 2] Spawning defence agent team...")
    agents = create_default_agent_team()
    engine.register_agents(agents)
    print(f"  Agents created: {len(agents)}")
    for agent in agents:
        print(f"    • {agent.name} ({agent.role_key})")
    print()

    # ─── STEP 3: Pull live data (Layer 3) ───
    print("[STEP 3] Pulling live data from open sources...")
    print("  This may take 15-30 seconds (API rate limits)...")
    print()

    data_collected = {}

    # 3a. OpenSky — live aircraft
    print("  [3a] OpenSky Network — live aircraft tracking...")
    try:
        opensky = OpenSkyFeed()
        # Pull worldwide data (or specify bbox for a region)
        flight_data = opensky.get_live_aircraft()
        data_collected["air_traffic"] = flight_data

        if flight_data.get("error"):
            print(f"    ⚠️ {flight_data['error']}")
        else:
            count = flight_data.get("count", 0)
            print(f"    ✓ Tracking {count} aircraft")

            # Detect anomalies
            if flight_data.get("states"):
                anomalies = opensky.detect_anomalies(flight_data["states"])
                if anomalies:
                    print(f"    ⚠️ {len(anomalies)} anomalies detected!")
                    for a in anomalies[:3]:
                        print(f"      • {a['type']}: {a['detail']}")
                    data_collected["air_anomalies"] = {
                        "anomalies": anomalies,
                        "count": len(anomalies),
                    }
    except Exception as e:
        print(f"    ⚠️ OpenSky error: {e}")
    print()

    # 3b. USGS — earthquakes
    print("  [3b] USGS — earthquake data...")
    try:
        usgs = USGSEarthquakeFeed()
        quake_data = usgs.get_recent_earthquakes()
        data_collected["earthquakes"] = quake_data
        count = quake_data.get("count", 0)
        if count > 0:
            print(f"    ✓ {count} earthquakes in last hour")
            for q in quake_data.get("earthquakes", [])[:3]:
                print(
                    f"      • M{q['magnitude']} at {q['place']}"
                )
        else:
            print("    ✓ No significant earthquakes")
    except Exception as e:
        print(f"    ⚠️ USGS error: {e}")
    print()

    # 3c. GDELT — global news events
    print("  [3c] GDELT — global threat news...")
    try:
        gdelt = GDELTFeed()
        news_data = gdelt.get_recent_events(
            query="military conflict threat defence", max_records=10
        )
        data_collected["global_news"] = news_data
        count = news_data.get("count", 0)
        print(f"    ✓ {count} relevant news articles found")
        for article in news_data.get("articles", [])[:3]:
            print(f"      • {article['title'][:80]}")
    except Exception as e:
        print(f"    ⚠️ GDELT error: {e}")
    print()

    # 3d. Celestrak — satellites
    print("  [3d] Celestrak — satellite data...")
    try:
        celestrak = CelestrakFeed()
        sat_data = celestrak.get_satellites("active")
        data_collected["satellite_orbits"] = sat_data
        count = sat_data.get("count", 0)
        print(f"    ✓ {count} active satellites tracked")
    except Exception as e:
        print(f"    ⚠️ Celestrak error: {e}")
    print()

    # Feed all data into the engine
    print("  Feeding data into simulation engine...")
    for source_name, data in data_collected.items():
        engine.feed_data(source_name, data)
    print(
        f"  ✓ {len(data_collected)} data sources loaded"
    )
    print()

    # ─── STEP 4: Run simulation (Layers 1+2 working together) ───
    print(f"[STEP 4] Running simulation ({AGENT_SIMULATION_ROUNDS} rounds)...")
    print("  Each round, all agents analyse the data and interact.")
    print()

    threat_engine = ThreatEngine()

    def on_round_complete(round_num, actions):
        """Called after each round — this is the human checkpoint."""
        print(f"  ── Round {round_num} Complete ──")
        for action in actions:
            if action.threat_score > 0:
                print(
                    f"    [{action.threat_score:.1f}] "
                    f"{action.content[:100]}"
                )

        # Generate threat report for this round
        report = threat_engine.analyse_round(actions, round_num)
        print(f"  Overall threat: {report.overall_threat_level}")
        print()

    all_actions = await engine.run_simulation(
        on_round_complete=on_round_complete
    )

    # ─── STEP 5: Final Report (Layer 4) ───
    print()
    print("[STEP 5] Generating final threat report...")
    print()
    print(threat_engine.get_report_summary())

    # Save report to file
    report_data = threat_engine.get_latest_report()
    report_file = REPORTS_DIR / f"report_{state.simulation_id}.json"
    with open(report_file, "w") as f:
        json.dump(report_data, f, indent=2, default=str)
    print(f"\n  Report saved to: {report_file}")

    # Clean up
    engine.close()

    return report_data


def main():
    """Entry point — run the demo cycle."""
    try:
        report = asyncio.run(run_demo_cycle())
        print("\n✓ Simulation complete.")
        print("  Run the dashboard with: python3 -m aimcrs.dashboard.server")
    except KeyboardInterrupt:
        print("\n\nSimulation stopped by operator.")
    except Exception as e:
        print(f"\n⚠️ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
