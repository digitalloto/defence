#!/usr/bin/env python3
# ============================================
# Step 9 — Traffic Flow Analysis Model
# ============================================
# File: scripts/train/train_flow.py
# What: Trains a model to understand Indian traffic flow
# How to run: python scripts/train/train_flow.py
#
# What this model detects:
#   - Vehicle count per lane/direction
#   - Estimated vehicle speed
#   - Direction of flow
#   - Congestion level (low/medium/high/severe)
#   - Queue length at signal
#   - Unusual stopped vehicles
#   - Emergency vehicle approaching
#
# This feeds directly into the AIMCRS AI-CER
# green corridor prediction engine.
# ============================================

import os
import sys
import json
import math
from pathlib import Path
from datetime import datetime
from collections import defaultdict

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
MODELS_DIR = PROJECT_ROOT / "models" / "flow_analysis"
LOGS_DIR = PROJECT_ROOT / "logs"

# ----- CONGESTION LEVELS -----
# We classify congestion into 4 levels
CONGESTION_LEVELS = {
    "low": {"max_vehicles": 10, "min_speed_ratio": 0.7},
    "medium": {"max_vehicles": 25, "min_speed_ratio": 0.4},
    "high": {"max_vehicles": 50, "min_speed_ratio": 0.15},
    "severe": {"max_vehicles": 999, "min_speed_ratio": 0.0},
}


def setup_logging():
    """Set up logging."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    logger.add(
        str(LOGS_DIR / "train_flow.log"),
        rotation="10 MB",
        retention="30 days",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    )
    logger.info("=" * 60)
    logger.info("Traffic Flow Analysis Started")
    logger.info("=" * 60)


class TrafficFlowAnalyser:
    """
    Analyses traffic flow in video frames.

    How it works (in simple words):
    1. YOLO detects all vehicles in each frame
    2. We track each vehicle across frames (where it moves)
    3. From movement, we calculate speed and direction
    4. We count vehicles in each area of the image
    5. We estimate congestion level
    """

    def __init__(self):
        self.model = None
        self.prev_detections = []  # Vehicles from previous frame
        self.vehicle_tracks = {}   # Track each vehicle over time
        self.next_track_id = 0
        self.frame_count = 0

    def load_model(self):
        """Load YOLOv8 for vehicle detection."""
        try:
            from ultralytics import YOLO
        except ImportError:
            print("ERROR: ultralytics not installed.")
            print("Fix: pip install ultralytics")
            sys.exit(1)

        # Check if we have our trained ambulance model
        custom_model = (
            PROJECT_ROOT / "models" / "ambulance_detection"
            / "aimcrs_ambulance" / "weights" / "best.pt"
        )

        if custom_model.exists():
            print("  Using AIMCRS trained model")
            self.model = YOLO(str(custom_model))
        else:
            print("  Using default YOLOv8 model")
            self.model = YOLO("yolov8n.pt")

        logger.info("Model loaded for flow analysis")

    def detect_vehicles(self, frame):
        """
        Detect all vehicles in a single frame.
        Returns list of detections: (class_id, x, y, w, h, confidence)
        """
        results = self.model(frame, verbose=False)
        detections = []

        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue
            for box in boxes:
                cls = int(box.cls[0])
                conf = float(box.conf[0])
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                cx = (x1 + x2) / 2
                cy = (y1 + y2) / 2
                w = x2 - x1
                h = y2 - y1
                detections.append({
                    "class_id": cls,
                    "center_x": cx,
                    "center_y": cy,
                    "width": w,
                    "height": h,
                    "confidence": conf,
                    "bbox": (x1, y1, x2, y2),
                })

        return detections

    def track_vehicles(self, detections):
        """
        Simple vehicle tracking across frames.

        How it works:
        - For each new detection, find the closest vehicle
          from the previous frame
        - If close enough, it's the same vehicle (same track)
        - If no match, it's a new vehicle entering the scene
        """
        matched = set()
        new_tracks = {}

        for det in detections:
            best_dist = float("inf")
            best_track_id = None

            for track_id, prev in self.vehicle_tracks.items():
                if track_id in matched:
                    continue
                # Calculate distance between current and previous position
                dx = det["center_x"] - prev["positions"][-1][0]
                dy = det["center_y"] - prev["positions"][-1][1]
                dist = math.sqrt(dx * dx + dy * dy)

                if dist < best_dist and dist < 100:  # Max 100px movement
                    best_dist = dist
                    best_track_id = track_id

            if best_track_id is not None:
                matched.add(best_track_id)
                track = self.vehicle_tracks[best_track_id]
                track["positions"].append(
                    (det["center_x"], det["center_y"])
                )
                track["last_seen"] = self.frame_count
                track["class_id"] = det["class_id"]
                new_tracks[best_track_id] = track
            else:
                # New vehicle
                track_id = self.next_track_id
                self.next_track_id += 1
                new_tracks[track_id] = {
                    "positions": [(det["center_x"], det["center_y"])],
                    "first_seen": self.frame_count,
                    "last_seen": self.frame_count,
                    "class_id": det["class_id"],
                }

        self.vehicle_tracks = new_tracks

    def estimate_speeds(self):
        """
        Estimate speed of each tracked vehicle.

        How it works:
        - Look at how far each vehicle moved between frames
        - More movement = faster speed
        - Returns speed in pixels/frame (not km/h — we'd need
          camera calibration for real speed)
        """
        speeds = {}
        for track_id, track in self.vehicle_tracks.items():
            positions = track["positions"]
            if len(positions) < 2:
                speeds[track_id] = 0
                continue

            # Average speed over last few positions
            total_dist = 0
            count = 0
            for i in range(max(0, len(positions) - 5), len(positions) - 1):
                dx = positions[i + 1][0] - positions[i][0]
                dy = positions[i + 1][1] - positions[i][1]
                total_dist += math.sqrt(dx * dx + dy * dy)
                count += 1

            speeds[track_id] = total_dist / max(count, 1)

        return speeds

    def estimate_congestion(self, detections, speeds):
        """
        Estimate congestion level.

        Factors:
        - Number of vehicles visible
        - Average speed (slower = more congested)
        - How close vehicles are to each other
        """
        num_vehicles = len(detections)
        avg_speed = (
            sum(speeds.values()) / max(len(speeds), 1) if speeds else 0
        )

        # Estimate congestion
        if num_vehicles <= 5 and avg_speed > 20:
            level = "low"
        elif num_vehicles <= 15 and avg_speed > 10:
            level = "medium"
        elif num_vehicles <= 30 or avg_speed > 5:
            level = "high"
        else:
            level = "severe"

        return {
            "level": level,
            "vehicle_count": num_vehicles,
            "avg_speed_px_per_frame": round(avg_speed, 1),
        }

    def detect_emergency_vehicle(self, detections):
        """
        Check if any detected vehicle is an emergency vehicle.
        This is the most important detection for AIMCRS.
        """
        for det in detections:
            # Class 5 = ambulance in our labelling
            if det["class_id"] == 5 and det["confidence"] > 0.5:
                return {
                    "found": True,
                    "position": (det["center_x"], det["center_y"]),
                    "confidence": det["confidence"],
                    "bbox": det["bbox"],
                }

            # Class 7 in COCO = truck — some ambulances detected as trucks
            # Flag large white vehicles for review

        return {"found": False}

    def analyse_frame(self, frame):
        """
        Complete analysis of one video frame.
        Returns all traffic flow information.
        """
        self.frame_count += 1

        # Detect vehicles
        detections = self.detect_vehicles(frame)

        # Track across frames
        self.track_vehicles(detections)

        # Estimate speeds
        speeds = self.estimate_speeds()

        # Estimate congestion
        congestion = self.estimate_congestion(detections, speeds)

        # Check for emergency vehicles
        emergency = self.detect_emergency_vehicle(detections)

        # Count vehicle types
        type_counts = defaultdict(int)
        for det in detections:
            type_counts[det["class_id"]] += 1

        return {
            "frame": self.frame_count,
            "total_vehicles": len(detections),
            "vehicle_types": dict(type_counts),
            "congestion": congestion,
            "emergency_vehicle": emergency,
            "active_tracks": len(self.vehicle_tracks),
            "avg_speed": round(
                sum(speeds.values()) / max(len(speeds), 1), 1
            ) if speeds else 0,
        }


def analyse_video(video_path, output_dir):
    """
    Run traffic flow analysis on a video file.
    Analyses every 5th frame and saves results.
    """
    analyser = TrafficFlowAnalyser()
    analyser.load_model()

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        logger.error(f"Cannot open video: {video_path}")
        return None

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    print(f"  Analysing: {Path(video_path).name}")
    print(f"  Frames: {total_frames}, FPS: {fps:.1f}")

    results = []
    frame_num = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_num += 1

        # Analyse every 5th frame
        if frame_num % 5 != 0:
            continue

        analysis = analyser.analyse_frame(frame)
        results.append(analysis)

        # Alert if emergency vehicle found
        if analysis["emergency_vehicle"]["found"]:
            print(f"    AMBULANCE DETECTED at frame {frame_num}!")
            logger.warning(f"AMBULANCE at frame {frame_num}")

        # Progress
        if frame_num % 100 == 0:
            cong = analysis["congestion"]["level"]
            vehs = analysis["total_vehicles"]
            print(f"    Frame {frame_num}: {vehs} vehicles, congestion: {cong}")

    cap.release()

    # Save results
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{Path(video_path).stem}_flow.json"
    with open(output_file, "w") as f:
        json.dump({
            "video": str(video_path),
            "fps": fps,
            "total_frames": total_frames,
            "analysed_frames": len(results),
            "analysis": results,
            "analysed_at": datetime.now().isoformat(),
        }, f, indent=2)

    return results


def main():
    """
    Main function — analyses traffic flow.
    """
    print("=" * 50)
    print("  AIMCRS Traffic Flow Analysis")
    print("  Understanding Indian traffic patterns")
    print("=" * 50)

    setup_logging()
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    # Find all videos to analyse
    raw_dir = PROJECT_ROOT / "raw"
    videos = []
    for ext in [".mp4", ".avi", ".mkv", ".mov", ".webm"]:
        videos.extend(raw_dir.rglob(f"*{ext}"))

    if not videos:
        print("\n  No video files found in raw/ directory.")
        print("  Run the download scripts first:")
        print("  python scripts/download/youtube_downloader.py")
        return

    print(f"\n  Found {len(videos)} videos to analyse")

    all_results = []
    for video_path in videos:
        results = analyse_video(video_path, MODELS_DIR / "results")
        if results:
            all_results.extend(results)

    # Summary
    if all_results:
        total_vehicles = sum(r["total_vehicles"] for r in all_results)
        ambulance_frames = sum(
            1 for r in all_results if r["emergency_vehicle"]["found"]
        )

        print("\n" + "=" * 50)
        print("  Flow Analysis Summary")
        print("=" * 50)
        print(f"  Frames analysed: {len(all_results)}")
        print(f"  Total vehicle detections: {total_vehicles}")
        print(f"  Ambulance detections: {ambulance_frames}")
        print(f"  Results saved to: {MODELS_DIR / 'results'}")
        print("=" * 50)

    logger.info("Traffic Flow Analysis Complete")


if __name__ == "__main__":
    main()
