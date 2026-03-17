#!/usr/bin/env python3
# ============================================
# Step 7 — Data Augmentation (FILE 2 OF 2)
# ============================================
# File: scripts/process/augment.py
# What: Creates variations of images to multiply dataset 6x
# How to run: python scripts/process/augment.py
#
# What is augmentation?
# It takes each image and creates modified copies:
# - Flip horizontally (mirror)
# - Make brighter/darker (different times of day)
# - Add rain effect (monsoon conditions)
# - Add haze/dust (Indian weather)
# - Blur slightly (simulate bad cameras)
# - Darken for night mode
#
# This turns 1,000 images into 6,000+ images!
# More data = better AI training = better ambulance detection.
# ============================================

import os
import sys
import random
from pathlib import Path

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
LABELLED_DIR = PROJECT_ROOT / "processed" / "labelled"
UNLABELLED_DIR = PROJECT_ROOT / "processed" / "unlabelled"
AUGMENTED_DIR = PROJECT_ROOT / "processed" / "augmented"
LOGS_DIR = PROJECT_ROOT / "logs"


def setup_logging():
    """Set up logging."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    logger.add(
        str(LOGS_DIR / "augmentation.log"),
        rotation="10 MB",
        retention="30 days",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    )


def flip_horizontal(image):
    """Mirror the image left-right."""
    return cv2.flip(image, 1)


def adjust_brightness(image, factor):
    """
    Make image brighter or darker.
    factor > 1.0 = brighter
    factor < 1.0 = darker
    """
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    hsv = hsv.astype(np.float32)
    hsv[:, :, 2] = np.clip(hsv[:, :, 2] * factor, 0, 255)
    hsv = hsv.astype(np.uint8)
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)


def add_rain_effect(image):
    """
    Simulate rain on the image.
    Adds diagonal white streaks (rain drops).
    Important for monsoon conditions training.
    """
    rain = image.copy()
    h, w = rain.shape[:2]

    # Random rain streaks
    num_drops = random.randint(300, 700)
    for _ in range(num_drops):
        x = random.randint(0, w - 1)
        y = random.randint(0, h - 1)
        length = random.randint(5, 15)
        # Rain falls diagonally
        x2 = min(x + length // 3, w - 1)
        y2 = min(y + length, h - 1)
        cv2.line(rain, (x, y), (x2, y2), (200, 200, 200), 1)

    # Slightly blur to blend rain
    rain = cv2.GaussianBlur(rain, (3, 3), 0)
    # Blend original and rain
    return cv2.addWeighted(image, 0.7, rain, 0.3, 0)


def add_haze_effect(image):
    """
    Simulate dust/haze — common in Indian cities.
    Adds a white fog layer over the image.
    """
    h, w = image.shape[:2]
    haze = np.full((h, w, 3), 220, dtype=np.uint8)  # Light gray
    intensity = random.uniform(0.15, 0.35)
    return cv2.addWeighted(image, 1 - intensity, haze, intensity, 0)


def add_slight_blur(image):
    """
    Slight blur to simulate low-quality CCTV cameras.
    Indian traffic cameras are often not high quality.
    """
    kernel_size = random.choice([3, 5])
    return cv2.GaussianBlur(image, (kernel_size, kernel_size), 0)


def simulate_night(image):
    """
    Darken the image to simulate night conditions.
    Adds a blue-ish tint like streetlight lighting.
    """
    dark = adjust_brightness(image, 0.3)
    # Add slight blue tint (street lights)
    blue_tint = dark.copy()
    blue_tint[:, :, 0] = np.clip(
        blue_tint[:, :, 0].astype(np.int16) + 15, 0, 255
    ).astype(np.uint8)
    return blue_tint


def augment_image(image_path, output_dir):
    """
    Apply all 6 augmentations to one image.
    Returns number of augmented images created.
    """
    img = cv2.imread(str(image_path))
    if img is None:
        return 0

    stem = image_path.stem
    output_dir.mkdir(parents=True, exist_ok=True)
    count = 0

    augmentations = [
        ("flip", flip_horizontal),
        ("bright", lambda img: adjust_brightness(img, 1.4)),
        ("rain", add_rain_effect),
        ("haze", add_haze_effect),
        ("blur", add_slight_blur),
        ("night", simulate_night),
    ]

    for aug_name, aug_func in augmentations:
        try:
            result = aug_func(img)
            save_path = output_dir / f"{stem}_{aug_name}.jpg"
            cv2.imwrite(str(save_path), result, [cv2.IMWRITE_JPEG_QUALITY, 85])
            count += 1
        except Exception as e:
            logger.error(f"Augmentation {aug_name} failed for {stem}: {e}")

    return count


def copy_label_file(image_path, output_dir, aug_name):
    """
    If a YOLO label file exists for this image,
    copy it for the augmented version too.
    (Flip needs label adjustment — handled separately)
    """
    label_path = image_path.with_suffix(".txt")
    if label_path.exists():
        new_label = output_dir / f"{image_path.stem}_{aug_name}.txt"
        import shutil
        shutil.copy2(label_path, new_label)


def main():
    """
    Main function — augments all processed images.
    Multiplies dataset by ~6x.
    """
    print("=" * 50)
    print("  AIMCRS Data Augmentation")
    print("  Multiplying dataset 6x with variations")
    print("=" * 50)

    setup_logging()
    AUGMENTED_DIR.mkdir(parents=True, exist_ok=True)

    # Find all images to augment
    source_dirs = [LABELLED_DIR, UNLABELLED_DIR]
    images = []
    for src_dir in source_dirs:
        if src_dir.exists():
            images.extend(
                p for p in src_dir.rglob("*.jpg")
                if "augmented" not in str(p)
            )

    print(f"  Found {len(images)} images to augment")
    logger.info(f"Augmenting {len(images)} images")

    total_created = 0
    for i, img_path in enumerate(images):
        # Create output in same subfolder structure
        try:
            relative = img_path.relative_to(PROJECT_ROOT / "processed")
        except ValueError:
            relative = Path(img_path.name)

        output_dir = AUGMENTED_DIR / relative.parent
        count = augment_image(img_path, output_dir)
        total_created += count

        # Progress update every 100 images
        if (i + 1) % 100 == 0:
            print(f"    Processed {i + 1}/{len(images)} images...")

    print("\n" + "=" * 50)
    print("  Augmentation Summary")
    print("=" * 50)
    print(f"  Original images: {len(images)}")
    print(f"  Augmented copies created: {total_created}")
    print(f"  Total dataset size: {len(images) + total_created}")
    print(f"  Multiplier: ~{(len(images) + total_created) / max(len(images), 1):.1f}x")
    print(f"  Output: {AUGMENTED_DIR}")
    print("=" * 50)

    logger.info(
        f"Augmentation complete: {total_created} new images "
        f"(~{(len(images) + total_created) / max(len(images), 1):.1f}x multiplier)"
    )


if __name__ == "__main__":
    main()
