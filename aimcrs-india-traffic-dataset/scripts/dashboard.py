#!/usr/bin/env python3
# ============================================
# Step 11 — AIMCRS Data Dashboard
# ============================================
# File: scripts/dashboard.py
# What: Web dashboard showing dataset stats and progress
# How to run: python scripts/dashboard.py
# Then open: http://localhost:5000 in your browser
#
# Shows:
#   - Total images collected (running count)
#   - Total videos downloaded
#   - Cities covered
#   - Vehicle types labelled
#   - Ambulance images (highlighted separately)
#   - Model accuracy scores
#   - Data source breakdown
#   - Map of India showing data coverage
# ============================================

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(SCRIPTS_DIR))

try:
    from flask import Flask, render_template_string, send_from_directory
except ImportError:
    print("ERROR: Flask is not installed.")
    print("Fix: pip install flask")
    sys.exit(1)

try:
    from loguru import logger
except ImportError:
    print("ERROR: loguru is not installed. Fix: pip install loguru")
    sys.exit(1)

app = Flask(
    __name__,
    template_folder=str(PROJECT_ROOT / "templates"),
    static_folder=str(PROJECT_ROOT / "static"),
)

# Register God Mode admin blueprint
try:
    from admin.routes import admin_bp
    app.register_blueprint(admin_bp)
    logger.info("God Mode admin panel loaded")
except ImportError as e:
    print(f"Warning: Admin panel not loaded: {e}")

# ----- PATHS -----
RAW_DIR = PROJECT_ROOT / "raw"
PROCESSED_DIR = PROJECT_ROOT / "processed"
MODELS_DIR = PROJECT_ROOT / "models"
DATASETS_DIR = PROJECT_ROOT / "datasets"
LOGS_DIR = PROJECT_ROOT / "logs"

# ----- VIDEO AND IMAGE EXTENSIONS -----
VIDEO_EXTS = {".mp4", ".avi", ".mkv", ".mov", ".webm", ".flv"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp"}


def count_files(directory, extensions):
    """Count files with specific extensions in a directory."""
    if not directory.exists():
        return 0
    count = 0
    for ext in extensions:
        count += len(list(directory.rglob(f"*{ext}")))
    return count


def get_stats():
    """Collect all statistics for the dashboard."""
    stats = {}

    # Video counts
    stats["total_videos"] = count_files(RAW_DIR, VIDEO_EXTS)

    # Image counts
    stats["raw_images"] = count_files(RAW_DIR, IMAGE_EXTS)
    stats["processed_images"] = count_files(PROCESSED_DIR, IMAGE_EXTS)
    stats["labelled_images"] = count_files(
        PROCESSED_DIR / "labelled", IMAGE_EXTS
    )
    stats["unlabelled_images"] = count_files(
        PROCESSED_DIR / "unlabelled", IMAGE_EXTS
    )
    stats["augmented_images"] = count_files(
        PROCESSED_DIR / "augmented", IMAGE_EXTS
    )
    stats["total_images"] = (
        stats["raw_images"]
        + stats["processed_images"]
        + stats["augmented_images"]
    )

    # Training dataset
    stats["train_images"] = count_files(DATASETS_DIR / "train", IMAGE_EXTS)
    stats["val_images"] = count_files(DATASETS_DIR / "validation", IMAGE_EXTS)
    stats["test_images"] = count_files(DATASETS_DIR / "test", IMAGE_EXTS)

    # Source breakdown
    stats["youtube_videos"] = count_files(RAW_DIR / "youtube", VIDEO_EXTS)
    stats["government_files"] = count_files(
        RAW_DIR / "government", {".csv", ".json", ".pdf", ".xlsx"}
    )
    stats["academic_files"] = count_files(RAW_DIR / "academic", IMAGE_EXTS)
    stats["kaggle_files"] = count_files(RAW_DIR / "kaggle", IMAGE_EXTS)

    # City coverage from YouTube metadata
    stats["cities"] = get_city_coverage()

    # Ambulance images count
    stats["ambulance_images"] = count_ambulance_images()

    # Model status
    stats["models"] = get_model_status()

    return stats


def get_city_coverage():
    """Check which cities have data."""
    cities = {}
    youtube_dir = RAW_DIR / "youtube"
    if youtube_dir.exists():
        for city_dir in youtube_dir.iterdir():
            if city_dir.is_dir() and city_dir.name != "__pycache__":
                count = count_files(city_dir, VIDEO_EXTS | IMAGE_EXTS)
                if count > 0:
                    cities[city_dir.name] = count

    # Also check metadata
    meta_path = RAW_DIR / "youtube" / "metadata.json"
    if meta_path.exists():
        with open(meta_path, "r") as f:
            meta = json.load(f)
        for video in meta.get("videos", []):
            city = video.get("city", "Other")
            cities[city] = cities.get(city, 0) + 1

    return cities


def count_ambulance_images():
    """Count images containing ambulance labels."""
    count = 0
    labelled_dir = PROCESSED_DIR / "labelled"
    if labelled_dir.exists():
        for label_path in labelled_dir.rglob("*.txt"):
            if label_path.name == "classes.txt":
                continue
            try:
                with open(label_path, "r") as f:
                    for line in f:
                        if line.strip().startswith("5 "):
                            count += 1
                            break
            except Exception:
                pass
    return count


def get_model_status():
    """Check status of trained models."""
    models = []

    # Ambulance model
    amb_weights = (
        MODELS_DIR / "ambulance_detection"
        / "aimcrs_ambulance" / "weights" / "best.pt"
    )
    amb_eval = MODELS_DIR / "ambulance_detection" / "evaluation_results.json"

    amb_status = {
        "name": "Ambulance Detection",
        "trained": amb_weights.exists(),
        "accuracy": "N/A",
    }
    if amb_eval.exists():
        with open(amb_eval, "r") as f:
            data = json.load(f)
        amb_status["accuracy"] = f"{data.get('mAP50', 0):.1%}"
    models.append(amb_status)

    # Flow analysis
    flow_results = MODELS_DIR / "flow_analysis" / "results"
    models.append({
        "name": "Traffic Flow Analysis",
        "trained": flow_results.exists() and any(flow_results.iterdir()) if flow_results.exists() else False,
        "accuracy": "N/A",
    })

    # VILTICS comparison
    comp_report = MODELS_DIR / "viltics_comparison" / "comparison_report.json"
    models.append({
        "name": "VILTICS Comparison",
        "trained": comp_report.exists(),
        "accuracy": "See report",
    })

    return models


# ----- HTML TEMPLATE -----
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AIMCRS India Traffic Dataset — Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0a1a;
            color: #e0e0e0;
            padding: 20px;
        }
        .header {
            text-align: center;
            padding: 30px;
            background: linear-gradient(135deg, #1a1a3e 0%, #0d0d2b 100%);
            border-radius: 12px;
            margin-bottom: 20px;
            border: 1px solid #2a2a5e;
        }
        .header h1 { color: #ff4444; font-size: 28px; }
        .header p { color: #888; margin-top: 8px; }
        .patent { color: #666; font-size: 12px; margin-top: 10px; }

        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        .card {
            background: #1a1a2e;
            border: 1px solid #2a2a5e;
            border-radius: 10px;
            padding: 20px;
            text-align: center;
        }
        .card h3 { color: #888; font-size: 12px; text-transform: uppercase; }
        .card .number {
            font-size: 36px;
            font-weight: bold;
            color: #4ecdc4;
            margin: 10px 0;
        }
        .card .number.ambulance { color: #ff4444; }
        .card .number.highlight { color: #ffd700; }

        .section {
            background: #1a1a2e;
            border: 1px solid #2a2a5e;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
        }
        .section h2 {
            color: #4ecdc4;
            margin-bottom: 15px;
            font-size: 18px;
        }

        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 10px 15px;
            text-align: left;
            border-bottom: 1px solid #2a2a5e;
        }
        th { color: #888; font-size: 12px; text-transform: uppercase; }
        td { color: #e0e0e0; }

        .status-trained { color: #4ecdc4; }
        .status-pending { color: #ffd700; }

        .bar {
            height: 20px;
            background: #2a2a5e;
            border-radius: 10px;
            overflow: hidden;
            margin: 5px 0;
        }
        .bar-fill {
            height: 100%;
            background: linear-gradient(90deg, #4ecdc4, #44bbaa);
            border-radius: 10px;
        }

        .city-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 10px;
        }
        .city-card {
            background: #0d0d2b;
            border: 1px solid #2a2a5e;
            border-radius: 8px;
            padding: 15px;
            text-align: center;
        }
        .city-card h4 { color: #4ecdc4; }
        .city-card .count { font-size: 24px; color: #ffd700; }

        .footer {
            text-align: center;
            padding: 20px;
            color: #666;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>AIMCRS India Traffic Dataset</h1>
        <p>AI-Powered Emergency Vehicle Green Corridor System</p>
        <p class="patent">Patent Pending: IN202541120892 | Abheet Prem Manghnani</p>
        <div style="margin-top: 15px; display: flex; gap: 12px; justify-content: center;">
            <a href="/admin" style="background: #e74c3c; color: #fff; padding: 8px 20px; border-radius: 5px; text-decoration: none; font-size: 13px; font-weight: bold; letter-spacing: 1px;">GOD MODE</a>
            <a href="/simulation" style="background: #4ecdc4; color: #000; padding: 8px 20px; border-radius: 5px; text-decoration: none; font-size: 13px; font-weight: bold; letter-spacing: 1px;">SIMULATION</a>
        </div>
    </div>

    <!-- Main Counters -->
    <div class="grid">
        <div class="card">
            <h3>Total Images</h3>
            <div class="number highlight">{{ stats.total_images }}</div>
        </div>
        <div class="card">
            <h3>Videos Downloaded</h3>
            <div class="number">{{ stats.total_videos }}</div>
        </div>
        <div class="card">
            <h3>Labelled Images</h3>
            <div class="number">{{ stats.labelled_images }}</div>
        </div>
        <div class="card">
            <h3>Ambulance Images</h3>
            <div class="number ambulance">{{ stats.ambulance_images }}</div>
        </div>
        <div class="card">
            <h3>Augmented Images</h3>
            <div class="number">{{ stats.augmented_images }}</div>
        </div>
        <div class="card">
            <h3>Cities Covered</h3>
            <div class="number">{{ stats.cities | length }}</div>
        </div>
    </div>

    <!-- Data Source Breakdown -->
    <div class="section">
        <h2>Data Sources</h2>
        <table>
            <tr>
                <th>Source</th>
                <th>Files</th>
                <th>Coverage</th>
            </tr>
            <tr>
                <td>YouTube Traffic Videos</td>
                <td>{{ stats.youtube_videos }}</td>
                <td>
                    <div class="bar">
                        <div class="bar-fill" style="width: {{ [stats.youtube_videos * 2, 100] | min }}%"></div>
                    </div>
                </td>
            </tr>
            <tr>
                <td>Government Open Data</td>
                <td>{{ stats.government_files }}</td>
                <td>
                    <div class="bar">
                        <div class="bar-fill" style="width: {{ [stats.government_files * 5, 100] | min }}%"></div>
                    </div>
                </td>
            </tr>
            <tr>
                <td>Academic Datasets</td>
                <td>{{ stats.academic_files }}</td>
                <td>
                    <div class="bar">
                        <div class="bar-fill" style="width: {{ [stats.academic_files * 2, 100] | min }}%"></div>
                    </div>
                </td>
            </tr>
            <tr>
                <td>Kaggle Datasets</td>
                <td>{{ stats.kaggle_files }}</td>
                <td>
                    <div class="bar">
                        <div class="bar-fill" style="width: {{ [stats.kaggle_files * 2, 100] | min }}%"></div>
                    </div>
                </td>
            </tr>
        </table>
    </div>

    <!-- Training Dataset -->
    <div class="section">
        <h2>Training Dataset Split</h2>
        <div class="grid">
            <div class="card">
                <h3>Training (80%)</h3>
                <div class="number">{{ stats.train_images }}</div>
            </div>
            <div class="card">
                <h3>Validation (10%)</h3>
                <div class="number">{{ stats.val_images }}</div>
            </div>
            <div class="card">
                <h3>Test (10%)</h3>
                <div class="number">{{ stats.test_images }}</div>
            </div>
        </div>
    </div>

    <!-- City Coverage -->
    <div class="section">
        <h2>City Coverage</h2>
        <div class="city-grid">
            {% for city, count in stats.cities.items() %}
            <div class="city-card">
                <h4>{{ city }}</h4>
                <div class="count">{{ count }}</div>
                <small>files</small>
            </div>
            {% endfor %}
            {% if not stats.cities %}
            <p style="color: #888;">No city data yet. Run the YouTube downloader first.</p>
            {% endif %}
        </div>
    </div>

    <!-- Model Performance -->
    <div class="section">
        <h2>Model Performance</h2>
        <table>
            <tr>
                <th>Model</th>
                <th>Status</th>
                <th>Accuracy</th>
            </tr>
            {% for model in stats.models %}
            <tr>
                <td>{{ model.name }}</td>
                <td>
                    {% if model.trained %}
                    <span class="status-trained">Trained</span>
                    {% else %}
                    <span class="status-pending">Not yet trained</span>
                    {% endif %}
                </td>
                <td>{{ model.accuracy }}</td>
            </tr>
            {% endfor %}
        </table>
    </div>

    <!-- Vehicle Types -->
    <div class="section">
        <h2>Vehicle Types AIMCRS Detects</h2>
        <table>
            <tr><th>ID</th><th>Type</th><th>Priority</th></tr>
            <tr><td>5</td><td style="color: #ff4444; font-weight: bold;">Ambulance</td><td style="color: #ff4444;">HIGHEST</td></tr>
            <tr><td>0</td><td>Car</td><td>Standard</td></tr>
            <tr><td>1</td><td>Motorcycle / Two Wheeler</td><td>Standard</td></tr>
            <tr><td>2</td><td>Auto Rickshaw</td><td>India-specific</td></tr>
            <tr><td>3</td><td>Bus</td><td>Standard</td></tr>
            <tr><td>4</td><td>Truck</td><td>Standard</td></tr>
            <tr><td>6</td><td>Pedestrian</td><td>Safety</td></tr>
            <tr><td>7</td><td>Cycle</td><td>Standard</td></tr>
            <tr><td>8</td><td>Animal</td><td>India-specific</td></tr>
        </table>
    </div>

    <div class="footer">
        <p>AIMCRS India Traffic Dataset | Patent Pending IN202541120892</p>
        <p>Built by Abheet Prem Manghnani | Chennai, India</p>
        <p>Last updated: {{ now }}</p>
    </div>
</body>
</html>
"""


@app.route("/")
def dashboard():
    """Main dashboard page."""
    stats = get_stats()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return render_template_string(DASHBOARD_HTML, stats=stats, now=now)


@app.route("/api/stats")
def api_stats():
    """API endpoint returning stats as JSON."""
    stats = get_stats()
    # Convert Path objects to strings for JSON
    stats["cities"] = dict(stats.get("cities", {}))
    return json.dumps(stats, indent=2, default=str)


@app.route("/admin")
def admin_page():
    """God Mode — Admin Command Centre."""
    from flask import render_template
    return render_template("admin.html")


@app.route("/simulation")
def simulation_page():
    """Interactive Traffic & Green Corridor Simulation."""
    from flask import render_template
    return render_template("simulation.html")


def main():
    """Launch the dashboard."""
    print("=" * 50)
    print("  AIMCRS Dashboard")
    print("=" * 50)
    print()
    print("  Starting web dashboard...")
    print("  Open in your browser: http://localhost:5000")
    print("  Press Ctrl+C to stop")
    print()

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    logger.add(
        str(LOGS_DIR / "dashboard.log"),
        rotation="10 MB",
        level="INFO",
    )

    app.run(host="0.0.0.0", port=5000, debug=False)


if __name__ == "__main__":
    main()
