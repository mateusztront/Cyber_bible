"""
Shared test fixtures for Cyber Bible tests.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PIL import Image

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def sample_background_image():
    """Create a 1080x1080 white background image."""
    return Image.new("RGB", (1080, 1080), "white")


@pytest.fixture
def sample_content_list():
    """Raw scraped content list from liturgy page."""
    return [
        "",
        "Liturgia Słowa",
        "",
        "PIERWSZE CZYTANIE",
        "Rdz 1, 1-19",
        "Czytanie z Księgi Rodzaju",
        "Na początku Bóg stworzył niebo i ziemię.",
        "Ziemia zaś była bezładem i pustkowiem.",
        "Oto słowo Boże",
        "",
        "PSALM RESPONSORYJNY",
        "Ps 104",
        "Refren: Niech zstąpi Duch Twój i odnowi ziemię.",
        "Błogosław, duszo moja, Pana.",
        "Boże mój, Panie, Ty jesteś bardzo wielki!",
        "Refren",
        "Odziany w światłość jak w szatę.",
        "Refren",
        "",
        "EWANGELIA",
        "J 1, 1-18",
        "Słowa Ewangelii według Świętego Jana",
        "Jezus powiedział do swoich uczniów:",
        "Na początku było Słowo.",
        "Oto słowo Pańskie.",
        "",
    ]


@pytest.fixture
def sample_content_dict():
    """Parsed readings dictionary."""
    return {
        "PIERWSZE CZYTANIE": [
            "Rdz 1, 1-19",
            "Czytanie z Księgi Rodzaju",
            "Na początku Bóg stworzył niebo i ziemię.",
            "Ziemia zaś była bezładem i pustkowiem.",
            "Oto słowo Boże",
        ],
        "PSALM RESPONSORYJNY": [
            "Ps 104",
            "Refren: Niech zstąpi Duch Twój i odnowi ziemię.",
            "Błogosław, duszo moja, Pana.",
            "Boże mój, Panie, Ty jesteś bardzo wielki!",
            "Refren",
            "Odziany w światłość jak w szatę.",
            "Refren",
        ],
        "EWANGELIA": [
            "J 1, 1-18",
            "Słowa Ewangelii według Świętego Jana",
            "Jezus powiedział do swoich uczniów:",
            "Na początku było Słowo.",
            "Oto słowo Pańskie.",
        ],
    }


@pytest.fixture
def sample_liturgy_html():
    """Sample HTML response from liturgia.wiara.pl."""
    return """
    <html>
    <body>
        <div class="txt__rich-area">First area</div>
        <div class="txt__rich-area">
            PIERWSZE CZYTANIE
            Rdz 1, 1-19
            Czytanie z Księgi Rodzaju
            Na początku Bóg stworzył niebo i ziemię.
            Oto słowo Boże

            PSALM RESPONSORYJNY
            Ps 104
            Refren: Niech zstąpi Duch Twój.
            Błogosław, duszo moja, Pana.
            Refren

            EWANGELIA
            J 1, 1-18
            Słowa Ewangelii według Świętego Jana
            Na początku było Słowo.
            Oto słowo Pańskie.
        </div>
    </body>
    </html>
    """


@pytest.fixture
def mock_instagram_client():
    """Mocked instagrapi Client."""
    client = MagicMock()
    client.login.return_value = True
    client.get_timeline_feed.return_value = {}
    client.album_upload.return_value = MagicMock(pk="123456")
    return client


@pytest.fixture
def temp_web_dir(tmp_path):
    """Temporary web directory for output."""
    web_dir = tmp_path / "web"
    web_dir.mkdir()
    return web_dir
