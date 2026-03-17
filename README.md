# AIMCRS — AI-Powered Multi-Domain Crisis Response System

> **100% Indigenous | 3 Indian Patents | Zero Foreign Dependencies**
> Built by **Abheet Prem Manghnani** | Chennai, India

---

## What is AIMCRS?

AIMCRS (AI-Powered Multi-Domain Crisis Response System) and its operational platform **NETRA** are a fully indigenous, patent-protected AI-driven intelligence and emergency response system. AIMCRS is aligned with the **Defence Forces Vision 2047** released by Hon'ble Raksha Mantri Shri Rajnath Singh on 10 March 2026.

This repository contains **two main projects**:

| # | Project | Description |
|---|---------|-------------|
| 1 | **Vision 2047 Strategic Alignment Website** | Interactive web dashboard mapping AIMCRS capabilities to Defence Forces Vision 2047 priorities |
| 2 | **India Traffic Dataset Pipeline** | AI-powered data collection, processing, labelling, and model training pipeline for Indian traffic and emergency vehicle detection |

---

## Repository Structure

```
defence/
│
├── README.md                          ← YOU ARE HERE
│
├── ── PROJECT 1: Vision 2047 Website ──
├── index.html                         ← Main webpage (HTML structure)
├── style.css                          ← Styling (colours, layout, fonts)
├── script.js                          ← Interactivity (click handlers, data)
│
├── ── STRATEGY DOCUMENTS ──
├── STEP1_ANALYSIS.md                  ← Vision 2047 analysis & AIMCRS alignment
├── STEP2_DEFENCE_ALIGNMENT.md         ← Formal alignment document for defence contacts
├── STEP3_REPLIT_INSTRUCTIONS.md       ← How to deploy the website on Replit
├── STEP4_OUTREACH_MESSAGES.md         ← WhatsApp, LinkedIn & email templates
│
├── ── REPLIT CONFIG ──
├── .replit                            ← Replit run configuration
├── replit.nix                         ← Replit system dependencies
│
└── ── PROJECT 2: India Traffic Dataset Pipeline ──
    └── aimcrs-india-traffic-dataset/
        ├── requirements.txt           ← Python dependencies
        ├── setup_replit.py            ← One-click Replit setup script
        ├── .env.example               ← API key template (copy to .env)
        ├── LICENSE.md                 ← Project licence
        │
        ├── scripts/
        │   ├── download/              ← Data downloaders (YouTube, Kaggle, etc.)
        │   │   ├── youtube_downloader.py
        │   │   ├── youtube_config.py
        │   │   ├── kaggle_downloader.py
        │   │   ├── roboflow_downloader.py
        │   │   ├── government_downloader.py
        │   │   ├── academic_downloader.py
        │   │   └── live_feeds.py
        │   │
        │   ├── process/               ← Data processing & augmentation
        │   │   ├── process_pipeline.py
        │   │   └── augment.py
        │   │
        │   ├── label/                 ← Auto-labelling with YOLOv8
        │   │   └── auto_label.py
        │   │
        │   ├── train/                 ← Model training scripts
        │   │   ├── train_ambulance.py
        │   │   ├── train_flow.py
        │   │   └── viltics_comparison.py
        │   │
        │   └── dashboard.py           ← Web dashboard (Flask, port 5000)
        │
        ├── raw/                       ← Raw downloaded data
        │   ├── youtube/               ← YouTube traffic videos
        │   ├── government/            ← Government open data
        │   ├── academic/              ← Academic datasets
        │   └── kaggle/                ← Kaggle datasets
        │
        ├── processed/                 ← Processed data
        │   ├── labelled/              ← Images with YOLO labels
        │   ├── unlabelled/            ← Images without labels
        │   └── augmented/             ← Augmented training images
        │
        ├── datasets/                  ← Final training splits
        │   ├── train/                 ← 80% training data
        │   ├── validation/            ← 10% validation data
        │   └── test/                  ← 10% test data
        │
        ├── models/                    ← Trained AI models
        │   ├── ambulance_detection/   ← Ambulance detection model (YOLOv8)
        │   ├── vehicle_detection/     ← Vehicle detection model
        │   └── flow_analysis/         ← Traffic flow analysis model
        │
        ├── logs/                      ← Runtime logs
        └── docs/
            └── DATA_SOURCES.md        ← Documentation of all data sources
```

---

## Project 1: Vision 2047 Strategic Alignment Website

### What It Does

An interactive web page that maps AIMCRS capabilities to each of the 8 major priorities in India's Defence Forces Vision 2047 document.

```
┌─────────────────────────────────────────────────────────┐
│                    AIMCRS WEBSITE                        │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  PRIORITY 1  │  │  PRIORITY 2  │  │  PRIORITY 3  │  │
│  │  Data-Centric│  │  Data Force  │  │     DGA      │  │
│  │   Warfare    │  │  Tri-Service │  │  Geo-Spatial │  │
│  │   ALIGNED    │  │   ALIGNED    │  │   ALIGNED    │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  PRIORITY 4  │  │  PRIORITY 5  │  │  PRIORITY 6  │  │
│  │  Sudarshan   │  │  Cognitive   │  │ Drone Force  │  │
│  │   Chakra     │  │   Warfare    │  │ Counter-UAS  │  │
│  │   ALIGNED    │  │   ALIGNED    │  │   ALIGNED    │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐                     │
│  │  PRIORITY 7  │  │  PRIORITY 8  │                     │
│  │ Space/Cyber  │  │ Atmanirbhar  │                     │
│  │  Commands    │  │   Bharat     │                     │
│  │   ALIGNED    │  │   ALIGNED    │                     │
│  └──────────────┘  └──────────────┘                     │
│                                                         │
│  Click any card → See full alignment details             │
└─────────────────────────────────────────────────────────┘
```

### 8 Vision 2047 Priorities Covered

| # | Priority | AIMCRS Response |
|---|----------|-----------------|
| 1 | Data-Centric Warfare & Decision Superiority | NETRA processes multi-source intelligence into real-time decision support |
| 2 | Data Force (New Tri-Service Entity) | Foundational AI technology layer for the proposed Data Force |
| 3 | Defence Geo-Spatial Agency (DGA) | Satellite feeds + terrain data → unified Common Operating Picture |
| 4 | Mission Sudarshan Chakra (Air Defence) | AI-driven threat detection, classification & counter-strategies |
| 5 | Cognitive Warfare Action Force | Information monitoring, pattern recognition, disinformation detection |
| 6 | Drone Force & Counter-UAS | AI data processing for drone fleet management & counter-UAS ops |
| 7 | Space & Cyber Commands | Cyber threat detection, space sensor integration, EM monitoring |
| 8 | Atmanirbhar Bharat | 100% Indian, 3 patents, zero foreign dependency, built in Chennai |

### How to View the Website

**Option A — Open locally:**
Open `index.html` in any web browser (Chrome, Safari, Firefox).

**Option B — Deploy on Replit:**
See `STEP3_REPLIT_INSTRUCTIONS.md` for step-by-step instructions.

---

## Project 2: India Traffic Dataset Pipeline

### What It Does

A complete AI pipeline to collect, process, label, and train models on Indian traffic data — specifically for **emergency vehicle (ambulance) detection** and **green corridor** creation.

**Patent:** IN202541120892 (Pending)

### Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    AIMCRS DATA PIPELINE                          │
│                                                                  │
│  STEP 1-6: DATA COLLECTION                                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │ YouTube  │ │Government│ │ Academic │ │  Kaggle  │           │
│  │ Traffic  │ │ Open Data│ │ Datasets │ │ Datasets │           │
│  │ Videos   │ │ (MoRTH)  │ │ (IITs)   │ │          │           │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘           │
│       │             │            │             │                  │
│       ▼             ▼            ▼             ▼                  │
│  ┌──────────────────────────────────────────────────┐            │
│  │              raw/ (Downloaded Data)               │            │
│  └──────────────────────┬───────────────────────────┘            │
│                         │                                        │
│  STEP 7: PROCESSING     ▼                                        │
│  ┌──────────────────────────────────────────────────┐            │
│  │  process_pipeline.py                              │            │
│  │  • Extract frames from videos                     │            │
│  │  • Resize to 640x640                              │            │
│  │  • Remove duplicates (image hashing)              │            │
│  │  • Quality filtering                              │            │
│  └──────────────────────┬───────────────────────────┘            │
│                         │                                        │
│  STEP 8: AUTO-LABELLING ▼                                        │
│  ┌──────────────────────────────────────────────────┐            │
│  │  auto_label.py (YOLOv8 pre-trained)               │            │
│  │  Detects 9 vehicle types:                         │            │
│  │  ┌────────────────────────────────────────┐       │            │
│  │  │ 0: Car        │ 5: AMBULANCE (PRIORITY)│       │            │
│  │  │ 1: Motorcycle │ 6: Pedestrian          │       │            │
│  │  │ 2: Auto Rick. │ 7: Cycle               │       │            │
│  │  │ 3: Bus        │ 8: Animal              │       │            │
│  │  │ 4: Truck      │    (India-specific)     │       │            │
│  │  └────────────────────────────────────────┘       │            │
│  └──────────────────────┬───────────────────────────┘            │
│                         │                                        │
│  STEP 9: AUGMENTATION   ▼                                        │
│  ┌──────────────────────────────────────────────────┐            │
│  │  augment.py (Albumentations)                      │            │
│  │  • Flip, rotate, brightness, contrast             │            │
│  │  • Rain/fog simulation (Indian conditions)        │            │
│  │  • 5x data multiplication                         │            │
│  └──────────────────────┬───────────────────────────┘            │
│                         │                                        │
│  STEP 10-11: TRAINING   ▼                                        │
│  ┌──────────────────────────────────────────────────┐            │
│  │  train_ambulance.py  → Ambulance detection model  │            │
│  │  train_flow.py       → Traffic flow analysis      │            │
│  │  viltics_comparison  → Benchmark vs VILTICS       │            │
│  └──────────────────────┬───────────────────────────┘            │
│                         │                                        │
│  DASHBOARD              ▼                                        │
│  ┌──────────────────────────────────────────────────┐            │
│  │  dashboard.py (Flask @ port 5000)                 │            │
│  │  • Total images/videos collected                  │            │
│  │  • City coverage map                              │            │
│  │  • Model accuracy scores                          │            │
│  │  • Data source breakdown                          │            │
│  └──────────────────────────────────────────────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

### Vehicle Types Detected

| ID | Type | Priority | Notes |
|----|------|----------|-------|
| 0 | Car | Standard | |
| 1 | Motorcycle / Two Wheeler | Standard | |
| 2 | Auto Rickshaw | India-specific | Unique to Indian roads |
| 3 | Bus | Standard | |
| 4 | Truck | Standard | |
| **5** | **Ambulance** | **HIGHEST** | **Primary target for green corridor** |
| 6 | Pedestrian | Safety | |
| 7 | Cycle | Standard | |
| 8 | Animal | India-specific | Cattle, dogs on Indian roads |

### Data Sources

| Source | Type | API Key Needed? |
|--------|------|-----------------|
| YouTube | Indian traffic videos (Delhi, Mumbai, Chennai, Bangalore, etc.) | No |
| data.gov.in | Government road accident & traffic data (MoRTH) | Yes (free) |
| Kaggle | Indian vehicle detection datasets | Yes (free) |
| Roboflow | Pre-labelled vehicle detection datasets | Yes (free) |
| Academic | IIT/university research datasets | No |
| Live feeds | TomTom, HERE Maps, MapmyIndia traffic APIs | Yes (free tier) |

---

## Getting Started

### Option 1: Run on Replit (Easiest)

1. Import this repository into Replit
2. Click the **Run** button — the setup script runs automatically
3. The dashboard opens at `http://localhost:5000`

Or run setup manually in the Replit Shell:
```bash
python aimcrs-india-traffic-dataset/setup_replit.py
```

### Option 2: Run Locally

```bash
# 1. Clone the repository
git clone https://github.com/digitalloto/defence.git
cd defence

# 2. Install Python dependencies
cd aimcrs-india-traffic-dataset
pip install -r requirements.txt

# 3. Set up API keys
cp .env.example .env
# Edit .env with your actual API keys (see below)

# 4. Run the dashboard
python scripts/dashboard.py
# Open http://localhost:5000 in your browser
```

### Setting Up API Keys

Copy `.env.example` to `.env` and fill in your keys:

```bash
cd aimcrs-india-traffic-dataset
cp .env.example .env
```

| Key | Where to Get It | Required? |
|-----|-----------------|-----------|
| `KAGGLE_USERNAME` / `KAGGLE_KEY` | kaggle.com → Profile → Settings → API → Create New Token | For Kaggle datasets |
| `ROBOFLOW_API_KEY` | roboflow.com → Settings → API Keys | For Roboflow datasets |
| `DATA_GOV_IN_API_KEY` | data.gov.in → API → Register | For government data |
| `TOMTOM_API_KEY` | developer.tomtom.com → Dashboard → Keys | For live traffic (2,500 req/day free) |
| `HERE_API_KEY` | developer.here.com → Project → API Key | For live traffic (250K req/month free) |
| `MAPPLS_CLIENT_ID` / `SECRET` | maps.mapmyindia.com → Developer → API Keys | For MapmyIndia data |
| `GOOGLE_API_KEY` | console.cloud.google.com | Optional |

**Note:** The YouTube downloader needs NO API keys — start there!

---

## Running the Full Pipeline (Step by Step)

```bash
cd aimcrs-india-traffic-dataset

# Step 1: Download YouTube traffic videos (no API key needed)
python scripts/download/youtube_downloader.py

# Step 2: Download government open data
python scripts/download/government_downloader.py

# Step 3: Download academic datasets
python scripts/download/academic_downloader.py

# Step 4: Download Kaggle datasets (needs KAGGLE_KEY)
python scripts/download/kaggle_downloader.py

# Step 5: Download Roboflow datasets (needs ROBOFLOW_API_KEY)
python scripts/download/roboflow_downloader.py

# Step 6: Fetch live traffic feeds
python scripts/download/live_feeds.py

# Step 7: Process all downloaded data
python scripts/process/process_pipeline.py

# Step 8: Auto-label images with YOLOv8
python scripts/label/auto_label.py

# Step 9: Augment training data (5x multiplication)
python scripts/process/augment.py

# Step 10: Train ambulance detection model
python scripts/train/train_ambulance.py

# Step 11: Train traffic flow analysis model
python scripts/train/train_flow.py

# Step 12: Benchmark against VILTICS
python scripts/train/viltics_comparison.py

# Step 13: View everything on the dashboard
python scripts/dashboard.py
```

---

## Strategy Documents

These files contain the strategic alignment and outreach materials:

| File | Contents |
|------|----------|
| `STEP1_ANALYSIS.md` | Detailed analysis of Defence Forces Vision 2047 — what matches AIMCRS, gaps AIMCRS fills, exact quotes to use in pitches |
| `STEP2_DEFENCE_ALIGNMENT.md` | Formal alignment document for defence contacts — maps every Vision 2047 priority to AIMCRS capabilities |
| `STEP3_REPLIT_INSTRUCTIONS.md` | Step-by-step guide to deploy the website on Replit |
| `STEP4_OUTREACH_MESSAGES.md` | Ready-to-use WhatsApp, LinkedIn, and email templates for defence outreach |

---

## Three Phases — Vision 2047 Timeline

```
 NOW ────────────── 2030 ────────────── 2040 ────────────── 2047
  │                   │                   │                   │
  │   PHASE I         │   PHASE II        │   PHASE III       │
  │   Era of          │   Era of          │   Era of          │
  │   Transition      │   Consolidation   │   Excellence      │
  │                   │                   │                   │
  │   AIMCRS:         │   AIMCRS:         │   AIMCRS:         │
  │   READY FOR       │   SCALABLE        │   FULL MULTI-     │
  │   DEPLOYMENT      │   ACROSS          │   DOMAIN          │
  │                   │   COMMANDS        │   INTEGRATION     │
  │                   │                   │                   │
```

---

## Three Indian Patents

| Patent | Description | Supports |
|--------|-------------|----------|
| **Patent 1** | AI-Driven Emergency Response & Crisis Management System | Data Force, Cognitive Warfare |
| **Patent 2** | Real-Time Multi-Sensor Threat Detection Platform | DGA, Mission Sudarshan Chakra |
| **Patent 3** | Predictive Intelligence & Multi-Domain Data Fusion Engine | Decision Superiority, Data-Centric Warfare |

*Patent numbers available on request. All patents filed and registered in India.*

---

## Dual-Use Capability

```
┌─────────────────────────┐         ┌─────────────────────────┐
│       MILITARY          │         │   EMERGENCY RESPONSE    │
│                         │         │                         │
│ • Battlefield threat    │         │ • Natural disaster      │
│   detection             │         │   early warning         │
│ • Multi-sensor intel    │◄───────►│ • Multi-agency crisis   │
│   fusion                │  SAME   │   coordination          │
│ • Predictive conflict   │   AI    │ • Predictive disaster   │
│   analytics             │  CORE   │   impact modelling      │
│ • Command & control     │         │ • Emergency ops centre  │
│ • Drone ISR coord.      │         │ • Search & rescue drones│
│ • Counter-UAS ops       │         │ • Civilian protection   │
└─────────────────────────┘         └─────────────────────────┘
```

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Website | HTML5, CSS3, Vanilla JavaScript |
| AI Models | YOLOv8 (Ultralytics), PyTorch |
| Data Processing | OpenCV, Pillow, NumPy, Pandas |
| Video Downloads | yt-dlp |
| Dataset Platforms | Kaggle API, Roboflow API |
| Data Augmentation | Albumentations |
| Dashboard | Flask, Plotly |
| Deployment | Replit (Nix + Python 3.11) |

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Website looks blank | Make sure all 3 files (`index.html`, `style.css`, `script.js`) are present |
| `pip install` fails | Try: `pip install --upgrade pip` then retry |
| Dashboard won't start | Run: `pip install flask loguru` |
| YouTube download fails | Update yt-dlp: `pip install --upgrade yt-dlp` |
| Kaggle download fails | Check your `KAGGLE_USERNAME` and `KAGGLE_KEY` in `.env` |
| Port 5000 in use | Kill the old process or change port in `dashboard.py` |
| Missing API key warnings | Add keys in `.env` file (see API Keys section above) |

---

## Contact

**Abheet Prem Manghnani**
Founder, AIMCRS
Chennai, India

**AIMCRS** — AI-Powered Multi-Domain Crisis Response System
*Atmanirbhar Bharat | Defence Forces Vision 2047 Aligned*
