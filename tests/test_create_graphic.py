"""
Tests for create_graphic.py module.
"""

import pytest

from create_graphic import (
    _build_caption,
    _clean_content_list,
    _normalize_readings,
    _parse_readings,
    _add_psalm_refrains,
    _truncate_readings,
    _clean_gospel_markers,
    _remove_pre_gospel_from_reading,
    _create_two_page_pagination,
    _create_four_page_pagination,
    _estimate_text_height,
    _calculate_optimal_pagination,
    _extract_vigil_page_nums,
    _mark_psalm_stanza_refrains,
    MAX_PAGES_PER_READING,
)
from draw_posts import _calculate_layout


class TestCleanContentList:
    """Tests for _clean_content_list function."""

    def test_removes_empty_trailing_elements(self):
        content = ["text1", "text2", "", "", ""]
        result = _clean_content_list(content)
        assert result[-1] != ""

    def test_removes_liturgia_slowa_header(self):
        content = ["Liturgia Słowa", "PIERWSZE CZYTANIE", "content"]
        result = _clean_content_list(content)
        assert "Liturgia Słowa" not in result

    def test_removes_empty_strings(self):
        content = ["text1", "", "text2", "", "text3"]
        result = _clean_content_list(content)
        assert "" not in result

    def test_strips_whitespace(self):
        content = ["  text with spaces  ", "\ttext with tab\t"]
        result = _clean_content_list(content)
        assert result[0] == "text with spaces"
        assert result[1] == "text with tab"

    def test_skips_passion_content(self):
        content = ["normal text", "Jezus przed Piłatem", "more text"]
        result = _clean_content_list(content)
        assert "Jezus przed Piłatem" not in result

    def test_skips_passion_rubric_legend_lines(self):
        content = [
            "normal text",
            "+ — słowa Chrystusa",
            "E — słowa Ewangelisty",
            "I — słowa innych osób pojedynczych",
            "T — słowa kilku osób lub tłumu",
            "more scripture text",
        ]
        result = _clean_content_list(content)
        joined = " ".join(result)
        assert "słowa Chrystusa" not in joined
        assert "słowa Ewangelisty" not in joined
        assert "słowa innych osób pojedynczych" not in joined
        assert "słowa kilku osób lub tłumu" not in joined
        assert "normal text" in result
        assert "more scripture text" in result

    def test_judasz_header_removed_but_scripture_kept(self):
        content = [
            "Judasz",
            "Także i Judasz, który Go wydał, znał to miejsce.",
        ]
        result = _clean_content_list(content)
        assert "Judasz" not in result
        assert any("Judasz" in line for line in result)

    def test_skips_good_friday_section_headers(self):
        content = [
            "Przed Piłatem",
            "Przesłuchanie",
            "\u201eOto człowiek\u201d",
            "Wyrok",
            "Testament dany z krzyża",
            "Przebicie serca",
            "Złożenie Jezusa do grobu",
            "scripture paragraph stays",
        ]
        result = _clean_content_list(content)
        assert result == ["scripture paragraph stays"]


class TestNormalizeReadings:
    """Tests for _normalize_readings function."""

    def test_replaces_shorter_reading_names(self):
        content = ["PIERWSZE CZYTANIE KRÓTSZE", "content", "Oto słowo Boże"]
        result = _normalize_readings(content)
        assert "PIERWSZE CZYTANIE" in result[0]
        assert "KRÓTSZE" not in result[0]

    def test_replaces_ewangelia_krotsza(self):
        content = ["EWANGELIA KRÓTSZA", "content"]
        result = _normalize_readings(content)
        assert "KRÓTSZA" not in str(result)

    def test_normalizes_psalm_name(self):
        content = [".PSALM RESPONSORYJNY", "content"]
        result = _normalize_readings(content)
        assert result[0] == "PSALM RESPONSORYJNY"

    def test_combined_longer_shorter_gospel_prefers_shorter(self):
        # Format seen on 2026-07-12: one Gospel text, stacked references,
        # inline "Koniec krótszej perykopy." end marker
        content = [
            "EWANGELIA DŁUŻSZA",
            "Mt 13, 1-23",
            "KRÓTSZA",
            "Mt 13, 1-9",
            "Przypowieść o siewcy",
            "Słowa Ewangelii według Świętego Mateusza",
            "Owego dnia Jezus wyszedł z domu i usiadł nad jeziorem.",
            "«Oto siewca wyszedł siać».",
            "Koniec krótszej perykopy.",
            "Przystąpili do Niego uczniowie i zapytali.",
            "Oto słowo Pańskie.",
        ]
        result = _normalize_readings(content)
        assert result[0] == "EWANGELIA"
        assert result[1] == "Mt 13, 1-9"
        assert result[2] == "Przypowieść o siewcy"
        assert "Koniec krótszej perykopy." not in result
        assert "Przystąpili do Niego uczniowie i zapytali." not in result
        assert result[-1] == "Oto słowo Pańskie."
        assert "DŁUŻSZA" not in str(result)
        assert "KRÓTSZA" not in str(result)

    def test_combined_gospel_without_end_marker_uses_longer(self):
        content = [
            "EWANGELIA DŁUŻSZA",
            "Mt 13, 1-23",
            "KRÓTSZA",
            "Mt 13, 1-9",
            "Przypowieść o siewcy",
            "Słowa Ewangelii według Świętego Mateusza",
            "Owego dnia Jezus wyszedł z domu i usiadł nad jeziorem.",
            "Przystąpili do Niego uczniowie i zapytali.",
            "Oto słowo Pańskie.",
        ]
        result = _normalize_readings(content)
        assert result[0] == "EWANGELIA"
        assert result[1] == "Mt 13, 1-23"
        assert "Przystąpili do Niego uczniowie i zapytali." in result
        assert result[-1] == "Oto słowo Pańskie."


class TestParseReadings:
    """Tests for _parse_readings function."""

    def test_parses_basic_readings(self, sample_content_list):
        cleaned = _clean_content_list(sample_content_list)
        result = _parse_readings(cleaned)

        assert "PIERWSZE CZYTANIE" in result
        assert "PSALM RESPONSORYJNY" in result
        assert "EWANGELIA" in result

    def test_returns_dict_with_lists(self, sample_content_list):
        cleaned = _clean_content_list(sample_content_list)
        result = _parse_readings(cleaned)

        for key, value in result.items():
            assert isinstance(value, list)


class TestAddPsalmRefrains:
    """Tests for _add_psalm_refrains function."""

    def test_adds_refrains_to_long_psalm(self):
        content_dic = {
            "PSALM RESPONSORYJNY": [
                "Ps 104",
                "Refren: Test refrain",
                "verse 1", "verse 2", "verse 3",
                "verse 4", "verse 5", "verse 6",
                "verse 7", "verse 8", "verse 9",
            ]
        }
        _add_psalm_refrains(content_dic)

        refrain_count = sum(1 for item in content_dic["PSALM RESPONSORYJNY"] if "Refren" in item)
        assert refrain_count > 1

    def test_does_nothing_for_short_psalm(self):
        content_dic = {
            "PSALM RESPONSORYJNY": ["Ps 104", "Refren: Test", "verse 1"]
        }
        original_len = len(content_dic["PSALM RESPONSORYJNY"])
        _add_psalm_refrains(content_dic)

        assert len(content_dic["PSALM RESPONSORYJNY"]) == original_len


class TestTruncateReadings:
    """Tests for _truncate_readings function."""

    def test_truncates_first_reading(self):
        content_dic = {
            "PIERWSZE CZYTANIE": [
                "Rdz 1, 1-5",
                "Czytanie",
                "content",
                "Oto słowo Boże",
                "extra content that should be removed",
            ]
        }
        _truncate_readings(content_dic)

        assert content_dic["PIERWSZE CZYTANIE"][-1] == "Oto słowo Boże"

    def test_truncates_gospel(self):
        content_dic = {
            "EWANGELIA": [
                "J 1, 1-5",
                "Słowa Ewangelii",
                "content",
                "Oto słowo Pańskie.",
                "should be removed",
            ]
        }
        _truncate_readings(content_dic)

        assert content_dic["EWANGELIA"][-1] == "Oto słowo Pańskie."


class TestCleanGospelMarkers:
    """Tests for _clean_gospel_markers function."""

    def test_removes_speaker_markers(self):
        content_dic = {
            "EWANGELIA": [
                "J 1, 1-5",
                "I. Narrator text",
                "T. Crowd text",
                "+ Jesus text",
            ]
        }
        _clean_gospel_markers(content_dic)

        assert "I." not in content_dic["EWANGELIA"][1]
        assert "T." not in content_dic["EWANGELIA"][2]
        assert "+" not in content_dic["EWANGELIA"][3]


class TestRemovePreGospelFromReading:
    """Tests for _remove_pre_gospel_from_reading function."""

    def test_removes_pre_gospel_acclamation(self):
        content_dic = {
            "DRUGIE CZYTANIE": [
                "Rz 1, 1-5",
                "content1",
                "content2",
                "Oto słowo Boże",
                "ŚPIEW PRZED EWANGELIĄ",
                "extra1",
                "extra2",
            ]
        }
        _remove_pre_gospel_from_reading(content_dic)

        assert "ŚPIEW PRZED EWANGELIĄ" not in content_dic["DRUGIE CZYTANIE"]

    def test_does_nothing_without_second_reading(self):
        content_dic = {
            "PIERWSZE CZYTANIE": ["content"]
        }
        _remove_pre_gospel_from_reading(content_dic)

        assert "PIERWSZE CZYTANIE" in content_dic


class TestCreateTwoPagePagination:
    """Tests for _create_two_page_pagination function."""

    def test_splits_content_at_break_point(self):
        content = ["line1", "line2", "line3", "line4", "line5", "line6"]
        result = _create_two_page_pagination("TEST", content, break_point=3)

        assert len(result) == 2
        assert "TEST cz.1" in result
        assert "TEST cz.2" in result

    def test_first_page_includes_name(self):
        content = ["line1", "line2", "line3", "line4"]
        result = _create_two_page_pagination("TEST", content, break_point=2)

        assert "TEST" in result["TEST cz.1"]

    def test_correct_content_distribution(self):
        content = ["a", "b", "c", "d", "e", "f"]
        result = _create_two_page_pagination("TEST", content, break_point=3)

        # First page: name + first 3 items
        assert len(result["TEST cz.1"]) == 4  # name + 3 items
        # Second page: remaining 3 items
        assert len(result["TEST cz.2"]) == 3


class TestCreateFourPagePagination:
    """Tests for _create_four_page_pagination function."""

    def test_splits_into_four_pages(self):
        content = list(range(30))  # 30 items
        result = _create_four_page_pagination("TEST", content, break_point=5)

        assert len(result) == 4

    def test_page_keys_are_correct(self):
        content = list(range(30))
        result = _create_four_page_pagination("TEST", content, break_point=5)

        assert "TEST cz.1" in result
        assert "TEST cz.2" in result
        assert "TEST cz.3" in result
        assert "TEST cz.6" in result


class TestBuildCaption:
    """Tests for _build_caption — verifies the *** footer block appears exactly once."""

    def test_single_asterisks_block_with_plain_caption(self):
        result = _build_caption("Czytanie z dnia.", "2026-03-24")
        assert result.count("***") == 1

    def test_single_asterisks_block_when_caption_already_contains_footer(self):
        # Regression: the old JS textarea appended the footer too, causing duplication
        caption_with_footer = "Czytanie z dnia.\n***\nGrafika wykonana za pomocą sztucznej inteligencji."
        result = _build_caption(caption_with_footer, "2026-03-24")
        assert result.count("***") == 1

    def test_ai_credit_appears_exactly_once(self):
        result = _build_caption("Czytanie z dnia.", "2026-03-24")
        assert result.count("Grafika wykonana za pomocą sztucznej inteligencji.") == 1

    def test_date_included_in_caption(self):
        result = _build_caption("Czytanie z dnia.", "2026-03-24")
        assert "2026-03-24" in result

    def test_caption_text_preserved(self):
        result = _build_caption("Pierwsze czytanie.", "2026-03-24")
        assert result.startswith("Pierwsze czytanie.")


class TestPaginationWidthFormula:
    """Ensure estimation width is conservative relative to the rendering layout."""

    @pytest.mark.parametrize("font_size", [30, 34, 40, 44, 50, 60])
    def test_width_conservative_vs_layout(self, font_size):
        # Estimation uses layout width minus 3-char safety margin
        size_x_left = int(25 / 12 * font_size)
        est_width = int(75 - 0.325 * size_x_left) - 3

        layout = _calculate_layout(font_size)

        assert est_width == layout["width"] - 3
        assert est_width < layout["width"]


class TestGospelPagination:
    """Ensure regular Gospels don't produce too many pages."""

    def _make_gospel_content(self, body_chars=2000):
        """Build a realistic Gospel content list with ~body_chars of body text."""
        header = ["J 20, 11-18", "Słowa Ewangelii według Świętego Jana", "W pierwszy dzień tygodnia:"]
        # Build body paragraphs ~200 chars each
        para = "Jezus powiedział do swoich uczniów słowa, które napełniły ich serca radością i nadzieją na przyszłość, bo wiedzieli że Pan jest z nimi zawsze aż do skończenia świata. "
        num_paras = body_chars // len(para)
        body = [para.strip() for _ in range(max(num_paras, 1))]
        closing = "Oto Słowo Pańskie."
        return header + body + [closing]

    def test_regular_gospel_max_4_pages(self):
        content = self._make_gospel_content(2000)
        num_pages, font, pages = _calculate_optimal_pagination(
            content, 44, reading_name="EWANGELIA", max_pages=MAX_PAGES_PER_READING,
        )
        assert num_pages <= MAX_PAGES_PER_READING

    def test_short_gospel_single_page(self):
        content = self._make_gospel_content(400)
        num_pages, font, pages = _calculate_optimal_pagination(
            content, 44, reading_name="EWANGELIA", max_pages=MAX_PAGES_PER_READING,
        )
        assert num_pages == 1


class TestExtractVigilPageNums:
    """Tests for _extract_vigil_page_nums (content_index sub-page detection)."""

    def _make_idx_div(self, links):
        from bs4 import BeautifulSoup
        html = '<div class="content_index">' + "".join(
            f'<a href="{href}">{text}</a>' for href, text in links
        ) + "</div>"
        return BeautifulSoup(html, "html.parser").find("div", "content_index")

    def test_easter_vigil_reading_links_are_combined(self):
        idx_div = self._make_idx_div([
            ("/kalendarz/x/2026-04-04/1#Par1", "PIERWSZE CZYTANIE dłuższe"),
            ("/kalendarz/x/2026-04-04/1#Par3", "1 PSALM RESPONSORYJNY"),
            ("/kalendarz/x/2026-04-04/3#Par7", "TRZECIE CZYTANIE"),
            ("/kalendarz/x/2026-04-04/8#Par17", "ÓSME CZYTANIE (EPISTOŁA)"),
            ("/kalendarz/x/2026-04-04/9#Par19", "EWANGELIA W ROKU A"),
            ("/kalendarz/x/2026-04-04/10#Par22", "LITURGIA SŁOWA WG STAREGO LEKCJONARZA"),
        ])
        assert _extract_vigil_page_nums(idx_div) == {1, 3, 8, 9}

    def test_assumption_alternative_masses_not_combined(self):
        # Aug 15: day Mass + vigil Mass + video pages are alternatives, not parts
        idx_div = self._make_idx_div([
            ("/kalendarz/x/2026-08-15/1#Par1", "Czytania mszalne z dnia"),
            ("/kalendarz/x/2026-08-15/2#Par2", "Czytania mszalne wigilii"),
            ("/kalendarz/x/2026-08-15/4#Par3", "Liturgia Słowa z dnia do odsłuchania (wersja wideo)"),
            ("/kalendarz/x/2026-08-15/5#Par4", "Liturgia Słowa z Mszy wigilii do odsłuchania (wersja wideo)"),
        ])
        assert _extract_vigil_page_nums(idx_div) == set()

    def test_christmas_alternative_masses_not_combined(self):
        idx_div = self._make_idx_div([
            ("/kalendarz/x/2025-12-25/1#Par1", "Liturgia Słowa wg lekcjonarza z 2015 roku - Msza Wigilii"),
            ("/kalendarz/x/2025-12-25/3#Par3", "Liturgia Słowa wg lekcjonarza z 2015 roku - Msza w nocy"),
            ("/kalendarz/x/2025-12-25/7#Par7", "Liturgia Słowa wg lekcjonarza z 2015 roku - Msza w dzień"),
            ("/kalendarz/x/2025-12-25/9#Par9", "Liturgia Słowa według starego lekcjonarza"),
        ])
        assert _extract_vigil_page_nums(idx_div) == set()


class TestMarkPsalmStanzaRefrains:
    """Tests for _mark_psalm_stanza_refrains (stanza breaks → Refren markers)."""

    def _psalm_section(self):
        return [
            "PSALM RESPONSORYJNY",
            "Ps 45,7.10-12.14-15",
            "Refren: Stoi Królowa po Twojej prawicy.",
            "",
            "Tron Twój, Boże, trwa na wieki,",
            "berłem sprawiedliwym berło Twego królestwa.",
            "",
            "Posłuchaj, córko, spójrz i nakłoń ucha,",
            "zapomnij o swym ludzie, o domu twego ojca.",
            "",
            "Córa królewska wchodzi pełna chwały,",
            "odziana w złotogłów.",
        ]

    def test_inserts_refren_at_each_stanza_break(self):
        result = _mark_psalm_stanza_refrains(self._psalm_section() + ["DRUGIE CZYTANIE", "1 Kor 15,20-26"])
        psalm_part = result[: result.index("DRUGIE CZYTANIE")]
        assert psalm_part.count("Refren") == 3

    def test_refren_closes_last_stanza(self):
        result = _mark_psalm_stanza_refrains(self._psalm_section() + ["EWANGELIA", "Łk 1,39-56"])
        psalm_part = result[: result.index("EWANGELIA")]
        assert psalm_part[-1] == "Refren"

    def test_no_refren_between_header_and_first_stanza(self):
        result = _mark_psalm_stanza_refrains(self._psalm_section() + ["EWANGELIA"])
        refrain_header_idx = next(i for i, l in enumerate(result) if l.startswith("Refren:"))
        assert result[refrain_header_idx + 1] == "Tron Twój, Boże, trwa na wieki,"

    def test_psalm_without_blank_breaks_unchanged(self):
        content = [
            "PSALM RESPONSORYJNY",
            "Ps 23",
            "Refren: Pan mym pasterzem.",
            "Wers 1.",
            "Wers 2.",
            "EWANGELIA",
        ]
        assert _mark_psalm_stanza_refrains(content) == content

    def test_numbered_alternative_refrains_stay_with_header(self):
        content = [
            "PSALM RESPONSORYJNY",
            "Ps 46",
            "Refren:",
            "",
            "1. Kościół nie zginie, Bóg jest w jego wnętrzu.",
            "2. Tyś wielką chlubą Kościoła świętego.",
            "",
            "Wers pierwszej strofy.",
            "Wers drugi.",
            "",
            "Wers trzeciej strofy.",
            "Wers czwarty.",
            "EWANGELIA",
        ]
        result = _mark_psalm_stanza_refrains(content)
        alt_idx = result.index("1. Kościół nie zginie, Bóg jest w jego wnętrzu.")
        assert result[alt_idx + 1] == "2. Tyś wielką chlubą Kościoła świętego."
        psalm_part = result[: result.index("EWANGELIA")]
        assert psalm_part.count("Refren") == 2

    def test_non_psalm_content_untouched(self):
        content = ["PIERWSZE CZYTANIE", "Ref", "Treść.", "", "Dalsza treść.", "EWANGELIA"]
        assert _mark_psalm_stanza_refrains(content) == content


class TestPublishReplyParsing:
    """publish() must not report failure when the post went live but instagrapi
    could not parse Instagram's reply (account_badges ints, Oct 2026)."""

    @staticmethod
    def _validation_error():
        from pydantic import BaseModel

        class Badged(BaseModel):
            account_badges: list[dict]

        try:
            Badged(account_badges=[0])
        except Exception as e:
            return e

    @staticmethod
    def _client(tmp_path, last_json, error):
        from unittest.mock import MagicMock
        from PIL import Image

        post_dir = tmp_path / "2026-10-14"
        post_dir.mkdir()
        Image.new("RGB", (100, 100), "white").save(post_dir / "cover.jpg")
        (post_dir / "EWANGELIA.jpg").write_bytes(b"fake")

        client = MagicMock()
        client.album_upload.side_effect = error
        client.last_json = last_json
        return client

    def test_reply_parse_error_after_success_is_success(self, tmp_path):
        from unittest.mock import patch
        from create_graphic import publish

        client = self._client(tmp_path, {"status": "ok", "media": {"pk": "1"}}, self._validation_error())
        with patch("create_graphic.login_user", return_value=client), patch("create_graphic.WEB_DIR", tmp_path):
            assert publish("2026-10-14", "caption") == ""

    def test_reply_parse_error_without_ok_status_is_failure(self, tmp_path):
        from unittest.mock import patch
        from create_graphic import publish

        client = self._client(tmp_path, {"status": "fail"}, self._validation_error())
        with patch("create_graphic.login_user", return_value=client), patch("create_graphic.WEB_DIR", tmp_path):
            assert publish("2026-10-14", "caption").startswith("Failed to publish")

    def test_other_errors_still_fail(self, tmp_path):
        from unittest.mock import patch
        from create_graphic import publish

        client = self._client(tmp_path, {"status": "ok", "media": {"pk": "1"}}, RuntimeError("network down"))
        with patch("create_graphic.login_user", return_value=client), patch("create_graphic.WEB_DIR", tmp_path):
            assert publish("2026-10-14", "caption") == "Failed to publish: network down"
