"""
Cyber Bible - Desktop application entry point.
Creates liturgical reading graphics and publishes to Instagram.
"""

import logging
import sys

import eel

from config import WEB_DIR, LOG_LEVEL, LOG_FORMAT

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

# Import exposed functions to register them with eel
from create_graphic import draw_post, readings_eng, readings_pol, publish


def main():
    """Initialize and start the Eel application."""
    # Ensure web directory exists
    WEB_DIR.mkdir(parents=True, exist_ok=True)

    # Initialize Eel with web folder
    eel.init(str(WEB_DIR))

    logger.info("Starting Cyber Bible application")
    logger.info(f"Web directory: {WEB_DIR}")

    try:
        # Start the application
        eel.start(
            "index.html",
            size=(800, 800),
            mode="chrome",
            port=8000,
        )
    except EnvironmentError:
        # If Chrome not found, try default browser
        logger.warning("Chrome not found, trying default browser")
        eel.start(
            "index.html",
            size=(800, 800),
            mode="default",
            port=8000,
        )


if __name__ == "__main__":
    main()
