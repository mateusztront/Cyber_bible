"""
Centralized configuration for Cyber Bible application.
All settings, paths, and environment variables are managed here.
"""

import os
import platform
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# =============================================================================
# PATHS
# =============================================================================

BASE_DIR = Path(__file__).parent
WEB_DIR = BASE_DIR / "web"
ASSETS_DIR = BASE_DIR / "assets"
BACKGROUND_IMAGE = ASSETS_DIR / "paper.gif"

# =============================================================================
# FONTS - Cross-platform font paths
# =============================================================================

if platform.system() == "Windows":
    FONT_DIR = Path(r"C:\Windows\Fonts")
else:
    # Linux/Mac - use system fonts or bundled fonts
    FONT_DIR = ASSETS_DIR / "fonts"

FONT_REGULAR = FONT_DIR / "tahoma.ttf"
FONT_BOLD = FONT_DIR / "tahomabd.ttf"

# Fallback fonts if Tahoma not available
FONT_FALLBACK_REGULAR = "arial.ttf"
FONT_FALLBACK_BOLD = "arialbd.ttf"

# =============================================================================
# IMAGE SETTINGS
# =============================================================================

IMAGE_SIZE = 1080
FONT_SIZE_DEFAULT = 44
FONT_SIZE_MAX = 60  # Maximum font size for autofit
FONT_SIZE_PSALM = 34
FONT_SIZE_MIN = 30  # Minimum font size for pagination

# Text layout
TEXT_PADDING_LEFT = 25
TEXT_PADDING_TOP = 75
LINE_HEIGHT_MULTIPLIER = 1.2

# Colors (RGB)
# COLOR_TITLE = "red"  # Old title red (pure 255, 0, 0) - uncomment to revert
COLOR_TITLE = (155, 22, 18)  # Dark brick red for titles/refrains (matches 2026-10-04 reference)
COLOR_TEXT = (0, 0, 0)  # Black for body text
COLOR_REFERENCE = (100, 100, 100)  # Gray for references

# =============================================================================
# INSTAGRAM CREDENTIALS (from environment)
# =============================================================================

INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME", "")
INSTAGRAM_PASSWORD = os.getenv("INSTAGRAM_PASSWORD", "")

# Instagram API settings
INSTAGRAM_DELAY_RANGE = [2, 5]  # Delay between requests (seconds)
INSTAGRAM_LOCALE = "pl_PL"
INSTAGRAM_TIMEZONE_OFFSET = 3600  # UTC+1 (Poland)

# =============================================================================
# ELEVENLABS API (Text-to-Speech)
# =============================================================================

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "3Ehk82QdxNa83Vm0xjf7")
ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1"

# =============================================================================
# DATA SOURCES
# =============================================================================

LITURGY_URL_PL = "https://liturgia.wiara.pl/kalendarz/67b53.Czytania-mszalne"
LITURGY_URL_EN = "https://www.vaticannews.va/en/word-of-the-day"

# =============================================================================
# HASHTAGS
# =============================================================================

DEFAULT_HASHTAGS = [
    "#Bible",
    "#Biblia",
    "#czytanianadzis",
    "#słowoboze",
    "#dalle3",
    "#midjourney",
    "#catholicchurch",
]

# =============================================================================
# SERVER MODE
# =============================================================================

# Headless mode: serve the app on the network (no desktop window) so it can be
# opened from other devices, e.g. a phone via Tailscale. Enable with HEADLESS=1
# in .env, or pass --headless on the command line.
HEADLESS = os.getenv("HEADLESS", "0").lower() in ("1", "true", "yes")

# =============================================================================
# LOGGING
# =============================================================================

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# logs/app.log, rotated at 1 MB, 5 old files kept. In Docker this folder is
# mounted from the host, so the log survives rebuilds (Docker's own log doesn't).
LOG_DIR = BASE_DIR / "logs"
LOG_FILE_MAX_BYTES = 1_000_000
LOG_FILE_BACKUPS = 5

# =============================================================================
# SESSION
# =============================================================================

SESSION_FILE = BASE_DIR / "session.json"

# =============================================================================
# EASTER WEEK SETTINGS
# =============================================================================

# Maximum images per Instagram carousel
MAX_CAROUSEL_IMAGES = 20

# Which of the 7 OT vigil readings to include (0-indexed: 0=1st, 2=3rd, 4=5th, 6=7th)
EASTER_VIGIL_OT_READING_INDICES = [0, 2, 4, 6]

# If EWANGELIA has more paragraphs than this threshold × 3, it's a Passion Gospel → allow extended pagination
PASSION_SPLIT_THRESHOLD = 4

# A Passion Gospel must also have at least this many characters of body text.
# Guards against normal Gospels made of many short poetic lines (e.g. the
# Magnificat on Aug 15: 21 paragraphs but only ~1300 chars; real Passions run
# 8000+ even in the shorter form).
PASSION_MIN_BODY_CHARS = 4000

# =============================================================================
# MIDJOURNEY API (Discord-based, unofficial)
# WARNING: Using this violates Midjourney ToS. Use at your own risk.
# =============================================================================

DISCORD_AUTH_TOKEN = os.getenv("DISCORD_AUTH_TOKEN", "")
MJ_APPLICATION_ID = os.getenv("MJ_APPLICATION_ID", "")
MJ_GUILD_ID = os.getenv("MJ_GUILD_ID", "")
MJ_CHANNEL_ID = os.getenv("MJ_CHANNEL_ID", "")
MJ_VERSION = os.getenv("MJ_VERSION", "")
MJ_ID = os.getenv("MJ_ID", "")

# Rate limiting (seconds) - helps avoid detection
MJ_DELAY_MIN = int(os.getenv("MJ_DELAY_MIN", "5"))
MJ_DELAY_MAX = int(os.getenv("MJ_DELAY_MAX", "15"))

