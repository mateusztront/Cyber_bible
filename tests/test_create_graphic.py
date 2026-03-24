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
)


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
