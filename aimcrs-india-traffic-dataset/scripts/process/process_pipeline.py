#!/usr/bin/env python3
# ============================================
# Step 7 — Data Processing Pipeline (FILE 1 OF 2)
# ============================================
# File: scripts/process/process_pipeline.py
# What: Processes raw videos and images for training
# How to run: python scripts/process/process_pipeline.py
#
# What this does:
#   1. Extract frames from video files (every 5th frame)
#   2. Resize to standard 640x640 pixels
#   3. Convert to JPG format
#   4. Remove blurry or dark frames
#   5. Remove duplicate images (perceptual hash)
#   6. Organise by city and type
# ============================================

import os
import sys
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import cv2
except ImportError:
    print("ERROR: opencv-python is not installed.")
    print("Fix: pip install opencv-python")
    sys.exit(1)

try:
    from PIL import Image
except ImportError:
    print("ERROR: Pillow is not installed.")
    print("Fix: pip install Pillow")
    sys.exit(1)

try:
    import imagehash
except ImportError:
    print("ERROR: imagehash is not installed.")
    print("Fix: pip install imagehash")
    sys.exit(1)

try:
    from loguru import logger
except ImportError:
    print("ERROR: loguru is not installed. Fix: pip install loguru")
    sys.exit(1)

# ----- PATHS -----
RAW_DIR = PROJECT_ROOT / "raw"
PROCESSED_DIR = PROJECT_ROOT / "processed"
UNLABELLED_DIR = PROCESSED_DIR / "unlabelled"
LOGS_DIR = PROJECT_ROOT / "logs"

# ----- SETTINGS -----

# Extract every Nth frame from videos
FRAME_EXTRACTION_INTERVAL = 5

# Standard image size for training
TARGET_WIDTH = 640
TARGET_HEIGHT = 640

# Minimum brightness threshold (0-255).
# Images darker than this are probably useless.
MIN_BRIGHTNESS = 30

# Blur detection threshold.
# Lower number = more blurry. Below this = reject.
MIN_SHARPNESS = 50

# Minimum vehicles needed (used later in labelling step)
# For now, we just extract and clean frames.

# Perceptual hash distance threshold.
# If two images have a hash distance less than this,
# they are considered duplicates.
DUPLICATE_HASH_THRESHOLD = 8

# Supported video formats
VIDEO_EXTENSIONS = {".mp4", ".avi", ".mkv", ".mov", ".webm", ".flv"}

# Supported image formats
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff"}


def setup_logging():
    """Set up logging."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    logger.add(
        str(LOGS_DIR / "processing.log"),
        rotation="10 MB",
        retention="30 days",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    )
    logger.info("=" * 60)
    logger.info("Processing Pipeline Started")
    logger.info("=" * 60)


def is_bright_enough(image_cv2):
    """
    Check if an image is bright enough to be useful.

    How it works:
    - Convert image to grayscale (black and white)
    - Calculate average brightness
    - If average is below threshold, image is too dark

    Returns True if bright enough, False if too dark.
    """
    gray = cv2.cvtColor(image_cv2, cv2.COLOR_BGR2GRAY)
    mean_brightness = gray.mean()
    return mean_brightness >= MIN_BRIGHTNESS


def is_sharp_enough(image_cv2):
    """
    Check if an image is sharp (not blurry).

    How it works:
    - Apply Laplacian filter (detects edges)
    - Calculate variance (spread) of the result
    - Low variance = no edges = blurry image

    Returns True if sharp enough, False if too blurry.
    """
    gray = cv2.cvtColor(image_cv2, cv2.COLOR_BGR2GRAY)
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    return laplacian_var >= MIN_SHARPNESS


def extract_frames_from_video(video_path, output_dir):
    """
    Extract frames from a video file.

    Takes every 5th frame (configurable), saves as JPG.
    Skips dark and blurry frames.

    Returns number of frames saved.
    """
    video_path = Path(video_path)
    logger.info(f"Extracting frames from: {video_path.name}")

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        logger.error(f"Cannot open video: {video_path}")
        return 0

    # Get video info
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    logger.info(f"  Total frames: {total_frames}, FPS: {fps:.1f}")

    output_dir.mkdir(parents=True, exist_ok=True)
    stem = video_path.stem  # Filename without extension

    saved = 0
    skipped_dark = 0
    skipped_blur = 0
    frame_num = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_num += 1

        # Only take every Nth frame
        if frame_num % FRAME_EXTRACTION_INTERVAL != 0:
            continue

        # Check brightness
        if not is_bright_enough(frame):
            skipped_dark += 1
            continue

        # Check sharpness
        if not is_sharp_enough(frame):
            skipped_blur += 1
            continue

        # Resize to standard size
        resized = cv2.resize(frame, (TARGET_WIDTH, TARGET_HEIGHT))

        # Save as JPG
        filename = f"{stem}_frame_{frame_num:06d}.jpg"
        save_path = output_dir / filename
        cv2.imwrite(str(save_path), resized, [cv2.IMWRITE_JPEG_QUALITY, 90])
        saved += 1

    cap.release()

    logger.info(
        f"  Saved: {saved} frames, "
        f"Skipped dark: {skipped_dark}, "
        f"Skipped blurry: {skipped_blur}"
    )
    return saved


def process_image_file(image_path, output_dir):
    """
    Process a single image file.
    Resize to standard size, check quality, save as JPG.
    """
    try:
        img = cv2.imread(str(image_path))
        if img is None:
            return False

        # Check brightness
        if not is_bright_enough(img):
            return False

        # Check sharpness
        if not is_sharp_enough(img):
            return False

        # Resize
        resized = cv2.resize(img, (TARGET_WIDTH, TARGET_HEIGHT))

        # Save
        output_dir.mkdir(parents=True, exist_ok=True)
        stem = Path(image_path).stem
        save_path = output_dir / f"{stem}.jpg"
        cv2.imwrite(str(save_path), resized, [cv2.IMWRITE_JPEG_QUALITY, 90])
        return True

    except Exception as e:
        logger.error(f"Failed to process {image_path}: {e}")
        return False


def remove_duplicates(image_dir):
    """
    Remove duplicate images using perceptual hashing.

    How it works:
    - Calculate a "fingerprint" (hash) of each image
    - Compare fingerprints
    - If two images have very similar fingerprints,
      they look almost the same — keep one, delete the other

    This is much smarter than just comparing file sizes.
    """
    logger.info(f"Removing duplicates from: {image_dir}")
    image_dir = Path(image_dir)

    # Collect all images
    images = sorted(
        p for p in image_dir.rglob("*")
        if p.suffix.lower() in IMAGE_EXTENSIONS
    )

    if len(images) < 2:
        logger.info("Less than 2 images — nothing to deduplicate")
        return 0

    logger.info(f"  Checking {len(images)} images for duplicates")

    # Calculate hashes
    hashes = {}
    duplicates = []

    for img_path in images:
        try:
            img = Image.open(img_path)
            h = imagehash.phash(img)

            # Check against existing hashes
            is_dup = False
            for existing_hash, existing_path in hashes.items():
                if abs(h - existing_hash) < DUPLICATE_HASH_THRESHOLD:
                    duplicates.append(img_path)
                    is_dup = True
                    break

            if not is_dup:
                hashes[h] = img_path

        except Exception as e:
            logger.error(f"  Hash failed for {img_path.name}: {e}")

    # Delete duplicates
    for dup_path in duplicates:
        dup_path.unlink()

    logger.info(f"  Removed {len(duplicates)} duplicates")
    return len(duplicates)


def find_all_videos():
    """Find all video files in the raw/ directory."""
    videos = []
    for ext in VIDEO_EXTENSIONS:
        videos.extend(RAW_DIR.rglob(f"*{ext}"))
    return sorted(videos)


def find_all_images():
    """Find all image files in the raw/ directory."""
    images = []
    for ext in IMAGE_EXTENSIONS:
        images.extend(RAW_DIR.rglob(f"*{ext}"))
    return sorted(images)


def main():
    """
    Main processing pipeline.

    Steps:
    1. Find all videos in raw/ → extract frames
    2. Find all images in raw/ → resize and clean
    3. Remove duplicates
    4. Print summary
    """
    print("=" * 50)
    print("  AIMCRS Data Processing Pipeline")
    print("  Extract, clean, resize, deduplicate")
    print("=" * 50)

    setup_logging()
    UNLABELLED_DIR.mkdir(parents=True, exist_ok=True)

    total_frames = 0
    total_images = 0

    # Step 1: Extract frames from videos
    print("\n--- Step 1: Extracting frames from videos ---")
    videos = find_all_videos()
    logger.info(f"Found {len(videos)} video files")
    print(f"  Found {len(videos)} video files")

    for video_path in videos:
        # Determine output subfolder based on source
        relative = video_path.relative_to(RAW_DIR)
        parts = relative.parts
        if len(parts) >= 2:
            subfolder = parts[0] + "_" + parts[1] if len(parts) > 2 else parts[0]
        else:
            subfolder = "other"

        output_dir = UNLABELLED_DIR / subfolder
        count = extract_frames_from_video(video_path, output_dir)
        total_frames += count
        print(f"    {video_path.name}: {count} frames extracted")

    # Step 2: Process standalone images
    print("\n--- Step 2: Processing standalone images ---")
    images = find_all_images()
    logger.info(f"Found {len(images)} image files")
    print(f"  Found {len(images)} image files")

    for img_path in images:
        # Skip images already in processed/
        if "processed" in str(img_path):
            continue

        relative = img_path.relative_to(RAW_DIR)
        parts = relative.parts
        if len(parts) >= 2:
            subfolder = parts[0]
        else:
            subfolder = "other"

        output_dir = UNLABELLED_DIR / subfolder
        if process_image_file(img_path, output_dir):
            total_images += 1

    # Step 3: Remove duplicates
    print("\n--- Step 3: Removing duplicates ---")
    dups_removed = remove_duplicates(UNLABELLED_DIR)

    # Step 4: Count final results
    final_count = sum(
        1 for _ in UNLABELLED_DIR.rglob("*.jpg")
    )

    # Summary
    print("\n" + "=" * 50)
    print("  Processing Pipeline Summary")
    print("=" * 50)
    print(f"  Frames extracted from video: {total_frames}")
    print(f"  Images processed: {total_images}")
    print(f"  Duplicates removed: {dups_removed}")
    print(f"  Final clean images: {final_count}")
    print(f"  Output: {UNLABELLED_DIR}")
    print("=" * 50)
    print()
    print("  Next step: Run auto-labelling")
    print("  Command: python scripts/label/auto_label.py")

    logger.info(f"Pipeline complete: {final_count} clean images")


if __name__ == "__main__":
    main()
