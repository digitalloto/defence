# ============================================
# FILE 1 OF 2 — YouTube Downloader Configuration
# ============================================
# File: scripts/download/youtube_config.py
# What: All settings for the YouTube downloader
# ============================================

# ----- SEARCH TERMS -----
# These are the YouTube searches we run to find
# Indian traffic footage for training data.

SEARCH_TERMS = [
    "India traffic CCTV",
    "Delhi traffic camera footage",
    "Mumbai traffic timelapse",
    "Chennai traffic intersection",
    "Bengaluru traffic signal",
    "Indian ambulance traffic",
    "India emergency vehicle road",
    "Dhaula Kuan traffic Delhi",
    "India highway traffic 4K",
    "Indian traffic jam 2024",
    "India road traffic drone view",
    "Hyderabad traffic signal camera",
    "Kolkata traffic intersection",
    "Pune traffic CCTV footage",
    "Indian ambulance stuck in traffic",
    "ambulance India traffic",
    "ambulance stuck traffic India",
    "Indian ambulance emergency",
]

# ----- TARGET CHANNELS -----
# Specific YouTube channels known to have Indian traffic footage.

TARGET_CHANNELS = [
    # The channel Ariansyah Center used for VILTICS Delhi demo
    "incredibleindiantraffic",
]

# ----- CITY DETECTION -----
# We look for these words in the video title and description
# to figure out which city the footage is from.
# The downloader checks each keyword and sorts the video
# into the matching city folder.

CITY_KEYWORDS = {
    "Delhi": [
        "delhi", "new delhi", "dhaula kuan", "connaught place",
        "chandni chowk", "karol bagh", "nehru place", "ito",
        "rajiv chowk", "noida", "gurgaon", "gurugram",
        "dwarka", "rohini", "lajpat nagar", "saket",
    ],
    "Mumbai": [
        "mumbai", "bombay", "western express", "eastern express",
        "bandra", "andheri", "dadar", "worli", "navi mumbai",
        "thane", "borivali", "goregaon", "powai", "marine drive",
    ],
    "Chennai": [
        "chennai", "madras", "anna nagar", "t nagar",
        "mount road", "adyar", "velachery", "tambaram",
        "guindy", "egmore", "mylapore", "porur",
    ],
    "Kolkata": [
        "kolkata", "calcutta", "howrah", "salt lake",
        "park street", "esplanade", "dum dum", "rajarhat",
    ],
    "Bengaluru": [
        "bengaluru", "bangalore", "koramangala", "whitefield",
        "electronic city", "marathahalli", "indiranagar",
        "hsr layout", "jayanagar", "silk board",
    ],
    "Hyderabad": [
        "hyderabad", "secunderabad", "hitec city", "hitech city",
        "gachibowli", "madhapur", "ameerpet", "kukatpally",
        "lb nagar", "dilsukhnagar",
    ],
    "Pune": [
        "pune", "pimpri", "chinchwad", "hinjewadi",
        "kothrud", "shivajinagar", "hadapsar",
    ],
    "Raipur": [
        "raipur", "chhattisgarh",
    ],
}

# ----- DOWNLOAD SETTINGS -----

# Maximum number of videos to download per search term
MAX_VIDEOS_PER_SEARCH = 10

# Maximum video length in seconds (30 minutes)
# Longer videos use too much disk space
MAX_VIDEO_LENGTH_SECONDS = 30 * 60

# Minimum video length in seconds (30 seconds)
# Very short videos are usually not useful
MIN_VIDEO_LENGTH_SECONDS = 30

# Seconds to wait between downloads (be polite to YouTube)
DELAY_BETWEEN_DOWNLOADS = 5

# Maximum total videos to download in one run
# (Safety limit to not fill your hard drive)
MAX_TOTAL_DOWNLOADS = 200

# ----- VIDEO QUALITY SETTINGS -----
# Download the best quality available
# "bestvideo+bestaudio/best" means:
#   Try to get best video AND best audio separately, then combine
#   If that fails, get the best single file available
VIDEO_FORMAT = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"

# ----- LICENSE TYPES -----
# We flag each video with its license type.
# Creative Commons = safe to use for training
# Standard YouTube = research use only, never redistribute

LICENSE_CREATIVE_COMMONS = "creative_commons"
LICENSE_STANDARD = "standard_youtube"
LICENSE_UNKNOWN = "unknown"
