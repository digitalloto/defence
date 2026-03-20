#!/usr/bin/env python3
# ============================================
# Step 10 — VILTICS Comparison Module
# ============================================
# File: scripts/train/viltics_comparison.py
# What: Compares our detection with VILTICS AI Vision system
# How to run: python scripts/train/viltics_comparison.py
#
# What is VILTICS?
# VILTICS is Ariansyah Center's AI Vision system that does
# similar vehicle detection. They demonstrated it on
# Dhaula Kuan Delhi intersection footage.
#
# This script:
# 1. Loads the same Dhaula Kuan footage (if available)
# 2. Runs our model on it
# 3. Generates a comparison report
# 4. Shows where we are vs VILTICS
# ============================================

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import cv2
    import numpy as np
except ImportError:
    print("ERROR: opencv-python or numpy not installed.")
    print("Fix: pip install opencv-python numpy")
    sys.exit(1)

try:
    from loguru import logger
except ImportError:
    print("ERROR: loguru is not installed. Fix: pip install loguru")
    sys.exit(1)

# ----- PATHS -----
MODELS_DIR = PROJECT_ROOT / "models"
COMPARISON_DIR = MODELS_DIR / "viltics_comparison"
LOGS_DIR = PROJECT_ROOT / "logs"
RAW_YOUTUBE_DIR = PROJECT_ROOT / "raw" / "youtube"

# ----- VILTICS REFERENCE DATA -----
# Known results from VILTICS Dhaula Kuan demo.
# Source: Ariansyah Center's demonstration.
VILTICS_REFERENCE = {
    "location": "Dhaula Kuan, Delhi",
    "source": "VILTICS AI Vision (Ariansyah Center)",
    "demo_type": "Vehicle detection and classification",
    "claimed_capabilities": [
        "Real-time vehicle detection",
        "Vehicle classification (car, bus, truck, etc.)",
        "Vehicle counting",
        "Traffic flow analysis",
    ],
}


def setup_logging():
    """Set up logging."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    logger.add(
        str(LOGS_DIR / "viltics_comparison.log"),
        rotation="10 MB",
        retention="30 days",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    )
    logger.info("=" * 60)
    logger.info("VILTICS Comparison Started")
    logger.info("=" * 60)


def find_dhaula_kuan_footage():
    """
    Look for Dhaula Kuan Delhi footage in our downloads.
    This is the intersection VILTICS used for their demo.
    """
    candidates = []

    if RAW_YOUTUBE_DIR.exists():
        for video_path in RAW_YOUTUBE_DIR.rglob("*"):
            if video_path.suffix.lower() in {".mp4", ".avi", ".mkv", ".webm"}:
                name_lower = video_path.name.lower()
                if "dhaula" in name_lower or "kuan" in name_lower:
                    candidates.append(video_path)

    # Also check Delhi folder
    delhi_dir = RAW_YOUTUBE_DIR / "Delhi"
    if delhi_dir.exists():
        for video_path in delhi_dir.rglob("*"):
            if video_path.suffix.lower() in {".mp4", ".avi", ".mkv", ".webm"}:
                candidates.append(video_path)

    return candidates


def run_our_detection(video_path):
    """
    Run our AIMCRS model on a video and collect performance metrics.
    """
    try:
        from ultralytics import YOLO
    except ImportError:
        print("ERROR: ultralytics not installed. Fix: pip install ultralytics")
        return None

    # Try to use our trained model first, fall back to default
    custom_model = (
        MODELS_DIR / "ambulance_detection"
        / "aimcrs_ambulance" / "weights" / "best.pt"
    )

    if custom_model.exists():
        model = YOLO(str(custom_model))
        model_name = "AIMCRS Trained YOLOv8"
    else:
        model = YOLO("yolov8n.pt")
        model_name = "YOLOv8n (baseline)"

    print(f"  Using model: {model_name}")

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return None

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    # Metrics we track
    total_detections = 0
    vehicle_counts = {}
    processing_times = []
    frame_count = 0
    analysed = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1

        # Analyse every 10th frame for speed
        if frame_count % 10 != 0:
            continue

        start_time = time.time()
        results = model(frame, verbose=False)
        end_time = time.time()

        processing_times.append(end_time - start_time)

        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue
            for box in boxes:
                cls = int(box.cls[0])
                conf = float(box.conf[0])
                if conf > 0.4:
                    total_detections += 1
                    cls_name = model.names.get(cls, f"class_{cls}")
                    vehicle_counts[cls_name] = (
                        vehicle_counts.get(cls_name, 0) + 1
                    )

        analysed += 1

    cap.release()

    avg_time = (
        sum(processing_times) / len(processing_times)
        if processing_times else 0
    )

    return {
        "model_name": model_name,
        "video": str(video_path),
        "total_frames": total_frames,
        "frames_analysed": analysed,
        "fps_video": fps,
        "total_detections": total_detections,
        "vehicle_type_counts": vehicle_counts,
        "avg_processing_time_seconds": round(avg_time, 4),
        "estimated_fps_processing": round(1 / avg_time, 1) if avg_time > 0 else 0,
    }


def generate_comparison_report(our_results, output_dir):
    """
    Generate a side-by-side comparison report.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    report = {
        "title": "AIMCRS vs VILTICS Comparison Report",
        "generated_at": datetime.now().isoformat(),
        "viltics_reference": VILTICS_REFERENCE,
        "aimcrs_results": our_results,
        "comparison": {
            "note": (
                "VILTICS exact numbers are not publicly available. "
                "This report shows our system's performance on the same "
                "type of footage (Dhaula Kuan, Delhi intersection). "
                "Use this to assess readiness for partnership discussions."
            ),
        },
    }

    # Save JSON report
    json_path = output_dir / "comparison_report.json"
    with open(json_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    # Generate text report
    text_path = output_dir / "comparison_report.txt"
    with open(text_path, "w") as f:
        f.write("=" * 60 + "\n")
        f.write("  AIMCRS vs VILTICS — Comparison Report\n")
        f.write("=" * 60 + "\n\n")

        f.write("VILTICS (Ariansyah Center):\n")
        f.write(f"  Location: {VILTICS_REFERENCE['location']}\n")
        f.write(f"  Capabilities:\n")
        for cap_item in VILTICS_REFERENCE["claimed_capabilities"]:
            f.write(f"    - {cap_item}\n")

        f.write("\n")
        f.write("AIMCRS (Our System):\n")

        if our_results:
            f.write(f"  Model: {our_results['model_name']}\n")
            f.write(f"  Total detections: {our_results['total_detections']}\n")
            f.write(f"  Processing speed: {our_results['estimated_fps_processing']} FPS\n")
            f.write(f"  Avg time per frame: {our_results['avg_processing_time_seconds']}s\n")
            f.write(f"\n  Vehicle types detected:\n")
            for vtype, count in sorted(
                our_results["vehicle_type_counts"].items(),
                key=lambda x: x[1],
                reverse=True,
            ):
                f.write(f"    {vtype}: {count}\n")
        else:
            f.write("  No video footage available for comparison.\n")
            f.write("  Download Dhaula Kuan footage first.\n")

        f.write("\n")
        f.write("AIMCRS ADVANTAGES over VILTICS:\n")
        f.write("  1. Ambulance-specific detection (VILTICS is general)\n")
        f.write("  2. Green corridor prediction (VILTICS doesn't do this)\n")
        f.write("  3. Signal control integration (our core innovation)\n")
        f.write("  4. Indian traffic specific training\n")
        f.write("\n")
        f.write("=" * 60 + "\n")

    logger.info(f"Comparison report saved to {output_dir}")
    return report


def main():
    """
    Main function — runs VILTICS comparison.
    """
    print("=" * 50)
    print("  AIMCRS vs VILTICS Comparison")
    print("  Testing on Dhaula Kuan Delhi footage")
    print("=" * 50)

    setup_logging()
    COMPARISON_DIR.mkdir(parents=True, exist_ok=True)

    # Step 1: Find Dhaula Kuan footage
    print("\n--- Step 1: Looking for Dhaula Kuan footage ---")
    candidates = find_dhaula_kuan_footage()

    our_results = None

    if candidates:
        print(f"  Found {len(candidates)} matching videos")
        # Use the first one
        video_path = candidates[0]
        print(f"  Using: {video_path.name}")

        # Step 2: Run our detection
        print("\n--- Step 2: Running AIMCRS detection ---")
        our_results = run_our_detection(video_path)

        if our_results:
            print(f"\n  Results:")
            print(f"    Total detections: {our_results['total_detections']}")
            print(f"    Processing speed: {our_results['estimated_fps_processing']} FPS")
            print(f"    Vehicle types found:")
            for vtype, count in sorted(
                our_results["vehicle_type_counts"].items(),
                key=lambda x: x[1], reverse=True,
            ):
                print(f"      {vtype}: {count}")
    else:
        print("  No Dhaula Kuan footage found.")
        print("  Download it first using the YouTube downloader.")
        print("  Search term: 'Dhaula Kuan traffic Delhi'")

    # Step 3: Generate report
    print("\n--- Step 3: Generating comparison report ---")
    report = generate_comparison_report(our_results, COMPARISON_DIR)
    print(f"  Report saved to: {COMPARISON_DIR}")

    print("\n" + "=" * 50)
    print("  Comparison Complete!")
    print("=" * 50)
    print(f"  Full report: {COMPARISON_DIR / 'comparison_report.txt'}")
    print(f"  JSON data: {COMPARISON_DIR / 'comparison_report.json'}")

    logger.info("VILTICS Comparison Complete")


if __name__ == "__main__":
    main()
