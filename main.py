"""
Cyber Bible - Desktop application entry point.
Creates liturgical reading graphics and publishes to Instagram.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler

import eel

from config import (
    WEB_DIR,
    LOG_LEVEL,
    LOG_FORMAT,
    LOG_DIR,
    LOG_FILE_MAX_BYTES,
    LOG_FILE_BACKUPS,
    HEADLESS,
)


def _log_handlers():
    handlers = [logging.StreamHandler(sys.stdout)]
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        handlers.append(RotatingFileHandler(
            LOG_DIR / "app.log",
            maxBytes=LOG_FILE_MAX_BYTES,
            backupCount=LOG_FILE_BACKUPS,
            encoding="utf-8",
        ))
    except OSError as e:
        # e.g. Docker created the mounted logs/ folder as root; run without it
        print(f"File logging disabled, cannot write to {LOG_DIR}: {e}", file=sys.stderr)
    return handlers


# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT,
    handlers=_log_handlers(),
)
logger = logging.getLogger(__name__)

# Ensure web directory exists
WEB_DIR.mkdir(parents=True, exist_ok=True)

# Initialize Eel BEFORE importing modules with @eel.expose decorators
eel.init(str(WEB_DIR))

# Now import exposed functions - @eel.expose will register correctly
from create_graphic import draw_post, readings_eng, readings_pol, publish
from login import check_2fa_needed, submit_2fa_code


@eel.expose
def client_log(message: str) -> None:
    """Record a browser-side event (e.g. a lost connection) in the server log."""
    logger.warning(f"Browser: {str(message)[:500]}")


def main():
    """Initialize and start the Eel application."""

    logger.info("Starting Cyber Bible application")
    logger.info(f"Web directory: {WEB_DIR}")

    def on_page_closed(page, sockets):
        logger.info(f"Page {page} disconnected ({len(sockets)} still connected) - keeping server running")

    if HEADLESS:
        mode=None
        host="0.0.0.0"
        close_callback=on_page_closed
    else:
        mode="default"
        host="localhost"
        close_callback=None

    eel.start(
        "index.html",
        size=(800, 800),
        mode=mode,
        host=host,
        close_callback=close_callback,
        port=8000,
    )


if __name__ == "__main__":
    main()
