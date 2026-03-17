"""
LAYER 4 — AIMCRS APINDRA DEFENCE APPLICATION LAYER
====================================================
This is YOUR layer, Abheet. This is what makes the system uniquely AIMCRS.

What this does:
1. Takes all agent outputs from the simulation
2. Combines signals across domains (air + ground + signals + etc.)
3. Scores each combined scenario by threat probability
4. Ranks the top 5 threats
5. Generates a human-readable report
6. Updates every 60 seconds
7. Allows human override at every step

This layer sits ON TOP of:
- OASIS engine (Layer 1 — runs the simulation)
- MiroFish framework (Layer 2 — manages agents)
- Data feeds (Layer 3 — real world intelligence)

APINDRA Patent Coverage:
- Swarm intelligence: Multiple agents producing emergent patterns
- Multi-source data fusion: Combining air, ground, signals, maritime, environment
- Edge processing: Can run locally without cloud dependency
- Predictive simulation: Agents model future scenarios
"""

import json
import uuid
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from config.settings import (
    THREAT_LEVEL_LOW,
    THREAT_LEVEL_MEDIUM,
    THREAT_LEVEL_HIGH,
    THREAT_LEVEL_CRITICAL,
    TOP_SCENARIOS_TO_SHOW,
)


@dataclass
class ThreatScenario:
    """
    One combined threat scenario.

    Think of this as one "story" of what might happen:
    "Aircraft anomaly detected + military news + earthquake near border
    = possible cover for military operation"

    Each scenario has:
    - title: Short name
    - description: What the agents think is happening
    - combined_score: 0.0 to 1.0 (higher = more dangerous)
    - contributing_signals: Which data sources fed into this
    - agent_assessments: What each agent said
    - recommended_action: What a human operator should do
    """
    scenario_id: str = ""
    title: str = ""
    description: str = ""
    combined_score: float = 0.0
    threat_level: str = "LOW"
    contributing_signals: list = field(default_factory=list)
    agent_assessments: list = field(default_factory=list)
    recommended_action: str = ""
    created_at: str = ""
    human_override: bool = False
    human_notes: str = ""


@dataclass
class ThreatReport:
    """
    The final output — a ranked list of threat scenarios.
    This is what the operator sees on the dashboard.
    """
    report_id: str = ""
    generated_at: str = ""
    overall_threat_level: str = "LOW"
    scenarios: list = field(default_factory=list)
    data_sources_used: list = field(default_factory=list)
    agent_count: int = 0
    simulation_round: int = 0
    human_operator_notes: str = ""


class ThreatEngine:
    """
    The AIMCRS intelligence fusion engine.

    This is the "brain" that takes all the raw agent outputs
    and turns them into actionable threat assessments.

    How it works:
    1. Collect all agent actions from the simulation
    2. Group related signals together
    3. Calculate combined threat scores
    4. Rank scenarios by probability
    5. Generate a report for the operator

    ⚠️ HUMAN IN THE LOOP:
    - The operator can override any threat score
    - The operator can add notes to any scenario
    - The operator can dismiss false positives
    - The operator can elevate missed signals
    - NOTHING is automated without human review
    """

    def __init__(self):
        self.scenarios = []
        self.reports = []

    def analyse_round(self, agent_actions: list,
                      round_number: int) -> ThreatReport:
        """
        Analyse one round of agent outputs and produce a threat report.

        Parameters:
        - agent_actions: List of AgentAction objects from the simulation engine
        - round_number: Which round this is

        Returns: ThreatReport with ranked scenarios.
        """
        now = datetime.now(timezone.utc).isoformat()

        # Step 1: Group actions by domain
        domain_actions = {}
        for action in agent_actions:
            role = action.agent_role
            if role not in domain_actions:
                domain_actions[role] = []
            domain_actions[role].append(action)

        # Step 2: Build threat scenarios from combinations
        scenarios = self._build_scenarios(domain_actions, round_number)

        # Step 3: Score and rank
        scenarios.sort(key=lambda s: s.combined_score, reverse=True)

        # Step 4: Determine overall threat level
        if scenarios:
            max_score = scenarios[0].combined_score
        else:
            max_score = 0.0

        if max_score >= THREAT_LEVEL_CRITICAL:
            overall = "CRITICAL"
        elif max_score >= THREAT_LEVEL_HIGH:
            overall = "HIGH"
        elif max_score >= THREAT_LEVEL_MEDIUM:
            overall = "MEDIUM"
        else:
            overall = "LOW"

        # Step 5: Build report
        report = ThreatReport(
            report_id=str(uuid.uuid4())[:8],
            generated_at=now,
            overall_threat_level=overall,
            scenarios=[
                asdict(s) for s in scenarios[:TOP_SCENARIOS_TO_SHOW]
            ],
            data_sources_used=list(domain_actions.keys()),
            agent_count=len(agent_actions),
            simulation_round=round_number,
        )

        self.reports.append(report)
        return report

    def _build_scenarios(self, domain_actions: dict,
                         round_number: int) -> list:
        """
        Build threat scenarios by combining signals across domains.

        This is where the magic happens — multi-source data fusion.
        We look at all combinations and ask: "What does this mean together?"
        """
        scenarios = []
        now = datetime.now(timezone.utc).isoformat()

        # Get the highest-threat action from each domain
        domain_highlights = {}
        for role, actions in domain_actions.items():
            if role in ("REPORT_AGENT",):
                continue  # Skip the report agent itself
            threat_actions = [a for a in actions if a.threat_score > 0]
            if threat_actions:
                best = max(threat_actions, key=lambda a: a.threat_score)
                domain_highlights[role] = best

        if not domain_highlights:
            # No threats detected
            scenarios.append(ThreatScenario(
                scenario_id=str(uuid.uuid4())[:8],
                title="All Clear",
                description="No significant threats detected across any domain.",
                combined_score=0.0,
                threat_level="LOW",
                recommended_action="Continue monitoring. No action required.",
                created_at=now,
            ))
            return scenarios

        # Scenario 1: Multi-domain correlation
        if len(domain_highlights) >= 3:
            contributing = list(domain_highlights.keys())
            scores = [a.threat_score for a in domain_highlights.values()]
            avg_score = sum(scores) / len(scores)
            # Multi-domain boosts the score significantly
            combined = min(avg_score + 0.2, 1.0)

            assessments = [
                {
                    "agent": role,
                    "content": action.content[:200],
                    "score": action.threat_score,
                }
                for role, action in domain_highlights.items()
            ]

            scenarios.append(ThreatScenario(
                scenario_id=str(uuid.uuid4())[:8],
                title="Multi-Domain Threat Correlation",
                description=(
                    f"Threat signals detected across {len(contributing)} "
                    f"domains simultaneously: {', '.join(contributing)}. "
                    f"This pattern suggests coordinated activity."
                ),
                combined_score=combined,
                threat_level=self._score_to_level(combined),
                contributing_signals=contributing,
                agent_assessments=assessments,
                recommended_action=(
                    "ALERT: Multi-domain correlation requires immediate "
                    "human assessment. Verify each signal independently."
                ),
                created_at=now,
            ))

        # Scenario 2: Individual domain threats
        for role, action in domain_highlights.items():
            if action.threat_score >= THREAT_LEVEL_MEDIUM:
                scenarios.append(ThreatScenario(
                    scenario_id=str(uuid.uuid4())[:8],
                    title=f"{role.replace('_', ' ').title()} Alert",
                    description=action.content[:300],
                    combined_score=action.threat_score,
                    threat_level=self._score_to_level(action.threat_score),
                    contributing_signals=[role],
                    agent_assessments=[{
                        "agent": role,
                        "content": action.content[:200],
                        "score": action.threat_score,
                    }],
                    recommended_action=self._recommend_action(
                        role, action.threat_score
                    ),
                    created_at=now,
                ))

        # Scenario 3: Red team challenges
        red_team = domain_actions.get("RED_TEAM", [])
        for action in red_team:
            if action.metadata and action.metadata.get("blind_spots"):
                scenarios.append(ThreatScenario(
                    scenario_id=str(uuid.uuid4())[:8],
                    title="Intelligence Gap Warning",
                    description=(
                        f"Red Team identified blind spots: "
                        f"{', '.join(action.metadata['blind_spots'])}. "
                        f"Missing data could hide threats."
                    ),
                    combined_score=0.3,
                    threat_level="MEDIUM",
                    contributing_signals=["RED_TEAM"],
                    agent_assessments=[{
                        "agent": "RED_TEAM",
                        "content": action.content[:200],
                        "score": 0.3,
                    }],
                    recommended_action=(
                        "Investigate missing data sources. "
                        "Activate backup feeds if available."
                    ),
                    created_at=now,
                ))

        return scenarios

    def _score_to_level(self, score: float) -> str:
        """Convert a numeric score to a threat level label."""
        if score >= THREAT_LEVEL_CRITICAL:
            return "CRITICAL"
        elif score >= THREAT_LEVEL_HIGH:
            return "HIGH"
        elif score >= THREAT_LEVEL_MEDIUM:
            return "MEDIUM"
        return "LOW"

    def _recommend_action(self, role: str, score: float) -> str:
        """Generate a recommended action based on domain and severity."""
        actions = {
            "AIR_WATCH": "Check flight radar. Verify aircraft identity. "
                         "Alert air traffic control if unknown.",
            "GROUND_WATCH": "Cross-reference with satellite imagery. "
                            "Check local military reports.",
            "SIGNALS_WATCH": "Verify news sources. Check for confirmation "
                             "from multiple independent sources.",
            "MARITIME_WATCH": "Check vessel AIS data. Verify port activity. "
                              "Alert coast guard if suspicious.",
            "ENVIRONMENT_WATCH": "Assess impact on operations. Update "
                                 "logistics plans if needed.",
            "CORRELATOR": "PRIORITY: Review all contributing signals. "
                          "This is a combined threat assessment.",
        }
        base = actions.get(role, "Review and assess manually.")

        if score >= THREAT_LEVEL_CRITICAL:
            return f"URGENT ACTION REQUIRED: {base}"
        elif score >= THREAT_LEVEL_HIGH:
            return f"HIGH PRIORITY: {base}"
        return base

    def human_override(self, scenario_id: str, new_score: float = None,
                       notes: str = "", dismiss: bool = False):
        """
        Human operator overrides a threat assessment.

        ⚠️ THIS IS THE MOST IMPORTANT FUNCTION.
        The human always has the final say.

        Parameters:
        - scenario_id: Which scenario to override
        - new_score: New threat score (0.0 to 1.0), or None to keep current
        - notes: Human's reasoning for the override
        - dismiss: Set True to mark as false positive
        """
        for report in self.reports:
            for scenario in report.scenarios:
                if isinstance(scenario, dict):
                    if scenario.get("scenario_id") == scenario_id:
                        if dismiss:
                            scenario["combined_score"] = 0.0
                            scenario["threat_level"] = "DISMISSED"
                        elif new_score is not None:
                            scenario["combined_score"] = new_score
                            scenario["threat_level"] = self._score_to_level(
                                new_score
                            )
                        scenario["human_override"] = True
                        scenario["human_notes"] = notes
                        return True
        return False

    def get_latest_report(self) -> dict:
        """Get the most recent threat report as a dictionary."""
        if not self.reports:
            return {"message": "No reports generated yet."}
        return asdict(self.reports[-1])

    def get_report_summary(self) -> str:
        """
        Get a plain-text summary of the latest report.
        Designed to be readable in 30 seconds by a non-technical operator.
        """
        if not self.reports:
            return "No reports available."

        report = self.reports[-1]
        lines = [
            "╔══════════════════════════════════════════════╗",
            "║   AIMCRS APINDRA — THREAT INTELLIGENCE       ║",
            "╚══════════════════════════════════════════════╝",
            "",
            f"  Report: {report.report_id}",
            f"  Generated: {report.generated_at}",
            f"  Round: {report.simulation_round}",
            f"  Agents Active: {report.agent_count}",
            f"  Overall Level: {report.overall_threat_level}",
            "",
            "  TOP THREAT SCENARIOS:",
            "  ─────────────────────",
        ]

        for i, scenario in enumerate(report.scenarios, 1):
            if isinstance(scenario, dict):
                score = scenario.get("combined_score", 0)
                level = scenario.get("threat_level", "LOW")
                title = scenario.get("title", "Unknown")
                bar = "█" * int(score * 20) + "░" * (20 - int(score * 20))
                lines.append(f"  {i}. [{level:8s}] {bar} {score:.1%}")
                lines.append(f"     {title}")
                desc = scenario.get("description", "")
                if desc:
                    lines.append(f"     {desc[:100]}")
                action = scenario.get("recommended_action", "")
                if action:
                    lines.append(f"     → {action[:100]}")
                if scenario.get("human_override"):
                    lines.append(
                        f"     ✋ HUMAN OVERRIDE: {scenario.get('human_notes', '')}"
                    )
                lines.append("")

        if report.human_operator_notes:
            lines.append(f"  OPERATOR NOTES: {report.human_operator_notes}")
            lines.append("")

        lines.append("  ⚠️ All assessments require human verification.")
        lines.append("  ⚠️ AI confidence does not equal ground truth.")

        return "\n".join(lines)
