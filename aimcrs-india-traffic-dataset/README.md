# AIMCRS India Traffic Dataset

## Patent Pending: IN202541120892 | Proprietary — Abheet Prem Manghnani

---

```
╔═══════════════════════════════════════════════════╗
║         AIMCRS INDIA TRAFFIC DATA PIPELINE        ║
╠═══════════════════════════════════════════════════╣
║  SOURCE LAYER                                     ║
║  YouTube → Government → Academic → Kaggle         ║
║  Roboflow → Live Feeds                            ║
╠═══════════════════════════════════════════════════╣
║  PROCESSING LAYER                                 ║
║  Download → Extract → Clean → Label → Augment     ║
╠═══════════════════════════════════════════════════╣
║  MODEL LAYER                                      ║
║  Vehicle Detection → Ambulance Detection          ║
║  Flow Analysis → Signal Prediction                ║
╠═══════════════════════════════════════════════════╣
║  OUTPUT LAYER                                     ║
║  AIMCRS AI-CER Green Corridor Engine              ║
╚═══════════════════════════════════════════════════╝
```

---

## SECTION 1 — WHAT THIS IS

This is the **training data engine** for AIMCRS.

In simple words: it collects Indian traffic videos and images from many
sources, cleans them up, labels the vehicles in them, and uses them to
train AI models that can recognise ambulances and understand Indian
traffic patterns.

**Why does this matter?**

AIMCRS AI-CER creates green corridors for ambulances — it detects an
ambulance approaching, predicts its route, and turns traffic signals
green ahead of it in real time. To do this, the AI must understand
Indian traffic perfectly. This repository builds that understanding.

---

## SECTION 2 — WHY INDIAN DATA IS DIFFERENT

Western traffic datasets (from USA, Europe) are **useless** for Indian
roads. Here is why:

| Challenge | Western Roads | Indian Roads |
|---|---|---|
| **Lane discipline** | Cars stay in lanes | No lanes — everyone weaves |
| **Vehicle mix** | Mostly cars | Cars, bikes, autos, trucks, buses, cycles ALL mixed |
| **Auto rickshaws** | Don't exist | Everywhere — uniquely Indian |
| **Two wheelers** | Small percentage | 70%+ of vehicles in many cities |
| **Animals on road** | Rare/never | Cows, dogs, goats — common |
| **Pedestrians** | Use footpaths | Walk on roads, cross anywhere |
| **Road quality** | Smooth, marked | Potholes, no markings, uneven |
| **Weather** | Clear mostly | Monsoon rain, dust, haze, fog |
| **Night visibility** | Good street lights | Poor lighting in many areas |
| **Density** | Spaced out | Extremely dense, vehicles touching |
| **Horn usage** | Rare | Constant — acoustic detection possible |
| **Ambulance types** | Standard white/red | Many types, different sirens, sometimes unmarked |

**Bottom line:** You cannot train an AI on American highway footage and
expect it to work at a Chennai intersection. That is why this dataset
exists.

---

## SECTION 3 — HOW TO INSTALL

### What You Need First (Prerequisites)

Before starting, make sure you have these installed on your computer:

1. **Python 3.9 or higher** — the programming language everything runs on
2. **Git** — for downloading this code
3. **pip** — Python's package installer (comes with Python)

### Step-by-Step Installation

```bash
# STEP 1: Clone (download) this repository
git clone https://github.com/digitalloto/defence.git
cd defence/aimcrs-india-traffic-dataset

# STEP 2: Create a virtual environment
# (This is like a clean room for Python — keeps things tidy)
python3 -m venv venv

# STEP 3: Activate the virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# STEP 4: Install all required packages
pip install -r requirements.txt

# STEP 5: Copy the example environment file
cp .env.example .env

# STEP 6: Edit .env and add your API keys
# (See SECTION 5 below for which keys you need)
nano .env
```

### That's It! You're Ready.

---

## SECTION 4 — HOW TO RUN EACH SCRIPT

Each script does one job. Run them in order.

```bash
# ----- STEP 1: Download YouTube traffic footage -----
# What it does: Downloads Indian traffic videos from YouTube
python scripts/download/youtube_downloader.py

# ----- STEP 2: Download government data -----
# What it does: Gets traffic data from Indian government websites
python scripts/download/government_downloader.py

# ----- STEP 3: Download academic datasets -----
# What it does: Downloads research datasets from IITs and universities
python scripts/download/academic_downloader.py

# ----- STEP 4: Download Kaggle datasets -----
# What it does: Downloads traffic datasets from Kaggle
# ⚠️ REQUIRES: Free Kaggle account + API key in .env file
python scripts/download/kaggle_downloader.py

# ----- STEP 5: Download Roboflow datasets -----
# What it does: Downloads labelled image datasets from Roboflow
# ⚠️ REQUIRES: Free Roboflow account for some datasets
python scripts/download/roboflow_downloader.py

# ----- STEP 6: Start live data feeds -----
# What it does: Connects to real-time traffic APIs
python scripts/download/live_feeds.py

# ----- STEP 7: Process all downloaded data -----
# What it does: Extracts frames, cleans images, removes duplicates
python scripts/process/process_pipeline.py

# ----- STEP 8: Auto-label all images -----
# What it does: Uses AI to label vehicles in every image
python scripts/label/auto_label.py

# ----- STEP 9: Augment the dataset -----
# What it does: Creates variations (flipped, darker, rainy) to 6x the data
python scripts/process/augment.py

# ----- STEP 10: Train ambulance detection model -----
# What it does: Trains the AI to spot ambulances in traffic
python scripts/train/train_ambulance.py

# ----- STEP 11: Train flow analysis model -----
# What it does: Trains the AI to understand traffic patterns
python scripts/train/train_flow.py

# ----- STEP 12: Run VILTICS comparison -----
# What it does: Compares our results with VILTICS system
python scripts/train/viltics_comparison.py

# ----- STEP 13: Launch dashboard -----
# What it does: Opens a web page showing all stats
python scripts/dashboard.py
```

---

## SECTION 5 — DATA SOURCES LIST

### FREE Sources (No Payment Required)

| Source | URL | What It Provides | Cost |
|---|---|---|---|
| YouTube (yt-dlp) | youtube.com | Indian traffic video footage | FREE |
| data.gov.in | data.gov.in | Government traffic & accident data | FREE |
| Smart Cities Mission | smartcities.gov.in | City traffic & mobility data | FREE |
| MoRTH | morth.nic.in | Road accident reports, traffic volumes | FREE |
| NCRB | ncrb.gov.in | Accident statistics by state/city | FREE |
| Delhi Traffic Police | delhitrafficpolice.nic.in | Traffic flow & signal timing data | FREE |
| iRAD | irad.nic.in | Integrated road accident database | FREE |
| IDD (IIIT Hyderabad) | idd.insaan.iiit.ac.in | Indian road scene segmentation | FREE |
| UA-DETRAC | detrac.smu.edu.sg | Vehicle detection benchmark | FREE |
| OpenStreetMap | overpass-api.de | Real-time road & vehicle data | FREE |
| Roboflow Universe | universe.roboflow.com | Labelled image datasets | FREE |

### Free With Account Required

| Source | URL | What It Provides | Cost |
|---|---|---|---|
| Kaggle | kaggle.com | Traffic & vehicle datasets | FREE (account needed) |
| Roboflow (some) | roboflow.com | Some premium labelled datasets | FREE (account needed) |

### Free Tier APIs (Limited Requests)

| Source | URL | Free Tier Limit | Cost If Over Limit |
|---|---|---|---|
| TomTom Traffic | developer.tomtom.com | 2,500 requests/day | ⚠️ Paid after that |
| HERE Maps | developer.here.com | 250,000 requests/month | ⚠️ Paid after that |
| MapMyIndia/Mappls | maps.mapmyindia.com | Limited free tier | ⚠️ Paid after that |

### ⚠️ Check Before Using

| Source | Issue |
|---|---|
| Google Maps Traffic | ⚠️ Check terms of service — scraping may not be allowed |
| IIT Bombay Dataset | Check availability — may require academic request |
| IIIT Delhi Dataset | Check availability — may require academic request |

---

## SECTION 6 — MODEL PERFORMANCE

*Models will be trained in later steps. This table will be updated.*

| Model | Task | Target Accuracy | Current Accuracy | Status |
|---|---|---|---|---|
| Vehicle Detection (YOLOv8) | Detect all vehicle types | 90%+ | — | Not yet trained |
| Ambulance Detection | Spot ambulances specifically | 95%+ | — | Not yet trained |
| Flow Analysis | Understand traffic patterns | 85%+ | — | Not yet trained |
| VILTICS Comparison | Compare with VILTICS system | Match or beat | — | Not yet run |

---

## SECTION 7 — HOW TO ADD NEW DATA SOURCES

Want to add a new place to get traffic data from? Follow these steps:

1. **Create a new Python script** in `scripts/download/`
   - Name it clearly: `your_source_downloader.py`

2. **Follow this pattern** in your script:
   - Load API keys from `.env` file (never put keys in the code)
   - Download data to the correct `raw/` subfolder
   - Save metadata (where it came from, when, what license)
   - Log everything to the `logs/` folder
   - Handle errors — if download fails, log it and continue

3. **Add the source** to this README in Section 5

4. **Add any new API keys** to `.env.example` (without the actual key value)

5. **Test it** — run your script and check:
   - Did files download correctly?
   - Is metadata saved?
   - Are errors logged?

---

## SECTION 8 — SYSTEM OVERVIEW

### Vehicle Types AIMCRS Detects

```
VEHICLE TYPES AIMCRS DETECTS:

  Ambulance       <-- HIGHEST PRIORITY
  Car
  Motorcycle
  Auto Rickshaw   <-- UNIQUELY INDIAN
  Bus
  Truck
  Pedestrian
  Cycle
  Animal          <-- ONLY IN INDIA
```

### Data Flow

```
DATA FLOW:

Raw Video ---------> Frame Extraction -----> Auto Label
    |                      |                      |
    v                      v                      v
  YouTube            Clean & Filter          YOLO Format
  Government         Remove Dupes           COCO Format
  Academic           Augmentation           Training Set
  Kaggle                  |                      |
                          v                      v
                      Dashboard ---------> Model Training
                                                |
                                                v
                                          AIMCRS AI-CER
                                       Green Corridor Engine
```

### Folder Structure

```
aimcrs-india-traffic-dataset/
|
|-- raw/                    <-- Downloaded raw data goes here
|   |-- youtube/            <-- YouTube traffic videos
|   |-- government/         <-- Government open data
|   |-- academic/           <-- University research datasets
|   |-- kaggle/             <-- Kaggle competition datasets
|
|-- processed/              <-- Cleaned and processed data
|   |-- labelled/           <-- Images with vehicle labels
|   |-- unlabelled/         <-- Images waiting to be labelled
|   |-- augmented/          <-- Augmented (modified) copies
|
|-- models/                 <-- Trained AI models
|   |-- vehicle_detection/  <-- General vehicle detector
|   |-- ambulance_detection/<-- Ambulance specialist model
|   |-- flow_analysis/      <-- Traffic flow analyser
|
|-- scripts/                <-- All the code that does the work
|   |-- download/           <-- Scripts to download data
|   |-- process/            <-- Scripts to clean and process
|   |-- label/              <-- Scripts to label images
|   |-- train/              <-- Scripts to train AI models
|
|-- datasets/               <-- Final training-ready datasets
|   |-- train/              <-- 80% of data for training
|   |-- validation/         <-- 10% for checking during training
|   |-- test/               <-- 10% for final testing
|
|-- docs/                   <-- Documentation and guides
```

---

## Built By

**Abheet Prem Manghnani**
Founder, AIMCRS
Chennai, India

*Building AI that saves lives on Indian roads.*
