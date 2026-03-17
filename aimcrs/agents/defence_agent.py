"""
LAYER 2 — DEFENCE AGENTS
=========================
Adapted from MiroFish agent spawning + OASIS agent framework.

What this does:
- Defines different types of defence intelligence agents
- Each agent has a ROLE (what it watches), a PERSONALITY (how it thinks),
  and MEMORY (what it remembers from previous rounds)
- Agents analyse data feeds and produce threat assessments
- Agents can see what other agents said and build on each other's work

This is the "brain" of each analyst in the system.

MiroFish connection:
- We borrow the concept of agent profiles with personalities
- We borrow the ReACT pattern (Think → Act → Observe → Repeat)
- We borrow the report synthesis approach

OASIS connection:
- We borrow the concurrent agent execution model
- We borrow the action-based communication system
- We borrow the scalable agent graph structure

IMPORTANT — No LLM required for the prototype:
These agents use RULE-BASED logic (if/then rules) for now.
This means they work without any AI API key.
When you're ready, you can plug in an LLM to make them smarter.
"""

import uuid
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from engine.simulation_engine import AgentAction


# ─────────────────────────────────────────────
# AGENT ROLES — What each agent watches for
# ─────────────────────────────────────────────

AGENT_ROLES = {
    "AIR_WATCH": {
        "name": "Air Domain Watcher",
        "description": "Monitors aircraft movements, altitude changes, "
                       "unusual flight paths, military aircraft activity",
        "watches": ["air_traffic", "satellite_orbits"],
        "personality": "methodical, detail-oriented, cautious",
    },
    "GROUND_WATCH": {
        "name": "Ground Movement Analyst",
        "description": "Monitors road networks, railway activity, "
                       "unusual ground movement patterns",
        "watches": ["ground_movement", "traffic"],
        "personality": "pattern-focused, systematic, thorough",
    },
    "SIGNALS_WATCH": {
        "name": "Signals & News Analyst",
        "description": "Monitors news feeds, social media signals, "
                       "global event patterns, emergency broadcasts",
        "watches": ["global_news", "emergency_feeds"],
        "personality": "quick-thinking, skeptical, cross-referencing",
    },
    "MARITIME_WATCH": {
        "name": "Maritime Domain Watcher",
        "description": "Monitors ship movements, port activity, "
                       "unusual vessel behaviour",
        "watches": ["maritime_traffic"],
        "personality": "patient, experienced, detail-oriented",
    },
    "ENVIRONMENT_WATCH": {
        "name": "Environmental Monitor",
        "description": "Monitors weather, earthquakes, fires, "
                       "natural disasters that affect operations",
        "watches": ["weather", "earthquakes", "fires"],
        "personality": "analytical, data-driven, precise",
    },
    "CORRELATOR": {
        "name": "Cross-Domain Correlator",
        "description": "Looks at ALL domains together, finds patterns "
                       "that no single watcher would see alone. "
                       "This is the key intelligence agent.",
        "watches": ["ALL"],  # Sees everything
        "personality": "strategic, big-picture, paranoid",
    },
    "RED_TEAM": {
        "name": "Red Team Adversary",
        "description": "Thinks like the enemy. What would a threat actor "
                       "do given the current situation? Challenges every "
                       "assumption made by other agents.",
        "watches": ["ALL"],
        "personality": "aggressive, creative, contrarian",
    },
    "REPORT_AGENT": {
        "name": "Report Synthesiser",
        "description": "Takes all agent outputs and creates a single "
                       "ranked threat report. Like the ReportAgent in "
                       "MiroFish but for defence.",
        "watches": ["ALL"],
        "personality": "clear communicator, prioritiser, concise",
    },
}


# ─────────────────────────────────────────────
# DEFENCE AGENT CLASS
# ─────────────────────────────────────────────

@dataclass
class AgentMemory:
    """
    What the agent remembers from previous rounds.
    This grows over time, giving agents context.
    """
    observations: list = field(default_factory=list)
    alerts_raised: list = field(default_factory=list)
    threat_scores_given: list = field(default_factory=list)

    def add_observation(self, observation: str, round_number: int):
        self.observations.append({
            "round": round_number,
            "text": observation,
            "time": datetime.now(timezone.utc).isoformat(),
        })
        # Keep only last 50 observations to avoid memory bloat
        if len(self.observations) > 50:
            self.observations = self.observations[-50:]


class DefenceAgent:
    """
    One defence intelligence agent.

    Each agent:
    1. Has a ROLE — what it watches (air, ground, signals, etc.)
    2. Has a PERSONALITY — how it thinks and weighs evidence
    3. Has MEMORY — what it remembers from earlier rounds
    4. ACTS each round — analyses data and produces an assessment

    The act() method is the main function. It:
    - Gets the latest data feeds
    - Filters for data relevant to this agent's role
    - Analyses the data using rules (or LLM later)
    - Produces an AgentAction with a threat score
    """

    def __init__(self, role_key: str, agent_id: str = None):
        if role_key not in AGENT_ROLES:
            raise ValueError(
                f"Unknown role: {role_key}. "
                f"Valid roles: {list(AGENT_ROLES.keys())}"
            )

        role = AGENT_ROLES[role_key]
        self.agent_id = agent_id or f"{role_key}_{uuid.uuid4().hex[:6]}"
        self.role_key = role_key
        self.name = role["name"]
        self.description = role["description"]
        self.watches = role["watches"]
        self.personality = role["personality"]
        self.memory = AgentMemory()
        self.active = True

    async def act(self, round_number: int, data_feeds: dict,
                  previous_actions: list = None) -> AgentAction:
        """
        The agent's main action each round.

        Steps:
        1. Filter data feeds to only what this agent watches
        2. Analyse the relevant data
        3. Check what other agents have said (if available)
        4. Produce an assessment with a threat score
        """
        if not self.active:
            return None

        # Step 1: Get relevant data
        relevant_data = self._filter_relevant_data(data_feeds)

        if not relevant_data and self.role_key not in (
            "CORRELATOR", "RED_TEAM", "REPORT_AGENT"
        ):
            # Domain watchers need data to work with
            return AgentAction(
                agent_id=self.agent_id,
                agent_role=self.role_key,
                action_type="NO_DATA",
                content=f"{self.name}: No relevant data available this round.",
                threat_score=0.0,
            )

        # Step 2: Analyse based on role
        if self.role_key == "AIR_WATCH":
            return await self._analyse_air(relevant_data, round_number)
        elif self.role_key == "GROUND_WATCH":
            return await self._analyse_ground(relevant_data, round_number)
        elif self.role_key == "SIGNALS_WATCH":
            return await self._analyse_signals(relevant_data, round_number)
        elif self.role_key == "MARITIME_WATCH":
            return await self._analyse_maritime(relevant_data, round_number)
        elif self.role_key == "ENVIRONMENT_WATCH":
            return await self._analyse_environment(
                relevant_data, round_number
            )
        elif self.role_key == "CORRELATOR":
            return await self._correlate(
                data_feeds, previous_actions, round_number
            )
        elif self.role_key == "RED_TEAM":
            return await self._red_team(
                data_feeds, previous_actions, round_number
            )
        elif self.role_key == "REPORT_AGENT":
            return await self._synthesise_report(
                previous_actions, round_number
            )

        return None

    def _filter_relevant_data(self, data_feeds: dict) -> dict:
        """Get only the data this agent cares about."""
        if "ALL" in self.watches:
            return data_feeds

        relevant = {}
        for source_name, feed in data_feeds.items():
            for watch_key in self.watches:
                if watch_key in source_name:
                    relevant[source_name] = feed
        return relevant

    # ─────────────────────────────────────────
    # DOMAIN-SPECIFIC ANALYSIS METHODS
    # These use simple rules for the prototype.
    # Replace with LLM calls when ready.
    # ─────────────────────────────────────────

    async def _analyse_air(self, data: dict, round_num: int) -> AgentAction:
        """Analyse air traffic data for anomalies."""
        findings = []
        threat_score = 0.0

        for source_name, feed in data.items():
            feed_data = feed.get("data", {})
            if isinstance(feed_data, list):
                aircraft_list = feed_data
            elif isinstance(feed_data, dict):
                aircraft_list = feed_data.get("states", [])
            else:
                continue

            total_aircraft = len(aircraft_list)
            findings.append(f"Tracking {total_aircraft} aircraft")

            # Check for anomalies
            for ac in aircraft_list:
                if isinstance(ac, dict):
                    alt = ac.get("baro_altitude") or ac.get("altitude", 0)
                    speed = ac.get("velocity") or ac.get("speed", 0)
                    on_ground = ac.get("on_ground", False)
                    callsign = ac.get("callsign", "UNKNOWN")
                    squawk = ac.get("squawk", "")

                    # Very low altitude and not on ground = unusual
                    if alt and 0 < alt < 300 and not on_ground:
                        findings.append(
                            f"LOW ALTITUDE: {callsign} at {alt}m"
                        )
                        threat_score = max(threat_score, 0.5)

                    # Very high speed = possible military
                    if speed and speed > 300:  # m/s ≈ 600 knots
                        findings.append(
                            f"HIGH SPEED: {callsign} at {speed} m/s"
                        )
                        threat_score = max(threat_score, 0.4)

                    # Emergency squawk codes
                    if squawk in ("7500", "7600", "7700"):
                        code_meaning = {
                            "7500": "HIJACK",
                            "7600": "RADIO FAILURE",
                            "7700": "EMERGENCY",
                        }
                        findings.append(
                            f"SQUAWK {squawk} ({code_meaning[squawk]}): "
                            f"{callsign}"
                        )
                        threat_score = max(threat_score, 0.8)

        observation = "; ".join(findings) if findings else "No anomalies"
        self.memory.add_observation(observation, round_num)

        return AgentAction(
            agent_id=self.agent_id,
            agent_role=self.role_key,
            action_type="ANALYSIS",
            target="air_domain",
            content=f"AIR WATCH: {observation}",
            threat_score=threat_score,
            metadata={"findings_count": len(findings)},
        )

    async def _analyse_ground(self, data: dict,
                              round_num: int) -> AgentAction:
        """Analyse ground movement data."""
        findings = []
        threat_score = 0.0

        for source_name, feed in data.items():
            feed_data = feed.get("data", {})
            if isinstance(feed_data, dict):
                events = feed_data.get("events", [])
                for event in events:
                    event_type = event.get("type", "")
                    if "military" in event_type.lower():
                        findings.append(
                            f"Military movement detected: {event_type}"
                        )
                        threat_score = max(threat_score, 0.6)
                    elif "blockade" in event_type.lower():
                        findings.append(f"Road blockade: {event_type}")
                        threat_score = max(threat_score, 0.4)

        if not findings:
            findings.append("No unusual ground activity detected")

        observation = "; ".join(findings)
        self.memory.add_observation(observation, round_num)

        return AgentAction(
            agent_id=self.agent_id,
            agent_role=self.role_key,
            action_type="ANALYSIS",
            target="ground_domain",
            content=f"GROUND WATCH: {observation}",
            threat_score=threat_score,
        )

    async def _analyse_signals(self, data: dict,
                               round_num: int) -> AgentAction:
        """Analyse news and signals data."""
        findings = []
        threat_score = 0.0

        threat_keywords = [
            "military", "attack", "missile", "nuclear", "invasion",
            "border", "troops", "conflict", "war", "explosion",
            "threat", "alert", "emergency", "evacuation", "strike",
        ]

        for source_name, feed in data.items():
            feed_data = feed.get("data", {})
            articles = []
            if isinstance(feed_data, list):
                articles = feed_data
            elif isinstance(feed_data, dict):
                articles = feed_data.get("articles", [])

            for article in articles:
                title = ""
                if isinstance(article, dict):
                    title = article.get("title", "")
                elif isinstance(article, str):
                    title = article

                title_lower = title.lower()
                matched_keywords = [
                    kw for kw in threat_keywords if kw in title_lower
                ]
                if matched_keywords:
                    findings.append(
                        f"SIGNAL [{','.join(matched_keywords)}]: {title[:100]}"
                    )
                    # More keywords = higher threat
                    score = min(0.3 + 0.1 * len(matched_keywords), 0.9)
                    threat_score = max(threat_score, score)

        if not findings:
            findings.append("No threat-related signals detected")

        observation = "; ".join(findings[:10])  # Cap at 10
        self.memory.add_observation(observation, round_num)

        return AgentAction(
            agent_id=self.agent_id,
            agent_role=self.role_key,
            action_type="ANALYSIS",
            target="signals_domain",
            content=f"SIGNALS WATCH: {observation}",
            threat_score=threat_score,
            metadata={"signal_count": len(findings)},
        )

    async def _analyse_maritime(self, data: dict,
                                round_num: int) -> AgentAction:
        """Analyse maritime traffic data."""
        findings = []
        threat_score = 0.0

        for source_name, feed in data.items():
            feed_data = feed.get("data", {})
            if isinstance(feed_data, dict):
                vessels = feed_data.get("vessels", [])
                findings.append(f"Tracking {len(vessels)} vessels")

        if not findings:
            findings.append("No maritime data available")

        observation = "; ".join(findings)
        self.memory.add_observation(observation, round_num)

        return AgentAction(
            agent_id=self.agent_id,
            agent_role=self.role_key,
            action_type="ANALYSIS",
            target="maritime_domain",
            content=f"MARITIME WATCH: {observation}",
            threat_score=threat_score,
        )

    async def _analyse_environment(self, data: dict,
                                   round_num: int) -> AgentAction:
        """Analyse environmental data (weather, quakes, fires)."""
        findings = []
        threat_score = 0.0

        for source_name, feed in data.items():
            feed_data = feed.get("data", {})

            # Earthquake data (USGS format)
            if "earthquake" in source_name:
                features = []
                if isinstance(feed_data, dict):
                    features = feed_data.get("features", [])
                for quake in features:
                    props = quake.get("properties", {})
                    mag = props.get("mag", 0)
                    place = props.get("place", "unknown")
                    if mag >= 5.0:
                        findings.append(
                            f"EARTHQUAKE: M{mag} at {place}"
                        )
                        threat_score = max(threat_score, 0.3 + mag * 0.05)

            # Weather data
            if "weather" in source_name:
                if isinstance(feed_data, dict):
                    alerts = feed_data.get("alerts", [])
                    for alert in alerts:
                        event = alert.get("event", "unknown")
                        findings.append(f"WEATHER ALERT: {event}")
                        threat_score = max(threat_score, 0.3)

        if not findings:
            findings.append("No significant environmental events")

        observation = "; ".join(findings)
        self.memory.add_observation(observation, round_num)

        return AgentAction(
            agent_id=self.agent_id,
            agent_role=self.role_key,
            action_type="ANALYSIS",
            target="environment",
            content=f"ENVIRONMENT: {observation}",
            threat_score=threat_score,
        )

    async def _correlate(self, all_data: dict, previous_actions: list,
                         round_num: int) -> AgentAction:
        """
        Cross-domain correlation — the MOST IMPORTANT agent.

        This agent looks at what ALL other agents found and asks:
        "What patterns emerge when we combine these signals?"

        Example: Air anomaly + news about military + earthquake near border
        = combined threat score higher than any single signal.
        """
        if not previous_actions:
            return AgentAction(
                agent_id=self.agent_id,
                agent_role=self.role_key,
                action_type="CORRELATE",
                content="CORRELATOR: Waiting for domain agents to report.",
                threat_score=0.0,
            )

        # Collect all threat scores from this round
        domain_scores = {}
        domain_findings = {}
        for action in previous_actions:
            if action.round_number == round_num:
                domain_scores[action.agent_role] = action.threat_score
                domain_findings[action.agent_role] = action.content

        if not domain_scores:
            return AgentAction(
                agent_id=self.agent_id,
                agent_role=self.role_key,
                action_type="CORRELATE",
                content="CORRELATOR: No domain reports this round.",
                threat_score=0.0,
            )

        # Count how many domains have elevated threat
        elevated = {
            k: v for k, v in domain_scores.items() if v >= 0.3
        }
        max_single = max(domain_scores.values()) if domain_scores else 0.0

        # Multi-domain correlation boosts the score
        if len(elevated) >= 3:
            combined = min(max_single + 0.2, 1.0)
            pattern = "MULTI-DOMAIN CORRELATION DETECTED"
        elif len(elevated) >= 2:
            combined = min(max_single + 0.1, 1.0)
            pattern = "Two-domain correlation detected"
        else:
            combined = max_single
            pattern = "Single-domain activity only"

        domains_text = ", ".join(
            f"{k}={v:.1f}" for k, v in domain_scores.items()
        )
        content = (
            f"CORRELATOR: {pattern}. "
            f"Scores: [{domains_text}]. "
            f"Combined assessment: {combined:.2f}"
        )

        self.memory.add_observation(content, round_num)

        return AgentAction(
            agent_id=self.agent_id,
            agent_role=self.role_key,
            action_type="CORRELATE",
            target="cross_domain",
            content=content,
            threat_score=combined,
            metadata={
                "domain_scores": domain_scores,
                "elevated_count": len(elevated),
            },
        )

    async def _red_team(self, all_data: dict, previous_actions: list,
                        round_num: int) -> AgentAction:
        """
        Red Team — thinks like the adversary.

        Asks: "If I were the enemy, what would I do with this situation?"
        Challenges assumptions from other agents.
        """
        if not previous_actions:
            return AgentAction(
                agent_id=self.agent_id,
                agent_role=self.role_key,
                action_type="RED_TEAM",
                content="RED TEAM: Standing by. Need domain data first.",
                threat_score=0.0,
            )

        # Look for what other agents might be MISSING
        active_domains = set()
        for action in previous_actions:
            if action.round_number == round_num:
                active_domains.add(action.agent_role)

        all_domain_roles = {
            "AIR_WATCH", "GROUND_WATCH", "SIGNALS_WATCH",
            "MARITIME_WATCH", "ENVIRONMENT_WATCH",
        }
        missing = all_domain_roles - active_domains
        blind_spots = []
        if missing:
            blind_spots.append(
                f"BLIND SPOTS: No data from {', '.join(missing)}"
            )

        # Challenge the highest threat assessment
        highest_threat = max(
            previous_actions,
            key=lambda a: a.threat_score,
            default=None,
        )
        challenges = []
        if highest_threat and highest_threat.threat_score > 0:
            challenges.append(
                f"Highest threat ({highest_threat.threat_score:.1f}) from "
                f"{highest_threat.agent_role} — could this be a decoy "
                f"or false positive?"
            )

        content_parts = ["RED TEAM ASSESSMENT:"]
        content_parts.extend(blind_spots)
        content_parts.extend(challenges)
        if not blind_spots and not challenges:
            content_parts.append("No significant concerns this round.")

        content = " ".join(content_parts)
        self.memory.add_observation(content, round_num)

        return AgentAction(
            agent_id=self.agent_id,
            agent_role=self.role_key,
            action_type="RED_TEAM",
            target="adversary_perspective",
            content=content,
            threat_score=0.0,  # Red team doesn't score, it questions
            metadata={
                "blind_spots": list(missing),
                "challenges": challenges,
            },
        )

    async def _synthesise_report(self, previous_actions: list,
                                 round_num: int) -> AgentAction:
        """
        Report Agent — synthesises everything into a ranked report.

        Like MiroFish's ReportAgent, but for defence:
        1. Collects all agent outputs
        2. Ranks by threat score
        3. Groups related findings
        4. Produces a concise summary for the operator
        """
        if not previous_actions:
            return AgentAction(
                agent_id=self.agent_id,
                agent_role=self.role_key,
                action_type="REPORT",
                content="REPORT: No agent data to synthesise yet.",
                threat_score=0.0,
            )

        # Get this round's actions (excluding ourselves)
        round_actions = [
            a for a in previous_actions
            if a.round_number == round_num
            and a.agent_role != "REPORT_AGENT"
        ]

        if not round_actions:
            return AgentAction(
                agent_id=self.agent_id,
                agent_role=self.role_key,
                action_type="REPORT",
                content="REPORT: No new intelligence this round.",
                threat_score=0.0,
            )

        # Sort by threat score (highest first)
        round_actions.sort(key=lambda a: a.threat_score, reverse=True)

        # Build report
        max_threat = round_actions[0].threat_score

        # Threat level label
        if max_threat >= 0.9:
            level = "CRITICAL"
        elif max_threat >= 0.7:
            level = "HIGH"
        elif max_threat >= 0.4:
            level = "MEDIUM"
        else:
            level = "LOW"

        report_lines = [
            f"=== THREAT REPORT — Round {round_num} ===",
            f"Overall Level: {level} ({max_threat:.2f})",
            f"Active Agents: {len(round_actions)}",
            "",
        ]

        for i, action in enumerate(round_actions[:5], 1):
            score_bar = "█" * int(action.threat_score * 10)
            report_lines.append(
                f"  {i}. [{action.threat_score:.1f}] {score_bar} "
                f"{action.content[:120]}"
            )

        content = "\n".join(report_lines)
        self.memory.add_observation(f"Report generated: {level}", round_num)

        return AgentAction(
            agent_id=self.agent_id,
            agent_role=self.role_key,
            action_type="REPORT",
            target="synthesis",
            content=content,
            threat_score=max_threat,
            metadata={
                "threat_level": level,
                "agent_count": len(round_actions),
            },
        )

    def to_dict(self) -> dict:
        """Convert agent to a dictionary for display/storage."""
        return {
            "agent_id": self.agent_id,
            "role": self.role_key,
            "name": self.name,
            "description": self.description,
            "personality": self.personality,
            "watches": self.watches,
            "active": self.active,
            "memory_size": len(self.memory.observations),
        }


# ─────────────────────────────────────────────
# AGENT FACTORY — Creates all agents at once
# ─────────────────────────────────────────────

def create_default_agent_team() -> list:
    """
    Create one agent for each role.
    Returns a list of 8 DefenceAgent objects.

    This is the standard team:
    1. Air Watcher
    2. Ground Watcher
    3. Signals Watcher
    4. Maritime Watcher
    5. Environment Watcher
    6. Cross-Domain Correlator
    7. Red Team Adversary
    8. Report Synthesiser
    """
    agents = []
    for role_key in AGENT_ROLES:
        agent = DefenceAgent(role_key=role_key)
        agents.append(agent)
    return agents


def create_scaled_agent_team(agents_per_role: int = 3) -> list:
    """
    Create multiple agents per role for larger simulations.
    More agents = more diverse perspectives.

    With agents_per_role=3, you get 24 agents total.
    """
    agents = []
    for role_key in AGENT_ROLES:
        for i in range(agents_per_role):
            agent = DefenceAgent(
                role_key=role_key,
                agent_id=f"{role_key}_{i}",
            )
            agents.append(agent)
    return agents
