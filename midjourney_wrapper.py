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
