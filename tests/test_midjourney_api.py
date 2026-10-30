"""
Tests for libs/midjourney/midjourney_api.py prompt matching.
"""

import time
from unittest.mock import patch, MagicMock

import pytest

from libs.midjourney.midjourney_api import MidjourneyApi


@pytest.fixture
def api():
    return MidjourneyApi("token", "app", "guild", "channel", "version", "id")


def _grid_message(content: str) -> dict:
    return {
        "id": "123",
        "author": {"bot": True, "username": "Midjourney Bot"},
        "timestamp": "2099-01-01T00:00:00.000000+00:00",
        "content": content,
        "components": [{"components": [{"label": "U1"}]}],
    }


class TestGetMatchingMidjourneyMessage:
    """Midjourney echoes the prompt with whitespace collapsed."""

    @pytest.mark.parametrize("prompt", [
        "ox  in a well and people trying to rescue it in style of reportage",
        "Which of you, if your son\nor an ox fell into a well",
        "  ox in a well and people trying to rescue it",
    ])
    def test_matches_despite_extra_whitespace(self, api, prompt):
        echoed = " ".join(prompt.split())
        response = MagicMock()
        response.json.return_value = [_grid_message(f"**{echoed} --ar 1:1** - <@1> (fast)")]

        with patch("libs.midjourney.midjourney_api.requests.get", return_value=response):
            result = api._get_matching_midjourney_message(prompt, time.time())

        assert result is not None
        assert result["id"] == "123"

    def test_ignores_other_prompts(self, api):
        response = MagicMock()
        response.json.return_value = [_grid_message("**minnie mouse wearing black boots** - <@2>")]

        with patch("libs.midjourney.midjourney_api.requests.get", return_value=response):
            result = api._get_matching_midjourney_message("ox in a well", time.time())

        assert result is None
