"""
Instagram authentication module for Cyber Bible.
Handles login via session or credentials with proper error handling.
"""

import logging
import time
from pathlib import Path

from instagrapi import Client
from instagrapi.exceptions import (
    LoginRequired,
    TwoFactorRequired,
    ChallengeRequired,
    BadPassword,
    PleaseWaitFewMinutes,
)

from config import (
    INSTAGRAM_USERNAME,
    INSTAGRAM_PASSWORD,
    INSTAGRAM_DELAY_RANGE,
    INSTAGRAM_LOCALE,
    INSTAGRAM_TIMEZONE_OFFSET,
    SESSION_FILE,
)

# Configure logging
logger = logging.getLogger(__name__)


def _configure_client(client: Client) -> None:
    """Configure Instagram client with device settings and delays."""
    client.delay_range = INSTAGRAM_DELAY_RANGE
    client.set_locale(INSTAGRAM_LOCALE)
    client.set_country_code(48)  # Poland
    client.set_timezone_offset(INSTAGRAM_TIMEZONE_OFFSET)

    # Samsung Galaxy S24+ (SM-S926B/DS) with Android 16
    client.set_device({
        "app_version": "326.0.0.42.90",
        "android_version": 36,
        "android_release": "16",
        "dpi": "600dpi",
        "resolution": "1440x3120",
        "manufacturer": "samsung",
        "device": "e2s",
        "model": "SM-S926B",
        "cpu": "qcom",
        "version_code": "567654321",
    })
    client.set_user_agent(
        "Instagram 326.0.0.42.90 Android (36/16; 600dpi; 1440x3120; "
        "samsung; SM-S926B; e2s; qcom; pl_PL; 567654321)"
    )


def _login_via_session(client: Client, username: str, password: str) -> bool:
    """
    Attempt to login using saved session.

    Returns:
        True if session login successful, False otherwise.
    """
    if not SESSION_FILE.exists():
        logger.info("No session file found, will login with credentials")
        return False

    try:
        client.load_settings(str(SESSION_FILE))
        client.login(username, password)

        # Verify session is valid
        try:
            client.get_timeline_feed()
            logger.info("Successfully logged in via session")
            return True
        except LoginRequired:
            logger.warning("Session expired, need to re-login")
            return False

    except Exception as e:
        logger.warning(f"Session login failed: {e}")
        return False


def _login_via_credentials(client: Client, username: str, password: str) -> bool:
    """
    Login using username and password.

    Returns:
        True if login successful, False otherwise.
    """
    try:
        logger.info(f"Attempting login for user: {username}")
        client.login(username, password)
        client.dump_settings(str(SESSION_FILE))
        logger.info("Successfully logged in with credentials")
        return True

    except TwoFactorRequired:
        logger.info("Two-factor authentication required")
        print("Enter 2FA verification code: ", end="")
        verification_code = input().strip()
        time.sleep(2)  # Small delay before 2FA attempt

        try:
            client.login(username, password, verification_code=verification_code)
            client.dump_settings(str(SESSION_FILE))
            logger.info("Successfully logged in with 2FA")
            return True
        except Exception as e:
            logger.error(f"2FA login failed: {e}")
            return False

    except BadPassword:
        logger.error("Invalid password provided")
        return False

    except PleaseWaitFewMinutes:
        logger.error("Rate limited by Instagram. Please wait a few minutes.")
        return False

    except ChallengeRequired as e:
        logger.error("Challenge required by Instagram")
        logger.error("Check your email/phone for verification")
        logger.error("You may need to log in via browser first")
        raise e

    except Exception as e:
        logger.error(f"Login failed: {e}")
        return False


def login_user(username: str = None, password: str = None) -> Client:
    """
    Login to Instagram using session or credentials.

    Args:
        username: Instagram username (defaults to config value)
        password: Instagram password (defaults to config value)

    Returns:
        Authenticated instagrapi Client

    Raises:
        ValueError: If credentials are not provided
        Exception: If login fails with both session and credentials
    """
    # Use provided credentials or fall back to config
    username = username or INSTAGRAM_USERNAME
    password = password or INSTAGRAM_PASSWORD

    if not username or not password:
        raise ValueError(
            "Instagram credentials not provided. "
            "Set INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD in .env file"
        )

    client = Client()
    _configure_client(client)

    # Try session login first
    if _login_via_session(client, username, password):
        return client

    # Fall back to credential login
    if _login_via_credentials(client, username, password):
        return client

    raise Exception("Failed to login with both session and credentials")


def logout(client: Client) -> None:
    """Logout and clear session."""
    try:
        client.logout()
        if SESSION_FILE.exists():
            SESSION_FILE.unlink()
        logger.info("Successfully logged out")
    except Exception as e:
        logger.warning(f"Logout error: {e}")
