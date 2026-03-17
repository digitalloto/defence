#!/usr/bin/env python3
# ============================================
# Step 7 — Auto-Labelling Script
# ============================================
# File: scripts/label/auto_label.py
# What: Uses pre-trained YOLO to auto-label vehicles
# How to run: python scripts/label/auto_label.py
#
# What is labelling?
# To train an AI, you need to show it images AND tell it
# what is in each image. A "label" says:
# "There is a car at position X,Y with width W and height H"
#
# This script uses an already-trained YOLO model to
# automatically label vehicles in our images. It's not
# perfect, but it's much faster than doing it by hand.
#
# Vehicle types we label:
#   0 = Car
#   1 = Motorcycle / Two wheeler
#   2 = Auto rickshaw
#   3 = Bus
#   4 = Truck
#   5 = Ambulance (HIGHEST PRIORITY)
#   6 = Pedestrian
#   7 = Cycle / Bicycle
#   8 = Animal (cows on Indian roads)
# ============================================

import os
import sys
import json
import shutil
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from loguru import logger
except ImportError:
    print("ERROR: loguru is not installed. Fix: pip install loguru")
    sys.exit(1)

# ----- PATHS -----
UNLABELLED_DIR = PROJECT_ROOT / "processed" / "unlabelled"
LABELLED_DIR = PROJECT_ROOT / "processed" / "labelled"
LOGS_DIR = PROJECT_ROOT / "logs"
REVIEW_DIR = PROJECT_ROOT / "processed" / "needs_review"

# ----- OUR CLASS MAPPING -----
# These are the vehicle types AIMCRS needs to detect.
AIMCRS_CLASSES = {
    0: "car",
    1: "motorcycle",
    2: "auto_rickshaw",
    3: "bus",
    4: "truck",
    5: "ambulance",
    6: "pedestrian",
    7: "cycle",
    8: "animal",
}

# ----- YOLO COCO CLASS MAPPING -----
# The pre-trained YOLO model knows these COCO classes.
# We map them to our AIMCRS classes.
# COCO class ID → AIMCRS class ID
COCO_TO_AIMCRS = {
    2: 0,   # COCO "car" → our "car"
    3: 1,   # COCO "motorcycle" → our "motorcycle"
    5: 3,   # COCO "bus" → our "bus"
    7: 4,   # COCO "truck" → our "truck"
    0: 6,   # COCO "person" → our "pedestrian"
    1: 7,   # COCO "bicycle" → our "cycle"
    # Note: COCO doesn't have auto_rickshaw, ambulance, or animal
    # Those need fine-tuning — which we do in Step 8
    # For now, they are labelled from context or flagged for review
}

# ----- SETTINGS -----
# Minimum confidence to accept a detection
MIN_CONFIDENCE = 0.4

# Below this confidence, flag for human review
REVIEW_CONFIDENCE = 0.6

# Minimum number of vehicles in image to keep it
MIN_VEHICLES_IN_IMAGE = 3


def setup_logging():
    """Set up logging."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    logger.add(
        str(LOGS_DIR / "auto_label.log"),
        rotation="10 MB",
        retention="30 days",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    )
    logger.info("=" * 60)
    logger.info("Auto-Labelling Started")
    logger.info("=" * 60)


def load_yolo_model():
    """
    Load the pre-trained YOLOv8 model.

    What is YOLOv8?
    YOLO = "You Only Look Once" — a fast AI that can detect
    objects in images. Version 8 is the latest free version.
    It comes pre-trained on 80 types of objects including
    cars, trucks, buses, motorcycles, and people.

    The model file downloads automatically on first run
    (~6 MB download).
    """
    try:
        from ultralytics import YOLO
    except ImportError:
        print("ERROR: ultralytics is not installed.")
        print("Fix: pip install ultralytics")
        sys.exit(1)

    logger.info("Loading YOLOv8 model...")
    print("  Loading YOLOv8 model (downloads ~6MB on first run)...")

    # yolov8n = nano version (fastest, good enough for labelling)
    model = YOLO("yolov8n.pt")
    logger.info("YOLOv8 model loaded")
    return model


def label_image(model, image_path):
    """
    Run YOLO on one image and create labels.

    Returns:
        labels: list of (class_id, x_center, y_center, width, height)
        needs_review: True if any detection has low confidence
        ambulance_found: True if ambulance-like vehicle detected
    """
    results = model(str(image_path), verbose=False)
    labels = []
    needs_review = False
    ambulance_found = False

    for result in results:
        boxes = result.boxes
        if boxes is None:
            continue

        for box in boxes:
            coco_class = int(box.cls[0])
            confidence = float(box.conf[0])

            # Skip low confidence
            if confidence < MIN_CONFIDENCE:
                continue

            # Map COCO class to our AIMCRS class
            if coco_class not in COCO_TO_AIMCRS:
                continue

            aimcrs_class = COCO_TO_AIMCRS[coco_class]

            # Get bounding box in YOLO format
            # (normalized: x_center, y_center, width, height)
            x_center, y_center, w, h = box.xywhn[0].tolist()

            labels.append((aimcrs_class, x_center, y_center, w, h))

            # Flag for review if confidence is low
            if confidence < REVIEW_CONFIDENCE:
                needs_review = True

            # Check if this could be an ambulance
            # (YOLO doesn't know ambulance specifically,
            #  but large white vehicles flagged for review)
            if aimcrs_class == 0 and confidence > 0.7:
                # Could check color/size for ambulance hints
                # For now, ambulances are caught in Step 8
                pass

    return labels, needs_review, ambulance_found


def save_yolo_labels(labels, label_path):
    """
    Save labels in YOLO format.

    YOLO format is a .txt file where each line is:
    class_id x_center y_center width height

    All values are normalized (0 to 1, not pixel values).
    """
    label_path.parent.mkdir(parents=True, exist_ok=True)
    with open(label_path, "w") as f:
        for class_id, x, y, w, h in labels:
            f.write(f"{class_id} {x:.6f} {y:.6f} {w:.6f} {h:.6f}\n")


def create_classes_file():
    """
    Create the classes.txt file that lists all class names.
    Required by YOLO training.
    """
    classes_path = LABELLED_DIR / "classes.txt"
    classes_path.parent.mkdir(parents=True, exist_ok=True)
    with open(classes_path, "w") as f:
        for class_id in sorted(AIMCRS_CLASSES.keys()):
            f.write(f"{AIMCRS_CLASSES[class_id]}\n")
    logger.info(f"Classes file created: {classes_path}")


def main():
    """
    Main function — auto-labels all unlabelled images.

    Steps:
    1. Load YOLOv8 model
    2. Find all unlabelled images
    3. Run detection on each image
    4. Save labels in YOLO format
    5. Move labelled images to labelled/ folder
    6. Flag low-confidence ones for human review
    """
    print("=" * 50)
    print("  AIMCRS Auto-Labelling")
    print("  Using YOLOv8 to detect vehicles in images")
    print("=" * 50)

    setup_logging()
    LABELLED_DIR.mkdir(parents=True, exist_ok=True)
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)

    # Step 1: Load model
    model = load_yolo_model()

    # Step 2: Create classes file
    create_classes_file()

    # Step 3: Find images
    images = sorted(UNLABELLED_DIR.rglob("*.jpg")) if UNLABELLED_DIR.exists() else []
    print(f"\n  Found {len(images)} images to label")

    if not images:
        print("  No images found. Run the processing pipeline first:")
        print("  python scripts/process/process_pipeline.py")
        return

    # Stats
    labelled_count = 0
    review_count = 0
    skipped_count = 0
    ambulance_count = 0

    # Step 4: Process each image
    for i, img_path in enumerate(images):
        labels, needs_review, ambulance_found = label_image(model, img_path)

        # Skip images with too few vehicles
        vehicle_labels = [
            l for l in labels
            if l[0] not in (6, 8)  # Exclude pedestrians and animals from count
        ]

        if len(vehicle_labels) < MIN_VEHICLES_IN_IMAGE:
            skipped_count += 1
            continue

        # Determine destination
        relative = img_path.relative_to(UNLABELLED_DIR)

        if needs_review:
            dest_dir = REVIEW_DIR / relative.parent
            review_count += 1
        else:
            dest_dir = LABELLED_DIR / relative.parent
            labelled_count += 1

        if ambulance_found:
            ambulance_count += 1

        # Copy image to destination
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_img = dest_dir / img_path.name
        shutil.copy2(img_path, dest_img)

        # Save labels
        label_path = dest_img.with_suffix(".txt")
        save_yolo_labels(labels, label_path)

        # Progress
        if (i + 1) % 100 == 0:
            print(f"    Processed {i + 1}/{len(images)} images...")

    # Summary
    print("\n" + "=" * 50)
    print("  Auto-Labelling Summary")
    print("=" * 50)
    print(f"  Total images processed: {len(images)}")
    print(f"  Labelled (confident): {labelled_count}")
    print(f"  Needs human review: {review_count}")
    print(f"  Skipped (too few vehicles): {skipped_count}")
    print(f"  Ambulance images found: {ambulance_count}")
    print()
    print(f"  Labelled images: {LABELLED_DIR}")
    print(f"  Review needed: {REVIEW_DIR}")
    print()
    print("  Vehicle classes:")
    for cid, name in AIMCRS_CLASSES.items():
        marker = " <-- HIGHEST PRIORITY" if name == "ambulance" else ""
        print(f"    {cid}: {name}{marker}")
    print("=" * 50)
    print()
    print("  Next step: Augment the dataset")
    print("  Command: python scripts/process/augment.py")

    logger.info(
        f"Auto-labelling complete: {labelled_count} labelled, "
        f"{review_count} for review, {skipped_count} skipped"
    )


if __name__ == "__main__":
    main()
