"""
Weekday feasts with two first readings to choose from (e.g. 9 Nov: Ez 47 albo
1 Kor 3). liturgia.wiara.pl prints the alternative under DRUGIE CZYTANIE;
brewiarz.pl is the cross-check for whether the day really has a second reading.
"""

from unittest.mock import MagicMock, patch

import pytest

import create_graphic
from create_graphic import (
    _apply_first_reading_choice,
    _brewiarz_has_second_reading,
    _brewiarz_urls,
    _has_alternative_first_reading,
    _parse_readings,
)

WEEKDAY_FEAST = "2026-11-09"   # Monday, Lateran Basilica
SUNDAY_FEAST = "2025-11-09"    # Sunday, Lateran Basilica — both readings are read
ORDINARY_SUNDAY = "2026-11-08"


def _wiara_content_list():
    """Lateran feast as liturgia.wiara.pl lists it (after cleaning)."""
    return [
        "PIERWSZE CZYTANIE",
        "Ez 47,1-2.8-9.12",
        "Woda wypływająca ze świątyni niesie życie",
        "Czytanie z Księgi proroka Ezechiela",
        "Podczas widzenia otrzymanego od Pana zaprowadził mnie anioł.",
        "Oto słowo Boże.",
        "PSALM RESPONSORYJNY",
        "Ps 46,2-3.5-6.8-9",
        "Refren: Bóg jest we wnętrzu swojego Kościoła.",
        "Bóg jest dla nas ucieczką i siłą.",
        "Refren",
        "DRUGIE CZYTANIE",
        "1 Kor 3.9b-11.16-17",
        "Jesteście Bożą budowlą",
        "Czytanie z Pierwszego Listu świętego Pawła Apostoła do Koryntian",
        "Bracia: Jesteście uprawną rolą Bożą i Bożą budowlą.",
        "Oto słowo Boże.",
        "ŚPIEW PRZED EWANGELIĄ",
        "2 Krn 7,16",
        "Aklamacja: Alleluja, alleluja, alleluja.",
        "Wybrałem i uświęciłem tę świątynię,",
        "aby moja obecność trwała tam na wieki.",
        "Aklamacja: Alleluja, alleluja, alleluja.",
        "EWANGELIA",
        "J 2,13-22",
        "Mówił o świątyni swego ciała",
        "Słowa Ewangelii według świętego Jana",
        "Zbliżała się pora Paschy żydowskiej.",
        "Oto słowo Pańskie.",
    ]


@pytest.fixture(autouse=True)
def clear_brewiarz_cache():
    create_graphic._brewiarz_cache.clear()
    yield
    create_graphic._brewiarz_cache.clear()


def _brewiarz(has_second):
    return patch.object(create_graphic, "_brewiarz_has_second_reading", return_value=has_second)


class TestBrewiarzUrls:
    def test_general_calendar_folder_first(self):
        assert _brewiarz_urls("2026-11-09") == [
            "https://brewiarz.pl/xi_26/0911p/czyt.php3",
            "https://brewiarz.pl/xi_26/0911/czyt.php3",
        ]

    def test_roman_month_and_padding(self):
        assert _brewiarz_urls("2027-02-02")[0] == "https://brewiarz.pl/ii_27/0202p/czyt.php3"


class TestBrewiarzCheck:
    def _page(self, body, status=200):
        resp = MagicMock(status_code=status)
        resp.content = f"<html><body>{body}</body></html>".encode("utf-8")
        return resp

    def test_alternative_first_reading_page(self):
        page = self._page(
            "<p>PIERWSZE CZYTANIE</p><p>Ez 47</p><p>Albo:</p>"
            "<p>PIERWSZE CZYTANIE</p><p>1 Kor 3</p>"
            "<p>WPROWADZENIE DO PIERWSZEGO CZYTANIA</p><p>PSALM RESPONSORYJNY</p>"
        )
        with patch.object(create_graphic.requests, "get", return_value=page):
            assert _brewiarz_has_second_reading(WEEKDAY_FEAST) is False

    def test_sunday_page_has_second_reading(self):
        page = self._page(
            "<p>PIERWSZE CZYTANIE</p><p>DRUGIE CZYTANIE DŁUŻSZE</p>"
            "<p>WPROWADZENIE DO DRUGIEGO CZYTANIA</p>"
        )
        with patch.object(create_graphic.requests, "get", return_value=page):
            assert _brewiarz_has_second_reading(ORDINARY_SUNDAY) is True

    def test_intro_heading_alone_is_not_a_second_reading(self):
        page = self._page("<p>PIERWSZE CZYTANIE</p><p>WPROWADZENIE DO DRUGIEGO CZYTANIA</p>")
        with patch.object(create_graphic.requests, "get", return_value=page):
            assert _brewiarz_has_second_reading(WEEKDAY_FEAST) is False

    def test_falls_back_to_bare_folder(self):
        missing = self._page("Not found", status=404)
        page = self._page("<p>PIERWSZE CZYTANIE</p>")
        with patch.object(create_graphic.requests, "get", side_effect=[missing, page]) as get:
            assert _brewiarz_has_second_reading(WEEKDAY_FEAST) is False
        assert get.call_args_list[1].args[0].endswith("/0911/czyt.php3")

    def test_unreachable_returns_none_and_is_not_cached(self):
        with patch.object(create_graphic.requests, "get", side_effect=OSError("offline")):
            assert _brewiarz_has_second_reading(WEEKDAY_FEAST) is None
        assert WEEKDAY_FEAST not in create_graphic._brewiarz_cache

    def test_answer_is_cached(self):
        page = self._page("<p>PIERWSZE CZYTANIE</p>")
        with patch.object(create_graphic.requests, "get", return_value=page) as get:
            _brewiarz_has_second_reading(WEEKDAY_FEAST)
            _brewiarz_has_second_reading(WEEKDAY_FEAST)
        assert get.call_count == 1


class TestHasAlternative:
    def test_brewiarz_without_second_reading(self):
        dic = _parse_readings(_wiara_content_list())
        with _brewiarz(False):
            assert _has_alternative_first_reading(WEEKDAY_FEAST, dic)

    def test_brewiarz_with_second_reading(self):
        dic = _parse_readings(_wiara_content_list())
        with _brewiarz(True):
            assert not _has_alternative_first_reading(SUNDAY_FEAST, dic)

    def test_no_brewiarz_call_without_second_reading_on_wiara(self):
        dic = {"PIERWSZE CZYTANIE": ["x"], "EWANGELIA": ["y"]}
        with _brewiarz(False) as check:
            assert not _has_alternative_first_reading(WEEKDAY_FEAST, dic)
        check.assert_not_called()

    def test_fallback_weekday_feast(self):
        dic = _parse_readings(_wiara_content_list())
        with _brewiarz(None):
            assert _has_alternative_first_reading(WEEKDAY_FEAST, dic)

    def test_fallback_sunday_feast_keeps_second_reading(self):
        dic = _parse_readings(_wiara_content_list())
        with _brewiarz(None):
            assert not _has_alternative_first_reading(SUNDAY_FEAST, dic)

    def test_fallback_other_weekday_keeps_second_reading(self):
        # e.g. a weekday solemnity (All Saints 2027-11-01 is a Monday)
        dic = _parse_readings(_wiara_content_list())
        with _brewiarz(None):
            assert not _has_alternative_first_reading("2027-11-01", dic)


class TestApplyChoice:
    def test_default_keeps_first_option_only(self):
        dic = _parse_readings(_wiara_content_list())
        with _brewiarz(False):
            _apply_first_reading_choice(dic, WEEKDAY_FEAST, 0)
        assert "DRUGIE CZYTANIE" not in dic
        assert dic["PIERWSZE CZYTANIE"][0] == "Ez 47,1-2.8-9.12"

    def test_alternative_takes_first_reading_slot(self):
        dic = _parse_readings(_wiara_content_list())
        with _brewiarz(False):
            _apply_first_reading_choice(dic, WEEKDAY_FEAST, 1)
        assert "DRUGIE CZYTANIE" not in dic
        assert dic["PIERWSZE CZYTANIE"][0] == "1 Kor 3.9b-11.16-17"
        assert dic["PIERWSZE CZYTANIE"][-1] == "Oto słowo Boże."
        assert list(dic) == ["PIERWSZE CZYTANIE", "PSALM RESPONSORYJNY", "EWANGELIA"]

    def test_acclamation_moves_to_psalm(self):
        dic = _parse_readings(_wiara_content_list())
        with _brewiarz(False):
            _apply_first_reading_choice(dic, WEEKDAY_FEAST, 1)
        psalm = dic["PSALM RESPONSORYJNY"]
        assert psalm[psalm.index("ŚPIEW PRZED EWANGELIĄ") + 1] == "2 Krn 7,16"
        assert "ŚPIEW PRZED EWANGELIĄ" not in dic["PIERWSZE CZYTANIE"]

    def test_choice_as_string_from_browser(self):
        dic = _parse_readings(_wiara_content_list())
        with _brewiarz(False):
            _apply_first_reading_choice(dic, WEEKDAY_FEAST, "1")
        assert dic["PIERWSZE CZYTANIE"][0] == "1 Kor 3.9b-11.16-17"

    def test_real_second_reading_untouched(self):
        dic = _parse_readings(_wiara_content_list())
        with _brewiarz(True):
            _apply_first_reading_choice(dic, SUNDAY_FEAST, 1)
        assert dic["PIERWSZE CZYTANIE"][0] == "Ez 47,1-2.8-9.12"
        assert dic["DRUGIE CZYTANIE"][0] == "1 Kor 3.9b-11.16-17"


class TestDrawPostIntegration:
    def test_weekday_feast_renders_one_first_reading(self, tmp_path):
        with patch.object(create_graphic, "_scrape_content_list", return_value=_wiara_content_list()), \
             patch.object(create_graphic, "WEB_DIR", tmp_path), \
             _brewiarz(False), \
             patch.object(create_graphic, "_generate_reading_images",
                          side_effect=lambda dic, *a, **k: [f"{n}.jpg" for n in dic if "PSALM" not in n]) as gen, \
             patch.object(create_graphic, "_generate_psalm_image", return_value="PSALM RESPONSORYJNY.jpg"):
            box = create_graphic.draw_post(WEEKDAY_FEAST, 1)

        assert box[1:] == ["PIERWSZE CZYTANIE.jpg", "EWANGELIA.jpg", "PSALM RESPONSORYJNY.jpg"]
        rendered = gen.call_args.args[0]
        assert rendered["PIERWSZE CZYTANIE"][0] == "1 Kor 3.9b-11.16-17"
        assert "ŚPIEW PRZED EWANGELIĄ" in rendered["PSALM RESPONSORYJNY"]

    def test_first_reading_options(self):
        with patch.object(create_graphic, "_scrape_content_list", return_value=_wiara_content_list()), \
             _brewiarz(False):
            assert create_graphic.get_first_reading_options(WEEKDAY_FEAST) == [
                "Ez 47,1-2.8-9.12", "1 Kor 3.9b-11.16-17",
            ]
        with patch.object(create_graphic, "_scrape_content_list", return_value=_wiara_content_list()), \
             _brewiarz(True):
            assert create_graphic.get_first_reading_options(SUNDAY_FEAST) == []
