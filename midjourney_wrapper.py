"""
Midjourney wrapper with rate limiting and configuration.

This module provides a high-level interface for generating images via Midjourney,
with built-in rate limiting to reduce ban risk.

WARNING: Using this violates Midjourney Terms of Service. Use at your own risk.
"""

import logging
import random
import time
from pathlib import Path
from typing import Optional

from config import (
    DISCORD_AUTH_TOKEN,
    MJ_APPLICATION_ID,
    MJ_CHANNEL_ID,
    MJ_GUILD_ID,
    MJ_ID,
    MJ_VERSION,
    MJ_DELAY_MIN,
    MJ_DELAY_MAX,
)
from libs.midjourney.midjourney_api import MidjourneyApi

logger = logging.getLogger(__name__)


class MidjourneyWrapper:
    """
    High-level wrapper for Midjourney image generation.

    Features:
    - Rate limiting with random delays
    - Automatic upscaling
    - Image download to specified path
    """

    def __init__(self):
        """Initialize the Midjourney client with config credentials."""
        if not all([DISCORD_AUTH_TOKEN, MJ_APPLICATION_ID, MJ_CHANNEL_ID, MJ_GUILD_ID]):
            raise ValueError(
                "Missing Midjourney configuration. "
                "Set DISCORD_AUTH_TOKEN, MJ_APPLICATION_ID, MJ_GUILD_ID, MJ_CHANNEL_ID, "
                "MJ_VERSION, and MJ_ID in .env"
            )

        self.client = MidjourneyApi(
            authorization=DISCORD_AUTH_TOKEN,
            application_id=MJ_APPLICATION_ID,
            guild_id=MJ_GUILD_ID,
            channel_id=MJ_CHANNEL_ID,
            version=MJ_VERSION,
            id=MJ_ID,
        )
        self.delay_min = MJ_DELAY_MIN
        self.delay_max = MJ_DELAY_MAX

    def _rate_limit_delay(self) -> None:
        """Apply random delay to avoid detection."""
        delay = random.uniform(self.delay_min, self.delay_max)
        logger.debug(f"Rate limit delay: {delay:.1f}s")
        time.sleep(delay)

    def generate(
        self,
        prompt: str,
        save_path: Path,
        auto_upscale: bool = True,
        timeout: int = 180,
    ) -> Path:
        """
        Generate an image from a prompt and save it.

        Args:
            prompt: Midjourney prompt (include --ar, --v parameters)
            save_path: Where to save the final image
            auto_upscale: Whether to automatically upscale one variant
            timeout: Maximum time to wait for generation

        Returns:
            Path to the saved image

        Raises:
            TimeoutError: If generation takes too long
            ValueError: If no image could be retrieved
        """
        logger.info(f"Generating image for prompt: {prompt[:80]}...")

        # Rate limiting delay before request
        self._rate_limit_delay()

        # Send /imagine and wait for grid
        result = self.client.imagine(prompt, timeout=timeout)

        message_id = result.get("id")
        components = result.get("components", [])

        if not message_id:
            raise ValueError("Failed to get message ID from generation result")

        if auto_upscale:
            # Rate limit before upscale
            self._rate_limit_delay()

            # Upscale a random variant
            upscaled = self.client.upscale_random(message_id, components)
            image_url = upscaled.get("attachments", [{}])[0].get("url")
        else:
            # Use the grid image
            image_url = result.get("attachments", [{}])[0].get("url")

        if not image_url:
            raise ValueError("Failed to get image URL from result")

        # Download the image
        return self.client.download_image(image_url, save_path)

    def generate_grid(self, prompt: str, timeout: int = 180) -> dict:
        """
        Generate image grid without upscaling.

        Args:
            prompt: Midjourney prompt
            timeout: Maximum wait time

        Returns:
            Dict with message_id, image_url, components (for manual upscale selection)
        """
        self._rate_limit_delay()
        return self.client.imagine(prompt, timeout=timeout)

    def upscale_variant(
        self,
        message_id: str,
        custom_id: str,
        save_path: Path,
    ) -> Path:
        """
        Upscale a specific variant and download.

        Args:
            message_id: Message ID from generate_grid result
            custom_id: Button custom_id for the variant to upscale
            save_path: Where to save the image

        Returns:
            Path to saved image
        """
        self._rate_limit_delay()
        result = self.client.upscale(message_id, custom_id)

        image_url = result.get("attachments", [{}])[0].get("url")
        if not image_url:
            raise ValueError("Failed to get upscaled image URL")

        return self.client.download_image(image_url, save_path)


    def upscale(self, message_id: str, custom_id: str) -> dict:
        """Click U1-U4 on a grid and return Midjourney's upscale message."""
        self._rate_limit_delay()
        return self.client.upscale(message_id, custom_id)

    def vary(self, message_id: str, custom_id: str, prompt: str) -> dict:
        """Click Vary (Subtle/Strong) on an upscaled image; returns the new grid message."""
        self._rate_limit_delay()
        return self.client.vary(message_id, custom_id, prompt)

    def download(self, image_url: str, save_path: Path) -> Path:
        return self.client.download_image(image_url, save_path)


def _buttons(components: list):
    for row in components or []:
        for button in row.get("components", []) if isinstance(row, dict) else []:
            yield button


def extract_upscale_buttons(components: list) -> dict:
    """U1-U4 label -> custom_id from a grid message."""
    return {
        b["label"]: b.get("custom_id", "")
        for b in _buttons(components)
        if b.get("label") in ("U1", "U2", "U3", "U4")
    }


def extract_vary_buttons(components: list) -> dict:
    """
    "subtle"/"strong" -> custom_id from an upscaled image message.
    Buttons are labelled "Vary (Subtle)" / "Vary (Strong)"; their custom_ids
    contain low_variation / high_variation, which is checked too in case the
    labels change.
    """
    found = {}
    for b in _buttons(components):
        label = (b.get("label") or "").lower()
        custom_id = b.get("custom_id") or ""
        if "region" in label or "inpaint" in custom_id.lower():
            continue
        if ("vary" in label and "subtle" in label) or "low_variation" in custom_id:
            found.setdefault("subtle", custom_id)
        elif ("vary" in label and "strong" in label) or "high_variation" in custom_id:
            found.setdefault("strong", custom_id)
    return found


def generate_cover_image(
    prompt: str,
    output_dir: Path,
    filename: str = "mateusztront.jpg",
) -> Path:
    """
    Convenience function to generate a cover image.

    Args:
        prompt: Midjourney prompt with parameters
        output_dir: Directory to save the image
        filename: Name for the saved file

    Returns:
        Path to the saved cover image
    """
    wrapper = MidjourneyWrapper()
    save_path = output_dir / filename
    return wrapper.generate(prompt, save_path)
