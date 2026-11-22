"""Fetching readings from liturgia.wiara.pl: retries, caching, errors shown to the page."""

from unittest.mock import MagicMock, patch

import pytest
import requests

import create_graphic as cg
from create_graphic import ReadingsUnavailable

URL = "https://liturgia.wiara.pl/kalendarz/67b53.Czytania-mszalne/2026-11-22"
PAGE = (
    b'<html><body><div class="txt__rich-area">nav</div>'
    b'<div class="txt__rich-area">PIERWSZE CZYTANIE\nEz 34</div></body></html>'
)
B = "Tekst czytania."

# Christ the King, 22 Nov 2026, as liturgia.wiara.pl lays it out (2015 lectionary)
CHRIST_THE_KING = [
    "Liturgia Słowa wg lekcjonarza z 2015 roku",
    "PIERWSZE CZYTANIE", "Ez 34, 11-12. 15-17", "Chrystus zna swoje owce",
    "Czytanie z Księgi proroka Ezechiela", B, "Oto słowo Boże.",
    "PSALM RESPONSORYJNY", "Ps 23 (22), 1b-2a. 2b-3. 5. 6 (R.: por. 1b)",
    "Refren: Pan mym pasterzem, nie brak mi niczego.",
    "Pan jest moim pasterzem, * niczego mi nie braknie.", "Refren.",
    "DRUGIE CZYTANIE", "1 Kor 15, 20-26. 28", "Królestwo Boże",
    "Czytanie z Pierwszego Listu Świętego Pawła Apostoła do Koryntian", B, "Oto słowo Boże.",
    "ŚPIEW PRZED EWANGELIĄ", "Por. Mk 11, 9c. 10a", "Aklamacja: Alleluja, alleluja, alleluja.",
    "Błogosławiony Ten, który przychodzi w imię Pańskie,", "Aklamacja: Alleluja, alleluja, alleluja.",
    "EWANGELIA", "Mt 25, 31-46", "Chrystus będzie sądził z uczynków miłości",
    "Słowa Ewangelii według Świętego Mateusza", B, "Oto słowo Pańskie.",
]


def _ok(content=PAGE):
    resp = MagicMock(status_code=200, content=content)
    resp.raise_for_status = MagicMock()
    return resp


@pytest.fixture(autouse=True)
def no_sleep():
    with patch.object(cg.time, "sleep") as sleep:
        yield sleep


class TestFetchRetries:
    def test_retries_timeout_then_succeeds(self, no_sleep):
        with patch.object(cg.requests, "get",
                          side_effect=[requests.Timeout("read timed out"), _ok()]) as get:
            assert cg._fetch_liturgy_page(URL).status_code == 200
        assert get.call_count == 2
        no_sleep.assert_called_once_with(2)

    def test_retries_server_errors(self):
        with patch.object(cg.requests, "get",
                          side_effect=[MagicMock(status_code=503), MagicMock(status_code=502), _ok()]) as get:
            cg._fetch_liturgy_page(URL)
        assert get.call_count == 3

    def test_gives_up_with_readable_error(self):
        with patch.object(cg.requests, "get", side_effect=requests.ConnectionError("reset")) as get:
            with pytest.raises(ReadingsUnavailable, match="didn't answer after 3 tries.*Try again"):
                cg._fetch_liturgy_page(URL)
        assert get.call_count == 3

    def test_sends_browser_user_agent(self):
        with patch.object(cg.requests, "get", return_value=_ok()) as get:
            cg._fetch_liturgy_page(URL)
        assert get.call_args.kwargs["headers"]["User-Agent"].startswith("Mozilla/5.0")

    def test_page_without_readings_area(self):
        with patch.object(cg.requests, "get", return_value=_ok(b"<html><body>Przerwa</body></html>")):
            with pytest.raises(ReadingsUnavailable, match="No readings found"):
                cg._scrape_content_list("2026-11-22")


class TestContentCache:
    def test_page_is_downloaded_once_per_load(self):
        with patch.object(cg.requests, "get", return_value=_ok()) as get:
            first = cg._scrape_content_list("2026-11-22")
            first.append("changed by caller")
            second = cg._scrape_content_list("2026-11-22")
        assert get.call_count == 1
        assert "changed by caller" not in second

    def test_cache_expires(self, monkeypatch):
        clock = iter([1000.0, 1000.0 + cg.CONTENT_CACHE_SECONDS + 1, 2000.0])
        monkeypatch.setattr(cg.time, "monotonic", lambda: next(clock))
        with patch.object(cg.requests, "get", return_value=_ok()) as get:
            cg._scrape_content_list("2026-11-22")
            cg._scrape_content_list("2026-11-22")
        assert get.call_count == 2

    def test_failures_are_not_cached(self):
        with patch.object(cg.requests, "get",
                          side_effect=[requests.Timeout("x")] * 3 + [_ok()]) as get:
            with pytest.raises(ReadingsUnavailable):
                cg._scrape_content_list("2026-11-22")
            cg._scrape_content_list("2026-11-22")
        assert get.call_count == 4


class TestLoadReadings:
    def test_christ_the_king_lists_all_four_readings(self):
        with patch.object(cg, "_download_content_list", return_value=list(CHRIST_THE_KING)), \
             patch.object(cg, "_brewiarz_has_second_reading") as brewiarz:
            readings = cg.get_readings_for_cover("2026-11-22")
            assert cg.get_first_reading_options("2026-11-22") == []
        assert list(readings) == ["PIERWSZE CZYTANIE", "PSALM RESPONSORYJNY", "DRUGIE CZYTANIE", "EWANGELIA"]
        brewiarz.assert_not_called()  # Sundays always have a second reading

    def test_network_failure_reaches_the_page(self):
        with patch.object(cg.requests, "get", side_effect=requests.Timeout("read timed out")):
            with pytest.raises(ReadingsUnavailable, match="liturgia.wiara.pl didn't answer"):
                cg.get_readings_for_cover("2026-11-22")

    def test_parse_failure_reaches_the_page(self):
        with patch.object(cg, "_download_content_list", return_value=["Brak czytań"]), \
             patch.object(cg, "_parse_readings", side_effect=KeyError("EWANGELIA")):
            with pytest.raises(ReadingsUnavailable, match="Couldn't read the readings for 2026-11-22"):
                cg.get_readings_for_cover("2026-11-22")

    def test_sunday_feast_never_loses_second_reading(self):
        # 9 Nov 2025 (Lateran feast on a Sunday): both readings, whatever brewiarz says
        with patch.object(cg, "_download_content_list", return_value=list(CHRIST_THE_KING)), \
             patch.object(cg, "_brewiarz_has_second_reading", return_value=False):
            assert "DRUGIE CZYTANIE" in cg.get_readings_for_cover("2025-11-09")
