#!/usr/bin/env python3
"""
AIMCRS Traffic Demo — All-In-One Flask Application
===================================================
Dashboard + God Mode Admin + Simulation + Pipeline Control
Patent Pending: IN202541120892 | Abheet Prem Manghnani

Run:  python app.py
Open: http://localhost:5000
"""

import os
import sys
import json
import time
import shutil
import subprocess
import threading
import uuid
from pathlib import Path
from datetime import datetime
from collections import defaultdict, deque

try:
    from flask import (
        Flask, render_template, render_template_string,
        send_from_directory, request, jsonify, Response, Blueprint
    )
except ImportError:
    print("ERROR: Flask is not installed. Fix: pip install flask")
    sys.exit(1)

try:
    from loguru import logger
except ImportError:
    print("ERROR: loguru is not installed. Fix: pip install loguru")
    sys.exit(1)

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

# ── Project Paths ─────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent
if load_dotenv:
    load_dotenv(PROJECT_ROOT / ".env")

RAW_DIR = PROJECT_ROOT / "raw"
PROCESSED_DIR = PROJECT_ROOT / "processed"
MODELS_DIR = PROJECT_ROOT / "models"
DATASETS_DIR = PROJECT_ROOT / "datasets"
LOGS_DIR = PROJECT_ROOT / "logs"

VIDEO_EXTS = {".mp4", ".avi", ".mkv", ".mov", ".webm", ".flv"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp"}

# ── Flask App ─────────────────────────────────────────────
app = Flask(
    __name__,
    template_folder=str(PROJECT_ROOT / "templates"),
    static_folder=str(PROJECT_ROOT / "static"),
)


# ═══════════════════════════════════════════════════════════
#  PIPELINE TASK RUNNER
# ═══════════════════════════════════════════════════════════

PIPELINE_STEPS = {
    "youtube_download": {
        "script": "scripts/download/youtube_downloader.py",
        "name": "YouTube Downloader",
        "phase": "Download",
        "order": 1,
    },
    "government_download": {
        "script": "scripts/download/government_downloader.py",
        "name": "Government Data",
        "phase": "Download",
        "order": 2,
    },
    "academic_download": {
        "script": "scripts/download/academic_downloader.py",
        "name": "Academic Datasets",
        "phase": "Download",
        "order": 3,
    },
    "kaggle_download": {
        "script": "scripts/download/kaggle_downloader.py",
        "name": "Kaggle Datasets",
        "phase": "Download",
        "order": 4,
    },
    "roboflow_download": {
        "script": "scripts/download/roboflow_downloader.py",
        "name": "Roboflow Datasets",
        "phase": "Download",
        "order": 5,
    },
    "live_feeds": {
        "script": "scripts/download/live_feeds.py",
        "name": "Live Traffic Feeds",
        "phase": "Download",
        "order": 6,
    },
    "process": {
        "script": "scripts/process/process_pipeline.py",
        "name": "Process Pipeline",
        "phase": "Process",
        "order": 7,
    },
    "auto_label": {
        "script": "scripts/label/auto_label.py",
        "name": "Auto Labeller",
        "phase": "Label",
        "order": 8,
    },
    "augment": {
        "script": "scripts/process/augment.py",
        "name": "Data Augmentation",
        "phase": "Augment",
        "order": 9,
    },
    "train_ambulance": {
        "script": "scripts/train/train_ambulance.py",
        "name": "Train Ambulance Model",
        "phase": "Train",
        "order": 10,
    },
    "train_flow": {
        "script": "scripts/train/train_flow.py",
        "name": "Train Flow Model",
        "phase": "Train",
        "order": 11,
    },
    "viltics_comparison": {
        "script": "scripts/train/viltics_comparison.py",
        "name": "VILTICS Comparison",
        "phase": "Evaluate",
        "order": 12,
    },
}


class TaskRunner:
    """Manages pipeline task execution with real-time output capture."""

    def __init__(self):
        self.tasks = {}
        self.lock = threading.Lock()

    def run_step(self, step_name):
        if step_name not in PIPELINE_STEPS:
            return None, f"Unknown step: {step_name}"

        with self.lock:
            for tid, task in self.tasks.items():
                if task["step"] == step_name and task["status"] == "running":
                    return None, f"Step '{step_name}' is already running (task {tid})"

        step = PIPELINE_STEPS[step_name]
        script_path = PROJECT_ROOT / step["script"]

        if not script_path.exists():
            return None, f"Script not found: {step['script']}"

        task_id = str(uuid.uuid4())[:8]
        task_info = {
            "id": task_id,
            "step": step_name,
            "name": step["name"],
            "status": "running",
            "started_at": datetime.now().isoformat(),
            "finished_at": None,
            "exit_code": None,
            "output": deque(maxlen=500),
            "error": "",
        }

        with self.lock:
            self.tasks[task_id] = task_info

        thread = threading.Thread(
            target=self._execute, args=(task_id, script_path), daemon=True
        )
        thread.start()

        return task_id, None

    def _execute(self, task_id, script_path):
        try:
            proc = subprocess.Popen(
                [sys.executable, str(script_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=str(PROJECT_ROOT),
                text=True,
                bufsize=1,
            )

            with self.lock:
                self.tasks[task_id]["pid"] = proc.pid

            for line in proc.stdout:
                with self.lock:
                    self.tasks[task_id]["output"].append(line.rstrip())

            proc.wait()

            with self.lock:
                self.tasks[task_id]["status"] = (
                    "complete" if proc.returncode == 0 else "error"
                )
                self.tasks[task_id]["exit_code"] = proc.returncode
                self.tasks[task_id]["finished_at"] = datetime.now().isoformat()

        except Exception as e:
            with self.lock:
                self.tasks[task_id]["status"] = "error"
                self.tasks[task_id]["error"] = str(e)
                self.tasks[task_id]["finished_at"] = datetime.now().isoformat()

    def get_task(self, task_id):
        with self.lock:
            task = self.tasks.get(task_id)
            if not task:
                return None
            return {
                "id": task["id"],
                "step": task["step"],
                "name": task["name"],
                "status": task["status"],
                "started_at": task["started_at"],
                "finished_at": task["finished_at"],
                "exit_code": task["exit_code"],
                "output": list(task["output"]),
                "error": task["error"],
            }

    def get_all_tasks(self):
        with self.lock:
            return [
                {
                    "id": t["id"],
                    "step": t["step"],
                    "name": t["name"],
                    "status": t["status"],
                    "started_at": t["started_at"],
                    "finished_at": t["finished_at"],
                }
                for t in self.tasks.values()
            ]


runner = TaskRunner()


# ═══════════════════════════════════════════════════════════
#  STATS HELPERS
# ═══════════════════════════════════════════════════════════

def count_files(directory, extensions):
    if not directory.exists():
        return 0
    count = 0
    for ext in extensions:
        count += len(list(directory.rglob(f"*{ext}")))
    return count


def _dir_size_mb(directory):
    if not directory.exists():
        return 0
    total = sum(f.stat().st_size for f in directory.rglob("*") if f.is_file())
    return round(total / (1024 * 1024), 1)


def get_city_coverage():
    cities = {}
    youtube_dir = RAW_DIR / "youtube"
    if youtube_dir.exists():
        for city_dir in youtube_dir.iterdir():
            if city_dir.is_dir() and city_dir.name != "__pycache__":
                count = count_files(city_dir, VIDEO_EXTS | IMAGE_EXTS)
                if count > 0:
                    cities[city_dir.name] = count

    meta_path = RAW_DIR / "youtube" / "metadata.json"
    if meta_path.exists():
        with open(meta_path, "r") as f:
            meta = json.load(f)
        for video in meta.get("videos", []):
            city = video.get("city", "Other")
            cities[city] = cities.get(city, 0) + 1

    return cities


def count_ambulance_images():
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
    models = []

    amb_weights = (
        MODELS_DIR / "ambulance_detection"
        / "aimcrs_ambulance" / "weights" / "best.pt"
    )
    amb_eval = MODELS_DIR / "ambulance_detection" / "evaluation_results.json"

    amb_status = {
        "name": "Ambulance Detection",
        "id": "ambulance",
        "trained": amb_weights.exists(),
        "accuracy": "N/A",
        "target": "95%+",
        "weights_size_mb": round(amb_weights.stat().st_size / (1024 * 1024), 1) if amb_weights.exists() else 0,
    }
    if amb_eval.exists():
        with open(amb_eval, "r") as f:
            data = json.load(f)
        amb_status["accuracy"] = f"{data.get('mAP50', 0):.1%}"
    models.append(amb_status)

    flow_results = MODELS_DIR / "flow_analysis" / "results"
    models.append({
        "name": "Traffic Flow Analysis",
        "id": "flow",
        "trained": flow_results.exists() and any(flow_results.iterdir()) if flow_results.exists() else False,
        "accuracy": "N/A",
        "target": "85%+",
    })

    comp_report = MODELS_DIR / "viltics_comparison" / "comparison_report.json"
    models.append({
        "name": "VILTICS Comparison",
        "id": "viltics",
        "trained": comp_report.exists(),
        "accuracy": "See report",
        "target": "Benchmark",
    })

    return models


def get_stats():
    stats = {}
    stats["total_videos"] = count_files(RAW_DIR, VIDEO_EXTS)
    stats["raw_images"] = count_files(RAW_DIR, IMAGE_EXTS)
    stats["processed_images"] = count_files(PROCESSED_DIR, IMAGE_EXTS)
    stats["labelled_images"] = count_files(PROCESSED_DIR / "labelled", IMAGE_EXTS)
    stats["unlabelled_images"] = count_files(PROCESSED_DIR / "unlabelled", IMAGE_EXTS)
    stats["augmented_images"] = count_files(PROCESSED_DIR / "augmented", IMAGE_EXTS)
    stats["total_images"] = (
        stats["raw_images"] + stats["processed_images"] + stats["augmented_images"]
    )
    stats["train_images"] = count_files(DATASETS_DIR / "train", IMAGE_EXTS)
    stats["val_images"] = count_files(DATASETS_DIR / "validation", IMAGE_EXTS)
    stats["test_images"] = count_files(DATASETS_DIR / "test", IMAGE_EXTS)
    stats["youtube_videos"] = count_files(RAW_DIR / "youtube", VIDEO_EXTS)
    stats["government_files"] = count_files(
        RAW_DIR / "government", {".csv", ".json", ".pdf", ".xlsx"}
    )
    stats["academic_files"] = count_files(RAW_DIR / "academic", IMAGE_EXTS)
    stats["kaggle_files"] = count_files(RAW_DIR / "kaggle", IMAGE_EXTS)
    stats["cities"] = get_city_coverage()
    stats["ambulance_images"] = count_ambulance_images()
    stats["models"] = get_model_status()
    return stats


# ═══════════════════════════════════════════════════════════
#  DASHBOARD ROUTES
# ═══════════════════════════════════════════════════════════

@app.route("/")
def dashboard():
    stats = get_stats()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return render_template("dashboard.html", stats=stats, now=now)


@app.route("/api/stats")
def api_stats():
    stats = get_stats()
    stats["cities"] = dict(stats.get("cities", {}))
    return jsonify(stats)


@app.route("/admin")
def admin_page():
    return render_template("admin.html")


@app.route("/simulation")
def simulation_page():
    return render_template("simulation.html")


# ═══════════════════════════════════════════════════════════
#  ADMIN API ROUTES (God Mode)
# ═══════════════════════════════════════════════════════════

@app.route("/admin/api/pipeline/steps")
def pipeline_steps():
    steps = []
    for key, step in sorted(PIPELINE_STEPS.items(), key=lambda x: x[1]["order"]):
        script_path = PROJECT_ROOT / step["script"]
        steps.append({
            "id": key,
            "name": step["name"],
            "phase": step["phase"],
            "order": step["order"],
            "script_exists": script_path.exists(),
        })
    return jsonify(steps)


@app.route("/admin/api/pipeline/status")
def pipeline_status():
    status = {
        "download": {
            "youtube_videos": count_files(RAW_DIR / "youtube", VIDEO_EXTS),
            "government_files": count_files(RAW_DIR / "government", {".csv", ".json", ".pdf", ".xlsx"}),
            "academic_files": count_files(RAW_DIR / "academic", IMAGE_EXTS),
            "kaggle_files": count_files(RAW_DIR / "kaggle", IMAGE_EXTS),
        },
        "process": {
            "unlabelled_images": count_files(PROCESSED_DIR / "unlabelled", IMAGE_EXTS),
            "labelled_images": count_files(PROCESSED_DIR / "labelled", IMAGE_EXTS),
            "augmented_images": count_files(PROCESSED_DIR / "augmented", IMAGE_EXTS),
        },
        "train": {
            "train_images": count_files(DATASETS_DIR / "train", IMAGE_EXTS),
            "val_images": count_files(DATASETS_DIR / "validation", IMAGE_EXTS),
            "test_images": count_files(DATASETS_DIR / "test", IMAGE_EXTS),
        },
        "models": {
            "ambulance_trained": (MODELS_DIR / "ambulance_detection" / "aimcrs_ambulance" / "weights" / "best.pt").exists(),
            "flow_trained": (MODELS_DIR / "flow_analysis" / "results").exists(),
            "viltics_done": (MODELS_DIR / "viltics_comparison" / "comparison_report.json").exists(),
        },
    }
    return jsonify(status)


@app.route("/admin/api/pipeline/run/<step_name>", methods=["POST"])
def pipeline_run(step_name):
    task_id, error = runner.run_step(step_name)
    if error:
        return jsonify({"error": error}), 400
    return jsonify({"task_id": task_id, "step": step_name})


@app.route("/admin/api/pipeline/task/<task_id>")
def pipeline_task(task_id):
    task = runner.get_task(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404
    return jsonify(task)


@app.route("/admin/api/pipeline/tasks")
def pipeline_tasks():
    return jsonify(runner.get_all_tasks())


# ── Logs APIs ─────────────────────────────────────────────

@app.route("/admin/api/logs/list")
def logs_list():
    if not LOGS_DIR.exists():
        return jsonify([])
    logs = []
    for f in sorted(LOGS_DIR.glob("*.log")):
        logs.append({
            "name": f.name,
            "size_kb": round(f.stat().st_size / 1024, 1),
            "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
        })
    return jsonify(logs)


@app.route("/admin/api/logs/<filename>")
def logs_view(filename):
    if ".." in filename or "/" in filename:
        return jsonify({"error": "Invalid filename"}), 400
    log_path = LOGS_DIR / filename
    if not log_path.exists():
        return jsonify({"error": "Log not found"}), 404
    tail = int(request.args.get("tail", 200))
    lines = log_path.read_text().splitlines()
    return jsonify({
        "name": filename,
        "total_lines": len(lines),
        "lines": lines[-tail:],
    })


@app.route("/admin/api/logs/stream/<filename>")
def logs_stream(filename):
    if ".." in filename or "/" in filename:
        return jsonify({"error": "Invalid filename"}), 400
    log_path = LOGS_DIR / filename
    if not log_path.exists():
        return jsonify({"error": "Log not found"}), 404

    def generate():
        with open(log_path, "r") as f:
            f.seek(0, 2)
            while True:
                line = f.readline()
                if line:
                    yield f"data: {line.rstrip()}\n\n"
                else:
                    time.sleep(1)

    return Response(generate(), mimetype="text/event-stream")


# ── Models APIs ───────────────────────────────────────────

@app.route("/admin/api/models/status")
def models_status():
    return jsonify(get_model_status())


# ── System APIs ───────────────────────────────────────────

@app.route("/admin/api/system/info")
def system_info():
    disk = shutil.disk_usage("/")
    gpu_available = False
    try:
        import torch
        gpu_available = torch.cuda.is_available()
    except ImportError:
        pass

    return jsonify({
        "python_version": sys.version,
        "project_root": str(PROJECT_ROOT),
        "disk_total_gb": round(disk.total / (1024**3), 1),
        "disk_used_gb": round(disk.used / (1024**3), 1),
        "disk_free_gb": round(disk.free / (1024**3), 1),
        "gpu_available": gpu_available,
        "data_sizes": {
            "raw_mb": _dir_size_mb(RAW_DIR),
            "processed_mb": _dir_size_mb(PROCESSED_DIR),
            "models_mb": _dir_size_mb(MODELS_DIR),
            "datasets_mb": _dir_size_mb(DATASETS_DIR),
            "logs_mb": _dir_size_mb(LOGS_DIR),
        },
    })


@app.route("/admin/api/system/health")
def system_health():
    checks = {
        "project_root": PROJECT_ROOT.exists(),
        "raw_dir": RAW_DIR.exists(),
        "processed_dir": PROCESSED_DIR.exists(),
        "models_dir": MODELS_DIR.exists(),
        "datasets_dir": DATASETS_DIR.exists(),
        "logs_dir": LOGS_DIR.exists(),
    }
    deps = {}
    for pkg in ["flask", "ultralytics", "cv2", "torch", "numpy", "PIL"]:
        try:
            __import__(pkg)
            deps[pkg] = True
        except ImportError:
            deps[pkg] = False

    return jsonify({
        "status": "healthy" if all(checks.values()) else "degraded",
        "directories": checks,
        "dependencies": deps,
        "timestamp": datetime.now().isoformat(),
    })


@app.route("/admin/api/vehicle-classes")
def vehicle_classes():
    classes = [
        {"id": 0, "name": "Car", "color": "#3498db", "priority": "standard"},
        {"id": 1, "name": "Motorcycle", "color": "#e67e22", "priority": "standard"},
        {"id": 2, "name": "Auto Rickshaw", "color": "#f1c40f", "priority": "india-specific"},
        {"id": 3, "name": "Bus", "color": "#27ae60", "priority": "standard"},
        {"id": 4, "name": "Truck", "color": "#8e44ad", "priority": "standard"},
        {"id": 5, "name": "Ambulance", "color": "#e74c3c", "priority": "HIGHEST"},
        {"id": 6, "name": "Pedestrian", "color": "#1abc9c", "priority": "safety"},
        {"id": 7, "name": "Cycle", "color": "#95a5a6", "priority": "standard"},
        {"id": 8, "name": "Animal", "color": "#d35400", "priority": "india-specific"},
    ]
    return jsonify(classes)


# ═══════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════

def main():
    print("=" * 50)
    print("  AIMCRS Traffic Demo")
    print("  All-In-One Dashboard")
    print("=" * 50)
    print()
    print("  Pages:")
    print("    http://localhost:5000/            Dashboard")
    print("    http://localhost:5000/admin        God Mode")
    print("    http://localhost:5000/simulation   Simulation")
    print()
    print("  Press Ctrl+C to stop")
    print()

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    logger.add(str(LOGS_DIR / "app.log"), rotation="10 MB", level="INFO")

    app.run(host="0.0.0.0", port=5000, debug=False)


if __name__ == "__main__":
    main()
