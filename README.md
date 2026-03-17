# AIMCRS APINDRA — Defence Intelligence Engine

**Built by Abheet Prem Manghnani, Founder of AIMCRS**
**Patent Architecture: Swarm Intelligence + Multi-Source Data Fusion**

---

## What Is This?

This is a defence intelligence prototype that watches the world from multiple angles at the same time and warns you about threats. Think of it like having 8 expert analysts working 24/7, each watching a different domain (air, ground, sea, news, environment), then comparing notes to find patterns no single analyst would catch alone.

It stacks three open source repositories together and adds a defence application layer on top.

---

## How It Works — Simple Explanation

### The 5 Layers (Bottom to Top)

```
┌─────────────────────────────────────────────┐
│  LAYER 5: Dashboard                         │  ← What you see (3D globe + threat panel)
├─────────────────────────────────────────────┤
│  LAYER 4: AIMCRS Defence Layer              │  ← Your patent layer — fuses all signals
├─────────────────────────────────────────────┤
│  LAYER 3: Live Data Feeds                   │  ← Real world data from free APIs
├─────────────────────────────────────────────┤
│  LAYER 2: Agent Framework (from MiroFish)   │  ← 8 AI analysts with different roles
├─────────────────────────────────────────────┤
│  LAYER 1: Simulation Engine (from OASIS)    │  ← The engine that runs everything
└─────────────────────────────────────────────┘
```

### The 8 Agents (Like 8 Expert Analysts)

| # | Agent Name | What It Watches |
|---|-----------|-----------------|
| 1 | **Air Domain Watcher** | Aircraft positions, altitude, speed, emergency codes |
| 2 | **Ground Movement Analyst** | Roads, railways, military ground movement |
| 3 | **Signals & News Analyst** | Global news, social media, emergency broadcasts |
| 4 | **Maritime Domain Watcher** | Ship movements, port activity |
| 5 | **Environmental Monitor** | Earthquakes, weather, fires, disasters |
| 6 | **Cross-Domain Correlator** | Combines ALL agent findings to spot patterns |
| 7 | **Red Team Adversary** | Thinks like the enemy — challenges assumptions |
| 8 | **Report Synthesiser** | Creates the final ranked threat report |

### How A Simulation Runs

1. The engine pulls live data from all free sources (aircraft, earthquakes, news, satellites)
2. All 8 agents analyse the data based on their role
3. This runs for 5 rounds — each round, agents build on what others found
4. The Correlator combines signals: "Air anomaly + military news + earthquake = higher threat"
5. The Red Team challenges: "Could this be a false alarm? What are we missing?"
6. The Report Agent ranks the top 5 threats by probability
7. Everything shows on the dashboard with a threat level (LOW / MEDIUM / HIGH / CRITICAL)

### Human In The Loop (Non-Negotiable)

- The human operator can pause the simulation at any time
- The human can override any threat score
- The human can inject new data or dismiss false positives
- The human can add notes to any scenario
- **Nothing is automated without human review**
- Every report says: "All assessments require human verification"

---

## How To Run It

### Step 1 — Install (One Time Only)

```bash
git clone https://github.com/digitalloto/defence.git
cd defence
git checkout claude/setup-technical-cobuilder-AXQZR
pip3 install -r requirements.txt
```

The only package needed is `requests` (for calling APIs). Python 3.10+ required.

### Step 2 — Run The Text Simulation

```bash
cd /path/to/defence
python3 -m aimcrs.run
```

This runs the full simulation in your terminal and prints the threat report. No browser needed.

### Step 3 — Run The 3D Globe Dashboard

```bash
cd /path/to/defence
python3 -m aimcrs.dashboard.server
```

Then open your browser and go to: **http://localhost:8080**

You will see:
- A 3D globe showing the Earth with land masses and oceans
- Blue dots for aircraft currently in the sky
- Red/orange circles for earthquakes
- A right panel with the top 5 threat scenarios ranked
- A threat level banner (LOW = green, MEDIUM = yellow, HIGH = orange, CRITICAL = red)
- Toggle switches to show/hide each data layer
- Auto-refreshes every 30 seconds

### Step 4 — Deploy On Replit (Free, No Install)

1. Go to https://replit.com
2. Click "Create Repl" then "Import from GitHub"
3. Paste: `https://github.com/digitalloto/defence`
4. Set branch to: `claude/setup-technical-cobuilder-AXQZR`
5. Set run command to: `python3 -m aimcrs.dashboard.server`
6. Click Run — you get a public URL you can share with anyone

---

## Data Sources

### Free Sources (No API Key Needed)

| Source | What It Provides | Rate Limit |
|--------|-----------------|------------|
| **OpenSky Network** | Live aircraft positions worldwide | 1 request per 10 seconds |
| **USGS Earthquake** | Earthquakes from the last hour | No limit |
| **GDELT Project** | Global news events in 100+ languages | No limit |
| **Celestrak** | Satellite orbital data | No limit |

### Free Sources (Free API Key Needed — Sign Up)

| Source | What It Provides | Sign Up Link |
|--------|-----------------|-------------|
| **OpenWeatherMap** | Weather data | https://openweathermap.org/api |
| **NASA FIRMS** | Active fire/disaster data | https://urs.earthdata.nasa.gov |
| **OpenSky (authenticated)** | Faster aircraft data | https://opensky-network.org |

### Paid Sources (NOT Used Unless You Approve)

- ADS-B Exchange (RapidAPI paid plan)
- MarineTraffic (paid API)
- VesselFinder (paid API)
- Twitter/X full API (paid)

---

## File Structure

```
defence/
├── aimcrs/                          ← All the code lives here
│   ├── config/
│   │   └── settings.py              ← All settings, API keys, thresholds
│   ├── engine/
│   │   └── simulation_engine.py     ← Layer 1: The simulation loop + database
│   ├── agents/
│   │   └── defence_agent.py         ← Layer 2: All 8 agent types
│   ├── data_feeds/
│   │   ├── opensky_feed.py          ← Layer 3: Live aircraft data
│   │   └── other_feeds.py           ← Layer 3: Earthquakes, news, satellites, weather, fires
│   ├── defence_layer/
│   │   └── threat_engine.py         ← Layer 4: Threat scoring + report generation
│   ├── dashboard/
│   │   ├── server.py                ← Layer 5: Web server for the dashboard
│   │   └── index.html               ← Layer 5: 3D globe + threat panel UI
│   ├── run.py                       ← Run the text simulation
│   ├── __main__.py                  ← Entry point for python3 -m aimcrs
│   └── __init__.py
├── vendors/                         ← Cloned source repos (not in git)
│   ├── oasis/                       ← OASIS by CAMEL-AI
│   ├── MiroFish/                    ← MiroFish swarm engine
│   └── opensky-api/                 ← OpenSky Python API
├── requirements.txt                 ← Dependencies (just requests)
├── .gitignore
└── README.md                        ← This file
```

---

## How The Three Repos Are Used

### OASIS (camel-ai/oasis)
- **What it is**: Simulation engine that can scale to 1 million agents
- **What we took**: The async agent execution model, round-based simulation loop, SQLite database storage, concurrent agent communication
- **What we changed**: Replaced social media simulation with defence threat simulation

### MiroFish (666ghj/MiroFish)
- **What it is**: Swarm intelligence framework with agent personalities and memories
- **What we took**: Agent profiles with roles and personalities, memory system, report synthesis pattern
- **What we changed**: Replaced financial prediction agents with defence domain agents

### OpenSky API (openskynetwork/opensky-api)
- **What it is**: Python API for live aircraft tracking
- **What we took**: The concept of pulling real-time aircraft state vectors
- **What we built**: Our own feed class with anomaly detection (emergency squawks, low altitude, high speed, missing callsigns)

---

## APINDRA Patent Coverage

This prototype demonstrates all four pillars of the APINDRA architecture:

1. **Swarm Intelligence**: 8 agents with independent roles and memories produce emergent patterns no single agent would find
2. **Multi-Source Data Fusion**: Air + ground + maritime + signals + environment combined into unified threat picture
3. **Edge Processing**: Runs entirely on a local machine with SQLite — no cloud dependency
4. **Predictive Simulation**: Agents model scenarios across multiple rounds, building on each other's findings

---

## Limitations and Risks

- This is a PROTOTYPE — not production-ready
- Rule-based agents (no LLM/AI API needed) — less intelligent but always works
- Free API rate limits mean data refreshes every 60 seconds, not real-time
- No maritime data in prototype (VesselFinder and MarineTraffic are paid)
- No Twitter/X data (full API is paid)
- The dashboard needs internet to load the globe map tiles
- All threat scores are estimates — human verification is always required
- This system does NOT make decisions — it provides intelligence for humans to act on

---

## Next Steps (Build Order)

1. Get the prototype running locally with flight data
2. Add one data layer at a time — test before adding next
3. Add LLM-powered agents (requires OpenAI or Anthropic API key)
4. Add maritime data when budget allows
5. Scale to more agents per domain (3-5 per role instead of 1)
6. Add historical pattern matching (compare today vs past data)
7. Add alert notifications (email, SMS, webhook)
8. Deploy to cloud for always-on monitoring

---

## Contact

**Abheet Prem Manghnani**
Founder, AIMCRS
Chennai, India
