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
FONT_SIZE_PSALM = 34
FONT_SIZE_MIN = 30  # Minimum font size for pagination

# Text layout
TEXT_PADDING_LEFT = 25
TEXT_PADDING_TOP = 75
LINE_HEIGHT_MULTIPLIER = 1.2

# Colors (RGB)
COLOR_TITLE = (139, 0, 0)  # Dark red for titles
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
# LOGGING
# =============================================================================

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# =============================================================================
# SESSION
# =============================================================================

SESSION_FILE = BASE_DIR / "session.json"
