"""
AIMCRS God Mode — Admin API Routes
Flask Blueprint providing pipeline control, logs, model management, and system info.
"""

import os
import sys
import json
import time
import shutil
from pathlib import Path
from datetime import datetime

from flask import Blueprint, request, jsonify, render_template_string, Response

from .task_runner import runner, PIPELINE_STEPS

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RAW_DIR = PROJECT_ROOT / "raw"
PROCESSED_DIR = PROJECT_ROOT / "processed"
MODELS_DIR = PROJECT_ROOT / "models"
DATASETS_DIR = PROJECT_ROOT / "datasets"
LOGS_DIR = PROJECT_ROOT / "logs"

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp"}
VIDEO_EXTS = {".mp4", ".avi", ".mkv", ".mov", ".webm", ".flv"}


def _count_files(directory, extensions):
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


# ── Pipeline APIs ──────────────────────────────────────────

@admin_bp.route("/api/pipeline/steps")
def pipeline_steps():
    """List all pipeline steps with their current status."""
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


@admin_bp.route("/api/pipeline/status")
def pipeline_status():
    """Get output counts and status for each pipeline phase."""
    status = {
        "download": {
            "youtube_videos": _count_files(RAW_DIR / "youtube", VIDEO_EXTS),
            "government_files": _count_files(RAW_DIR / "government", {".csv", ".json", ".pdf", ".xlsx"}),
            "academic_files": _count_files(RAW_DIR / "academic", IMAGE_EXTS),
            "kaggle_files": _count_files(RAW_DIR / "kaggle", IMAGE_EXTS),
        },
        "process": {
            "unlabelled_images": _count_files(PROCESSED_DIR / "unlabelled", IMAGE_EXTS),
            "labelled_images": _count_files(PROCESSED_DIR / "labelled", IMAGE_EXTS),
            "augmented_images": _count_files(PROCESSED_DIR / "augmented", IMAGE_EXTS),
        },
        "train": {
            "train_images": _count_files(DATASETS_DIR / "train", IMAGE_EXTS),
            "val_images": _count_files(DATASETS_DIR / "validation", IMAGE_EXTS),
            "test_images": _count_files(DATASETS_DIR / "test", IMAGE_EXTS),
        },
        "models": {
            "ambulance_trained": (MODELS_DIR / "ambulance_detection" / "aimcrs_ambulance" / "weights" / "best.pt").exists(),
            "flow_trained": (MODELS_DIR / "flow_analysis" / "results").exists(),
            "viltics_done": (MODELS_DIR / "viltics_comparison" / "comparison_report.json").exists(),
        },
    }
    return jsonify(status)


@admin_bp.route("/api/pipeline/run/<step_name>", methods=["POST"])
def pipeline_run(step_name):
    """Start a pipeline step."""
    task_id, error = runner.run_step(step_name)
    if error:
        return jsonify({"error": error}), 400
    return jsonify({"task_id": task_id, "step": step_name})


@admin_bp.route("/api/pipeline/task/<task_id>")
def pipeline_task(task_id):
    """Get task status and output."""
    task = runner.get_task(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404
    return jsonify(task)


@admin_bp.route("/api/pipeline/tasks")
def pipeline_tasks():
    """List all tasks."""
    return jsonify(runner.get_all_tasks())


# ── Logs APIs ──────────────────────────────────────────────

@admin_bp.route("/api/logs/list")
def logs_list():
    """List available log files."""
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


@admin_bp.route("/api/logs/<filename>")
def logs_view(filename):
    """View last N lines of a log file."""
    # Prevent path traversal
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


@admin_bp.route("/api/logs/stream/<filename>")
def logs_stream(filename):
    """SSE endpoint for live log tailing."""
    if ".." in filename or "/" in filename:
        return jsonify({"error": "Invalid filename"}), 400
    log_path = LOGS_DIR / filename
    if not log_path.exists():
        return jsonify({"error": "Log not found"}), 404

    def generate():
        with open(log_path, "r") as f:
            # Start from end
            f.seek(0, 2)
            while True:
                line = f.readline()
                if line:
                    yield f"data: {line.rstrip()}\n\n"
                else:
                    time.sleep(1)

    return Response(generate(), mimetype="text/event-stream")


# ── Models APIs ────────────────────────────────────────────

@admin_bp.route("/api/models/status")
def models_status():
    """Detailed model status."""
    models = []

    # Ambulance model
    amb_weights = MODELS_DIR / "ambulance_detection" / "aimcrs_ambulance" / "weights" / "best.pt"
    amb_eval = MODELS_DIR / "ambulance_detection" / "evaluation_results.json"
    amb = {
        "name": "Ambulance Detection",
        "id": "ambulance",
        "trained": amb_weights.exists(),
        "weights_size_mb": round(amb_weights.stat().st_size / (1024 * 1024), 1) if amb_weights.exists() else 0,
        "accuracy": "N/A",
        "target": "95%+",
    }
    if amb_eval.exists():
        data = json.loads(amb_eval.read_text())
        amb["accuracy"] = f"{data.get('mAP50', 0):.1%}"
    models.append(amb)

    # Flow model
    flow_results = MODELS_DIR / "flow_analysis" / "results"
    models.append({
        "name": "Traffic Flow Analysis",
        "id": "flow",
        "trained": flow_results.exists() and any(flow_results.iterdir()) if flow_results.exists() else False,
        "accuracy": "N/A",
        "target": "85%+",
    })

    # VILTICS
    comp_report = MODELS_DIR / "viltics_comparison" / "comparison_report.json"
    models.append({
        "name": "VILTICS Comparison",
        "id": "viltics",
        "trained": comp_report.exists(),
        "accuracy": "See report",
        "target": "Benchmark",
    })

    return jsonify(models)


# ── System APIs ────────────────────────────────────────────

@admin_bp.route("/api/system/info")
def system_info():
    """System information."""
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


@admin_bp.route("/api/system/health")
def system_health():
    """Quick health check."""
    checks = {
        "project_root": PROJECT_ROOT.exists(),
        "raw_dir": RAW_DIR.exists(),
        "processed_dir": PROCESSED_DIR.exists(),
        "models_dir": MODELS_DIR.exists(),
        "datasets_dir": DATASETS_DIR.exists(),
        "logs_dir": LOGS_DIR.exists(),
    }

    # Check key dependencies
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


# ── Vehicle Classes API (shared with simulation) ──────────

@admin_bp.route("/api/vehicle-classes")
def vehicle_classes():
    """Return the 9 AIMCRS vehicle classes."""
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
