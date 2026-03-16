"""
Midjourney API client.
Based on yachty66/unofficial_midjourney_python_api with modifications for better control.

WARNING: This violates Midjourney ToS. Use at your own risk.
"""

import json
import logging
import os
import random
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)


class MidjourneyApi:
    """
    Client for interacting with Midjourney via Discord API.

    Args:
        authorization: Discord user token
        application_id: Midjourney application ID
        guild_id: Discord server ID
        channel_id: Discord channel ID
        version: Midjourney command version
        id: Midjourney command ID
    """

    DISCORD_API_BASE = "https://discord.com/api/v9"

    def __init__(
        self,
        authorization: str,
        application_id: str,
        guild_id: str,
        channel_id: str,
        version: str,
        id: str,
    ):
        self.authorization = authorization
        self.application_id = application_id
        self.guild_id = guild_id
        self.channel_id = channel_id
        self.version = version
        self.id = id

        self._headers = {
            "Authorization": self.authorization,
            "Content-Type": "application/json",
        }

    def imagine(self, prompt: str, timeout: int = 120, poll_interval: int = 10) -> dict:
        """
        Send /imagine command and wait for the 4-image grid result.

        Args:
            prompt: The image generation prompt
            timeout: Maximum seconds to wait for result
            poll_interval: Seconds between status checks

        Returns:
            Dict with message_id, image_url, and components (buttons)
        """
        logger.info(f"Sending /imagine prompt: {prompt[:50]}...")

        # Send the /imagine command
        self._send_imagine_command(prompt)

        # Wait for generation to complete
        start_time = time.time()
        while time.time() - start_time < timeout:
            time.sleep(poll_interval)

            try:
                result = self._get_latest_midjourney_message()
                if result and self._is_generation_complete(result):
                    logger.info("Image generation complete")
                    return result
            except Exception as e:
                logger.warning(f"Error checking status: {e}")

        raise TimeoutError(f"Image generation timed out after {timeout}s")

    def upscale(self, message_id: str, custom_id: str, timeout: int = 90) -> dict:
        """
        Click an upscale button (U1, U2, U3, or U4) and wait for result.

        Args:
            message_id: The message ID containing the image grid
            custom_id: The button's custom_id (from imagine result)
            timeout: Maximum seconds to wait

        Returns:
            Dict with upscaled image URL
        """
        logger.info(f"Upscaling with button: {custom_id[:20]}...")

        self._click_button(message_id, custom_id)

        start_time = time.time()
        while time.time() - start_time < timeout:
            time.sleep(10)

            try:
                result = self._get_latest_midjourney_message()
                if result and "attachments" in result:
                    # Check if this is an upscaled image (single, not grid)
                    if self._is_upscaled_image(result):
                        return result
            except Exception as e:
                logger.warning(f"Error checking upscale: {e}")

        raise TimeoutError(f"Upscale timed out after {timeout}s")

    def upscale_random(self, message_id: str, components: list, timeout: int = 90) -> dict:
        """
        Randomly select and click one of the U1-U4 upscale buttons.

        Args:
            message_id: The message ID containing the image grid
            components: The components list from imagine result
            timeout: Maximum seconds to wait

        Returns:
            Dict with upscaled image URL
        """
        # Extract U1-U4 button custom_ids
        upscale_buttons = []
        for row in components:
            if "components" in row:
                for button in row["components"]:
                    label = button.get("label", "")
                    if label in ["U1", "U2", "U3", "U4"]:
                        upscale_buttons.append(button["custom_id"])

        if not upscale_buttons:
            raise ValueError("No upscale buttons found in components")

        custom_id = random.choice(upscale_buttons)
        return self.upscale(message_id, custom_id, timeout)

    def download_image(self, image_url: str, save_path: Path) -> Path:
        """
        Download image from Discord CDN.

        Args:
            image_url: URL of the image to download
            save_path: Where to save the image

        Returns:
            Path to saved image
        """
        logger.info(f"Downloading image to: {save_path}")

        response = requests.get(image_url, timeout=60)
        response.raise_for_status()

        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_bytes(response.content)

        return save_path

    def _send_imagine_command(self, prompt: str) -> None:
        """Send /imagine slash command to Discord."""
        url = f"{self.DISCORD_API_BASE}/interactions"

        data = {
            "type": 2,
            "application_id": self.application_id,
            "guild_id": self.guild_id,
            "channel_id": self.channel_id,
            "session_id": "cannot be empty",
            "data": {
                "version": self.version,
                "id": self.id,
                "name": "imagine",
                "type": 1,
                "options": [
                    {
                        "type": 3,
                        "name": "prompt",
                        "value": prompt
                    }
                ],
                "application_command": {
                    "id": self.id,
                    "application_id": self.application_id,
                    "version": self.version,
                    "default_member_permissions": None,
                    "type": 1,
                    "nsfw": False,
                    "name": "imagine",
                    "description": "Create images with Midjourney",
                    "dm_permission": True,
                    "contexts": None,
                    "options": [
                        {
                            "type": 3,
                            "name": "prompt",
                            "description": "The prompt to imagine",
                            "required": True
                        }
                    ]
                },
                "attachments": []
            },
        }

        response = requests.post(url, headers=self._headers, json=data, timeout=30)
        response.raise_for_status()

    def _click_button(self, message_id: str, custom_id: str) -> None:
        """Click a button component on a message."""
        url = f"{self.DISCORD_API_BASE}/interactions"

        data = {
            "type": 3,
            "guild_id": self.guild_id,
            "channel_id": self.channel_id,
            "message_flags": 0,
            "message_id": message_id,
            "application_id": self.application_id,
            "session_id": "cannot be empty",
            "data": {
                "component_type": 2,
                "custom_id": custom_id,
            }
        }

        response = requests.post(url, headers=self._headers, json=data, timeout=30)
        response.raise_for_status()

    def _get_latest_midjourney_message(self) -> dict | None:
        """Get the most recent message from Midjourney in the channel."""
        url = f"{self.DISCORD_API_BASE}/channels/{self.channel_id}/messages"

        response = requests.get(url, headers=self._headers, timeout=30)
        response.raise_for_status()

        messages = response.json()

        # Find most recent message from Midjourney bot
        for msg in messages:
            author = msg.get("author", {})
            # Midjourney bot ID or check for bot flag
            if author.get("bot", False) and "Midjourney" in author.get("username", ""):
                return msg

        return messages[0] if messages else None

    def _is_generation_complete(self, message: dict) -> bool:
        """Check if image generation is complete (has U1-U4 buttons)."""
        components = message.get("components", [])

        for row in components:
            if "components" in row:
                for button in row["components"]:
                    if button.get("label") in ["U1", "U2", "U3", "U4"]:
                        return True

        return False

    def _is_upscaled_image(self, message: dict) -> bool:
        """Check if this is an upscaled single image (not a grid)."""
        attachments = message.get("attachments", [])
        if not attachments:
            return False

        # Upscaled images typically don't have the U1-U4 buttons
        components = message.get("components", [])
        has_upscale_buttons = False

        for row in components:
            if "components" in row:
                for button in row["components"]:
                    if button.get("label") in ["U1", "U2", "U3", "U4"]:
                        has_upscale_buttons = True
                        break

        return not has_upscale_buttons and len(attachments) > 0
