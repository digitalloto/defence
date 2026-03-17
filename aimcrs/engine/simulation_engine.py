"""
LAYER 1 — SIMULATION ENGINE
============================
Adapted from OASIS (camel-ai/oasis).

What this does:
- Runs the simulation loop — like a game engine that ticks every round
- Manages all agents — creates them, runs their actions, collects results
- Stores everything in a SQLite database (a local file, no server needed)
- Handles time — each "round" represents a time step in the simulation

Think of this as the "game board" where all the agents play.
The OASIS repo does social media simulation. We replace that with
defence threat simulation.
"""

import asyncio
import sqlite3
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass, field, asdict

from config.settings import (
    AGENT_SIMULATION_ROUNDS,
    DB_PATH,
    REFRESH_INTERVAL_SECONDS,
)


# ─────────────────────────────────────────────
# DATA CLASSES — Structured containers for data
# A dataclass is like a form with labelled fields.
# ─────────────────────────────────────────────

@dataclass
class SimulationState:
    """Tracks where the simulation is right now."""
    simulation_id: str = ""
    status: str = "CREATED"  # CREATED → RUNNING → PAUSED → COMPLETED
    current_round: int = 0
    total_rounds: int = AGENT_SIMULATION_ROUNDS
    started_at: str = ""
    last_updated: str = ""
    agent_count: int = 0
    data_sources_active: list = field(default_factory=list)
    error: str = ""


@dataclass
class AgentAction:
    """One action taken by one agent in one round."""
    action_id: str = ""
    agent_id: str = ""
    agent_role: str = ""
    round_number: int = 0
    action_type: str = ""       # e.g. "ANALYSE", "ALERT", "CORRELATE"
    target: str = ""            # What the action is about
    content: str = ""           # The agent's output text
    threat_score: float = 0.0   # 0.0 to 1.0
    timestamp: str = ""
    metadata: dict = field(default_factory=dict)


# ─────────────────────────────────────────────
# DATABASE SETUP
# SQLite is a file-based database — no server needed.
# It stores all agent actions and simulation history.
# ─────────────────────────────────────────────

DB_SCHEMA = """
CREATE TABLE IF NOT EXISTS simulations (
    simulation_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    current_round INTEGER DEFAULT 0,
    total_rounds INTEGER DEFAULT 5,
    started_at TEXT,
    last_updated TEXT,
    agent_count INTEGER DEFAULT 0,
    data_sources TEXT DEFAULT '[]',
    error TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS agent_actions (
    action_id TEXT PRIMARY KEY,
    simulation_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    agent_role TEXT NOT NULL,
    round_number INTEGER NOT NULL,
    action_type TEXT NOT NULL,
    target TEXT DEFAULT '',
    content TEXT DEFAULT '',
    threat_score REAL DEFAULT 0.0,
    timestamp TEXT NOT NULL,
    metadata TEXT DEFAULT '{}',
    FOREIGN KEY (simulation_id) REFERENCES simulations(simulation_id)
);

CREATE TABLE IF NOT EXISTS threat_scenarios (
    scenario_id TEXT PRIMARY KEY,
    simulation_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    combined_score REAL DEFAULT 0.0,
    contributing_agents TEXT DEFAULT '[]',
    data_sources TEXT DEFAULT '[]',
    created_at TEXT NOT NULL,
    FOREIGN KEY (simulation_id) REFERENCES simulations(simulation_id)
);

CREATE TABLE IF NOT EXISTS data_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    source_name TEXT NOT NULL,
    data_type TEXT NOT NULL,
    raw_data TEXT NOT NULL,
    processed_at TEXT NOT NULL,
    record_count INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_actions_sim
    ON agent_actions(simulation_id, round_number);
CREATE INDEX IF NOT EXISTS idx_scenarios_sim
    ON threat_scenarios(simulation_id);
CREATE INDEX IF NOT EXISTS idx_snapshots_source
    ON data_snapshots(source_name, processed_at);
"""


def init_database(db_path: Path = None) -> sqlite3.Connection:
    """
    Create (or open) the database and set up tables.

    What this does:
    1. Opens a file called simulation.db
    2. Creates the tables if they don't exist
    3. Returns the connection so other code can use it
    """
    if db_path is None:
        db_path = DB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row  # Access columns by name
    conn.executescript(DB_SCHEMA)
    conn.commit()
    return conn


# ─────────────────────────────────────────────
# SIMULATION ENGINE — The main loop
# ─────────────────────────────────────────────

class SimulationEngine:
    """
    The core engine that runs everything.

    How it works:
    1. You create a simulation (like starting a new game)
    2. Agents are loaded with their roles and personalities
    3. Real-world data is fed in as "seed intelligence"
    4. The engine runs rounds — each round, every agent acts
    5. After all rounds, a threat report is generated

    Human in the loop:
    - You can pause at any time
    - You can inject new data mid-simulation
    - You can override any agent's assessment
    - You can adjust threat levels manually
    """

    def __init__(self):
        self.db = init_database()
        self.state = SimulationState()
        self.agents = []           # List of agent objects
        self.data_feeds = {}       # Name → latest data from each source
        self.threat_scenarios = [] # Combined threat assessments
        self._running = False
        self._paused = False

    def create_simulation(self, agent_count: int = 20) -> SimulationState:
        """
        Start a new simulation.

        What happens:
        1. Creates a unique ID for this simulation
        2. Saves it to the database
        3. Returns the state so you can track it
        """
        now = datetime.now(timezone.utc).isoformat()
        self.state = SimulationState(
            simulation_id=str(uuid.uuid4())[:8],
            status="CREATED",
            current_round=0,
            total_rounds=AGENT_SIMULATION_ROUNDS,
            started_at=now,
            last_updated=now,
            agent_count=agent_count,
        )

        self.db.execute(
            """INSERT INTO simulations
               (simulation_id, status, current_round, total_rounds,
                started_at, last_updated, agent_count)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                self.state.simulation_id,
                self.state.status,
                self.state.current_round,
                self.state.total_rounds,
                self.state.started_at,
                self.state.last_updated,
                self.state.agent_count,
            ),
        )
        self.db.commit()
        return self.state

    def register_agents(self, agents: list):
        """
        Add agents to the simulation.
        Each agent is a DefenceAgent object (see agents/ folder).
        """
        self.agents = agents
        self.state.agent_count = len(agents)
        self._update_state()

    def feed_data(self, source_name: str, data: dict):
        """
        Feed real-world data into the simulation.

        This is how live intelligence gets into the system:
        - OpenSky flight data → feed_data("air_traffic", {...})
        - GDELT news events → feed_data("global_news", {...})
        - Weather alerts → feed_data("weather", {...})

        All agents can then see and react to this data.
        """
        self.data_feeds[source_name] = {
            "data": data,
            "received_at": datetime.now(timezone.utc).isoformat(),
        }

        # Save snapshot to database
        snapshot_id = str(uuid.uuid4())[:8]
        record_count = len(data) if isinstance(data, list) else 1
        self.db.execute(
            """INSERT INTO data_snapshots
               (snapshot_id, source_name, data_type, raw_data,
                processed_at, record_count)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                snapshot_id,
                source_name,
                type(data).__name__,
                json.dumps(data, default=str),
                datetime.now(timezone.utc).isoformat(),
                record_count,
            ),
        )
        self.db.commit()

        if source_name not in self.state.data_sources_active:
            self.state.data_sources_active.append(source_name)
            self._update_state()

    async def run_round(self, round_number: int) -> list:
        """
        Run one round of the simulation.

        What happens in one round:
        1. Each agent gets the latest data feeds
        2. Each agent analyses the data based on its role
        3. Each agent produces an action (assessment, alert, etc.)
        4. All actions are saved to the database
        5. Actions are returned for the correlation engine

        This is the heartbeat of the whole system.
        """
        actions = []

        for agent in self.agents:
            # Each agent analyses the current data
            action = await agent.act(
                round_number=round_number,
                data_feeds=self.data_feeds,
                previous_actions=actions,  # Agents can see what others said
            )

            if action:
                action.action_id = str(uuid.uuid4())[:8]
                action.round_number = round_number
                action.timestamp = datetime.now(timezone.utc).isoformat()
                actions.append(action)

                # Save to database
                self.db.execute(
                    """INSERT INTO agent_actions
                       (action_id, simulation_id, agent_id, agent_role,
                        round_number, action_type, target, content,
                        threat_score, timestamp, metadata)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        action.action_id,
                        self.state.simulation_id,
                        action.agent_id,
                        action.agent_role,
                        action.round_number,
                        action.action_type,
                        action.target,
                        action.content,
                        action.threat_score,
                        action.timestamp,
                        json.dumps(action.metadata, default=str),
                    ),
                )

        self.db.commit()
        return actions

    async def run_simulation(self, on_round_complete=None) -> list:
        """
        Run the full simulation — all rounds.

        Parameters:
        - on_round_complete: A function called after each round
          so you can see progress. This is your "human in the loop"
          checkpoint.

        Returns: List of all threat scenarios found.

        ⚠️ HUMAN IN THE LOOP:
        The on_round_complete callback lets you:
        - See what happened each round
        - Pause the simulation
        - Inject new data
        - Override threat scores
        """
        self.state.status = "RUNNING"
        self._running = True
        self._update_state()

        all_actions = []

        for round_num in range(1, self.state.total_rounds + 1):
            if not self._running:
                break

            while self._paused:
                await asyncio.sleep(0.5)

            self.state.current_round = round_num
            self._update_state()

            # Run one round
            round_actions = await self.run_round(round_num)
            all_actions.extend(round_actions)

            # Callback for human oversight
            if on_round_complete:
                on_round_complete(round_num, round_actions)

        self.state.status = "COMPLETED"
        self._running = False
        self._update_state()

        return all_actions

    def pause(self):
        """Pause the simulation. Human can review before continuing."""
        self._paused = True
        self.state.status = "PAUSED"
        self._update_state()

    def resume(self):
        """Resume after pause."""
        self._paused = False
        self.state.status = "RUNNING"
        self._update_state()

    def stop(self):
        """Stop the simulation completely."""
        self._running = False
        self.state.status = "STOPPED"
        self._update_state()

    def override_threat_score(self, scenario_id: str, new_score: float,
                              reason: str = ""):
        """
        Human operator manually adjusts a threat score.
        This is the "human in the loop" override.
        """
        self.db.execute(
            """UPDATE threat_scenarios
               SET combined_score = ?
               WHERE scenario_id = ?""",
            (new_score, scenario_id),
        )
        self.db.commit()

    def get_all_actions(self, simulation_id: str = None) -> list:
        """Get all agent actions for a simulation."""
        sim_id = simulation_id or self.state.simulation_id
        cursor = self.db.execute(
            """SELECT * FROM agent_actions
               WHERE simulation_id = ?
               ORDER BY round_number, timestamp""",
            (sim_id,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_threat_scenarios(self, simulation_id: str = None) -> list:
        """Get all threat scenarios, ranked by score."""
        sim_id = simulation_id or self.state.simulation_id
        cursor = self.db.execute(
            """SELECT * FROM threat_scenarios
               WHERE simulation_id = ?
               ORDER BY combined_score DESC""",
            (sim_id,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def _update_state(self):
        """Save current state to database."""
        self.state.last_updated = datetime.now(timezone.utc).isoformat()
        self.db.execute(
            """UPDATE simulations
               SET status = ?, current_round = ?, last_updated = ?,
                   agent_count = ?,
                   data_sources = ?
               WHERE simulation_id = ?""",
            (
                self.state.status,
                self.state.current_round,
                self.state.last_updated,
                self.state.agent_count,
                json.dumps(self.state.data_sources_active),
                self.state.simulation_id,
            ),
        )
        self.db.commit()

    def close(self):
        """Clean up database connection."""
        if self.db:
            self.db.close()
