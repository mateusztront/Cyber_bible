"""
Tests for Easter week special handling in create_graphic.py.
Covers: Palm Sunday (PROCESJA, Passion split), Easter Sunday (SEKWENCJA),
        Good Friday (Passion detection), Holy Saturday (Vigil parsing/filtering).
"""

import pytest
from unittest.mock import MagicMock, patch, call
from pathlib import Path

from create_graphic import (
    _normalize_readings,
    _normalize_vigil_markers,
    _parse_readings,
    _parse_vigil_readings,
    _filter_easter_vigil,
    _normalize_sekwencja_content,
    _add_psalm_refrains,
    _truncate_readings,
)
from config import EASTER_VIGIL_OT_READING_INDICES


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def procesja_content_list():
    """Palm Sunday raw content with PROCESJA Z PALMAMI before main readings."""
    return [
        "PROCESJA Z PALMAMI",
        "Mt 21, 1-11",
        "Słowa Ewangelii według Świętego Mateusza",
        "Gdy Jezus i uczniowie zbliżali się do Jerozolimy.",
        "Oto słowo Pańskie.",
        "PIERWSZE CZYTANIE",
        "Iz 50, 4-7",
        "Czytanie z Księgi Izajasza",
        "Pan Bóg otworzył mi ucho.",
        "Oto słowo Boże.",
        "PSALM RESPONSORYJNY",
        "Ps 22",
        "Refren: Boże mój, czemuś mnie opuścił?",
        "Wszyscy, którzy mnie widzą, szydzą ze mnie.",
        "Refren",
        "EWANGELIA",
        "Mt 27, 11-54",
        "Słowa Ewangelii według Świętego Mateusza",
        "Jezus stanął przed namiestnikiem.",
        "Oto słowo Pańskie.",
    ]


@pytest.fixture
def sekwencja_content_list():
    """Easter Sunday raw content with SEKWENCJA between DRUGIE and EWANGELIA."""
    return [
        "PIERWSZE CZYTANIE",
        "Dz 10, 34a. 37-43",
        "Czytanie z Dziejów Apostolskich",
        "Wstał Jezus z martwych.",
        "Oto słowo Boże.",
        "PSALM RESPONSORYJNY",
        "Ps 118",
        "Refren: W tym dniu wspaniałym wszedł Pan.",
        "Dziękujcie Panu, bo jest dobry.",
        "Refren",
        "DRUGIE CZYTANIE",
        "Kol 3, 1-4",
        "Czytanie z Listu świętego Pawła Apostoła do Kolosan",
        "Jeśliście razem z Chrystusem powstali z martwych.",
        "Oto słowo Boże.",
        "SEKWENCJA",
        "Niech w święto radosne Paschalnej Ofiary.",
        "składają chrześcijanie ofiarę pochwalną.",
        "Baranek odkupił owce.",
        "Amen. Alleluja.",
        "EWANGELIA",
        "J 20, 1-9",
        "Słowa Ewangelii według Świętego Jana",
        "Pierwszego dnia po szabacie Maria Magdalena.",
        "Oto słowo Pańskie.",
    ]


@pytest.fixture
def vigil_content_list():
    """Easter Vigil content with numbered readings and psalms."""
    return [
        "PIERWSZE CZYTANIE",
        "Rdz 1, 1-2, 2",
        "Czytanie z Księgi Rodzaju",
        "Na początku Bóg stworzył niebo i ziemię.",
        "Oto słowo Boże.",
        "1 PSALM RESPONSORYJNY",
        "Ps 104",
        "Refren: Niech zstąpi Duch Twój.",
        "Błogosław, duszo moja, Pana.",
        "Refren",
        "DRUGIE CZYTANIE",
        "Rdz 22, 1-18",
        "Czytanie z Księgi Rodzaju",
        "Bóg wystawił Abrahama na próbę.",
        "Oto słowo Boże.",
        "2 PSALM RESPONSORYJNY",
        "Ps 16",
        "Refren: Strzeż mnie, o Boże.",
        "Zachowaj mnie, Boże.",
        "Refren",
        "TRZECIE CZYTANIE",
        "Wj 14, 15-15, 1",
        "Czytanie z Księgi Wyjścia",
        "Pan rzekł do Mojżesza.",
        "Oto słowo Boże.",
        "3 PSALM RESPONSORYJNY",
        "Wj 15",
        "Refren: Śpiewajmy Panu.",
        "Śpiewajmy pieśń chwały Panu.",
        "Refren",
        "CZWARTE CZYTANIE",
        "Iz 54, 5-14",
        "Czytanie z Księgi Izajasza",
        "Oblubieniec twój jest Stwórcą twoim.",
        "Oto słowo Boże.",
        "4 PSALM RESPONSORYJNY",
        "Ps 30",
        "Refren: Będę Cię wysławiał.",
        "Wysławiam Cię, Panie.",
        "Refren",
        "PIĄTE CZYTANIE",
        "Iz 55, 1-11",
        "Czytanie z Księgi Izajasza",
        "Wszyscy spragnieni, przyjdźcie do wody.",
        "Oto słowo Boże.",
        "5 PSALM RESPONSORYJNY",
        "Iz 12",
        "Refren: Będziecie czerpać wodę.",
        "Oto Bóg jest moim zbawieniem.",
        "Refren",
        "SZÓSTE CZYTANIE",
        "Ba 3, 9-15. 32-4, 4",
        "Czytanie z Księgi Barucha",
        "Posłuchaj, Izraelu, przykazań życia.",
        "Oto słowo Boże.",
        "6 PSALM RESPONSORYJNY",
        "Ps 19",
        "Refren: Słowa Twe, Panie, są duchem i życiem.",
        "Prawo Pańskie jest doskonałe.",
        "Refren",
        "SIÓDME CZYTANIE",
        "Ez 36, 16-17a. 18-28",
        "Czytanie z Księgi Ezechiela",
        "Pan skierował do mnie te słowa.",
        "Oto słowo Boże.",
        "7 PSALM RESPONSORYJNY",
        "Ps 42-43",
        "Refren: Jak łania pragnie wody.",
        "Jak łania pragnie wody ze strumieni.",
        "Refren",
        "ÓSME CZYTANIE",
        "Rz 6, 3-11",
        "Czytanie z Listu świętego Pawła do Rzymian",
        "My wszyscy, ochrzczeni w Chrystusie Jezusie.",
        "Oto słowo Boże.",
        "8 PSALM RESPONSORYJNY",
        "Ps 118",
        "Refren: Alleluja, alleluja, alleluja.",
        "Dziękujcie Panu, bo jest dobry.",
        "Refren",
        "EWANGELIA",
        "Mk 16, 1-7",
        "Słowa Ewangelii według Świętego Marka",
        "Po upływie szabatu Maria Magdalena.",
        "Oto słowo Pańskie.",
    ]


@pytest.fixture
def passion_content_dict():
    """Content dict simulating a long Passion Gospel (Palm Sunday / Good Friday)."""
    long_gospel = (
        ["Mt 26, 14-27, 66", "Słowa Ewangelii według Świętego Mateusza", "Jezus rzekł do uczniów:"]
        + [f"Werset pasyjny {i}." for i in range(20)]
        + ["Oto słowo Pańskie."]
    )
    return {
        "PIERWSZE CZYTANIE": ["Iz 50, 4-7", "Czytanie", "Intro.", "Treść.", "Oto słowo Boże."],
        "PSALM RESPONSORYJNY": ["Ps 22", "Refren: Test.", "Werset 1.", "Refren"],
        "DRUGIE CZYTANIE": ["Flp 2, 6-11", "Czytanie", "Intro.", "Treść.", "Oto słowo Boże."],
        "EWANGELIA": long_gospel,
    }


# ---------------------------------------------------------------------------
# _normalize_readings — PROCESJA Z PALMAMI
# ---------------------------------------------------------------------------

class TestNormalizeReadingsEaster:

    def test_strips_procesja_z_palmami(self, procesja_content_list):
        result = _normalize_readings(procesja_content_list)
        assert "PROCESJA Z PALMAMI" not in result

    def test_procesja_gospel_content_removed(self, procesja_content_list):
        result = _normalize_readings(procesja_content_list)
        # The processional gospel verses should be gone
        assert "Gdy Jezus i uczniowie zbliżali się do Jerozolimy." not in result

    def test_pierwsze_czytanie_preserved_after_procesja_strip(self, procesja_content_list):
        result = _normalize_readings(procesja_content_list)
        assert "PIERWSZE CZYTANIE" in result

    def test_keeps_sekwencja_in_list(self, sekwencja_content_list):
        result = _normalize_readings(sekwencja_content_list)
        assert "SEKWENCJA" in result

    def test_sekwencja_content_preserved(self, sekwencja_content_list):
        result = _normalize_readings(sekwencja_content_list)
        assert "Niech w święto radosne Paschalnej Ofiary." in result

    def test_removes_optional_sekwencja_note(self):
        content = [
            "DRUGIE CZYTANIE", "content", "Oto słowo Boże.",
            "Można odmawiać sekwencję: Niech w święto radosne Paschalnej Ofiary.",
            "SEKWENCJA", "Poem line.", "Amen. Alleluja.",
            "EWANGELIA", "content", "Oto słowo Pańskie.",
        ]
        result = _normalize_readings(content)
        assert "Można odmawiać sekwencję: Niech w święto radosne Paschalnej Ofiary." not in result

    def test_no_procesja_on_normal_day_unchanged(self):
        content = [
            "PIERWSZE CZYTANIE", "Rdz 1, 1", "Czytanie", "Treść.", "Oto słowo Boże.",
            "PSALM RESPONSORYJNY", "Ps 1", "Refren: test.", "Werset.",
            "EWANGELIA", "J 1, 1", "Słowa", "Treść.", "Oto słowo Pańskie.",
        ]
        result = _normalize_readings(content)
        assert "PIERWSZE CZYTANIE" in result
        assert "EWANGELIA" in result


# ---------------------------------------------------------------------------
# _parse_readings — SEKWENCJA cut_point
# ---------------------------------------------------------------------------

class TestParseReadingsEaster:

    def test_parses_sekwencja_as_separate_key(self, sekwencja_content_list):
        normalized = _normalize_readings(sekwencja_content_list)
        result = _parse_readings(normalized)
        assert "SEKWENCJA" in result

    def test_sekwencja_content_not_in_drugie_czytanie(self, sekwencja_content_list):
        normalized = _normalize_readings(sekwencja_content_list)
        result = _parse_readings(normalized)
        drugie = result.get("DRUGIE CZYTANIE", [])
        assert "SEKWENCJA" not in drugie
        assert "Niech w święto radosne Paschalnej Ofiary." not in drugie

    def test_ewangelia_not_contaminated_by_sekwencja(self, sekwencja_content_list):
        normalized = _normalize_readings(sekwencja_content_list)
        result = _parse_readings(normalized)
        ewangelia = result.get("EWANGELIA", [])
        assert "Amen. Alleluja." not in ewangelia

    def test_all_four_sections_present_on_easter_sunday(self, sekwencja_content_list):
        normalized = _normalize_readings(sekwencja_content_list)
        result = _parse_readings(normalized)
        for key in ("PIERWSZE CZYTANIE", "PSALM RESPONSORYJNY", "DRUGIE CZYTANIE", "SEKWENCJA", "EWANGELIA"):
            assert key in result, f"Missing key: {key}"

    def test_normal_day_no_sekwencja_key(self):
        content = [
            "PIERWSZE CZYTANIE", "Iz 1, 1", "Czytanie", "Treść.", "Oto słowo Boże.",
            "PSALM RESPONSORYJNY", "Ps 1", "Refren: test.", "Werset.",
            "DRUGIE CZYTANIE", "Rz 1, 1", "Czytanie", "Treść.", "Oto słowo Boże.",
            "EWANGELIA", "J 1, 1", "Słowa", "Treść.", "Oto słowo Pańskie.",
        ]
        result = _parse_readings(content)
        assert "SEKWENCJA" not in result


# ---------------------------------------------------------------------------
# _normalize_sekwencja_content
# ---------------------------------------------------------------------------

class TestNormalizeSekwencjaContent:

    def test_wraps_content_with_empty_reference_and_subtitle(self):
        content_dic = {
            "SEKWENCJA": ["Niech w święto radosne.", "Baranek odkupił owce.", "Amen. Alleluja."]
        }
        _normalize_sekwencja_content(content_dic)
        assert content_dic["SEKWENCJA"][0] == ""
        assert content_dic["SEKWENCJA"][1] == ""

    def test_closing_amen_alleluja_at_end(self):
        content_dic = {
            "SEKWENCJA": ["Linia 1.", "Amen. Alleluja.", "Linia 2."]
        }
        _normalize_sekwencja_content(content_dic)
        assert content_dic["SEKWENCJA"][-1] == "Amen. Alleluja."

    def test_amen_alleluja_added_if_missing(self):
        content_dic = {
            "SEKWENCJA": ["Linia 1.", "Linia 2."]
        }
        _normalize_sekwencja_content(content_dic)
        assert content_dic["SEKWENCJA"][-1] == "Amen. Alleluja."

    def test_strips_spiew_przed_ewangelia_from_content(self):
        content_dic = {
            "SEKWENCJA": [
                "Linia 1.", "Amen. Alleluja.",
                "ŚPIEW PRZED EWANGELIĄ", "Aklamacja.", "tekst.",
            ]
        }
        _normalize_sekwencja_content(content_dic)
        sekwencja = content_dic["SEKWENCJA"]
        assert "ŚPIEW PRZED EWANGELIĄ" not in sekwencja
        assert "Aklamacja." not in sekwencja

    def test_removes_empty_sekwencja_from_dict(self):
        content_dic = {"SEKWENCJA": ["", "   ", ""]}
        _normalize_sekwencja_content(content_dic)
        assert "SEKWENCJA" not in content_dic

    def test_does_nothing_when_no_sekwencja_key(self):
        content_dic = {"EWANGELIA": ["J 1, 1", "content", "Oto słowo Pańskie."]}
        _normalize_sekwencja_content(content_dic)
        assert "EWANGELIA" in content_dic  # unchanged


# ---------------------------------------------------------------------------
# _parse_vigil_readings
# ---------------------------------------------------------------------------

class TestParseVigilReadings:

    def test_parses_all_seven_ot_readings(self, vigil_content_list):
        result = _parse_vigil_readings(vigil_content_list)
        for key in ("PIERWSZE CZYTANIE", "DRUGIE CZYTANIE", "TRZECIE CZYTANIE",
                    "CZWARTE CZYTANIE", "PIĄTE CZYTANIE", "SZÓSTE CZYTANIE", "SIÓDME CZYTANIE"):
            assert key in result, f"Missing OT reading: {key}"

    def test_parses_epistle(self, vigil_content_list):
        result = _parse_vigil_readings(vigil_content_list)
        assert "ÓSME CZYTANIE" in result

    def test_parses_gospel(self, vigil_content_list):
        result = _parse_vigil_readings(vigil_content_list)
        assert "EWANGELIA" in result

    def test_parses_numbered_psalms(self, vigil_content_list):
        result = _parse_vigil_readings(vigil_content_list)
        for i in range(1, 9):
            assert f"{i} PSALM RESPONSORYJNY" in result, f"Missing psalm: {i} PSALM RESPONSORYJNY"

    def test_reading_content_not_contaminated_by_next_section(self, vigil_content_list):
        result = _parse_vigil_readings(vigil_content_list)
        # PIERWSZE CZYTANIE content should NOT include psalm content
        assert "1 PSALM RESPONSORYJNY" not in result["PIERWSZE CZYTANIE"]
        assert "Ps 104" not in result["PIERWSZE CZYTANIE"]

    def test_psalm_content_correct(self, vigil_content_list):
        result = _parse_vigil_readings(vigil_content_list)
        psalm1 = result["1 PSALM RESPONSORYJNY"]
        assert "Ps 104" in psalm1
        assert "Refren: Niech zstąpi Duch Twój." in psalm1

    def test_gospel_content_correct(self, vigil_content_list):
        result = _parse_vigil_readings(vigil_content_list)
        gospel = result["EWANGELIA"]
        assert "Mk 16, 1-7" in gospel
        assert "Po upływie szabatu Maria Magdalena." in gospel

    def test_returns_dict_of_lists(self, vigil_content_list):
        result = _parse_vigil_readings(vigil_content_list)
        for key, value in result.items():
            assert isinstance(value, list), f"{key} should be a list"


# ---------------------------------------------------------------------------
# _filter_easter_vigil
# ---------------------------------------------------------------------------

class TestFilterEasterVigil:

    def test_keeps_only_selected_ot_readings(self, vigil_content_list):
        full = _parse_vigil_readings(vigil_content_list)
        filtered = _filter_easter_vigil(full)

        ot_keys = [
            "PIERWSZE CZYTANIE", "DRUGIE CZYTANIE", "TRZECIE CZYTANIE",
            "CZWARTE CZYTANIE", "PIĄTE CZYTANIE", "SZÓSTE CZYTANIE", "SIÓDME CZYTANIE",
        ]
        kept = [k for k in ot_keys if k in filtered]
        expected = [ot_keys[i] for i in EASTER_VIGIL_OT_READING_INDICES if i < len(ot_keys)]
        assert kept == expected

    def test_always_keeps_epistle(self, vigil_content_list):
        full = _parse_vigil_readings(vigil_content_list)
        filtered = _filter_easter_vigil(full)
        assert "ÓSME CZYTANIE" in filtered

    def test_always_keeps_gospel(self, vigil_content_list):
        full = _parse_vigil_readings(vigil_content_list)
        filtered = _filter_easter_vigil(full)
        assert "EWANGELIA" in filtered

    def test_keeps_psalms_for_selected_readings(self, vigil_content_list):
        full = _parse_vigil_readings(vigil_content_list)
        filtered = _filter_easter_vigil(full)
        for idx in EASTER_VIGIL_OT_READING_INDICES:
            psalm_key = f"{idx + 1} PSALM RESPONSORYJNY"
            assert psalm_key in filtered, f"Missing psalm for reading {idx + 1}"

    def test_removes_non_selected_ot_readings(self, vigil_content_list):
        full = _parse_vigil_readings(vigil_content_list)
        filtered = _filter_easter_vigil(full)

        ot_keys = [
            "PIERWSZE CZYTANIE", "DRUGIE CZYTANIE", "TRZECIE CZYTANIE",
            "CZWARTE CZYTANIE", "PIĄTE CZYTANIE", "SZÓSTE CZYTANIE", "SIÓDME CZYTANIE",
        ]
        removed_indices = [i for i in range(7) if i not in EASTER_VIGIL_OT_READING_INDICES]
        for idx in removed_indices:
            assert ot_keys[idx] not in filtered, f"{ot_keys[idx]} should have been removed"

    def test_total_sections_is_expected_count(self, vigil_content_list):
        # 4 OT readings + 4 OT psalms + Epistle + Epistle psalm + Gospel = 11 sections.
        # Each vigil reading is short so most fit on 1 image — actual image count
        # after rendering should come in at or near the 10-image limit.
        full = _parse_vigil_readings(vigil_content_list)
        filtered = _filter_easter_vigil(full)
        expected = len(EASTER_VIGIL_OT_READING_INDICES) * 2 + 3  # readings + psalms + epistle + epistle psalm + gospel
        assert len(filtered) == expected


# ---------------------------------------------------------------------------
# _add_psalm_refrains — numbered vigil psalms
# ---------------------------------------------------------------------------

class TestAddPsalmRefrainVigil:

    def test_adds_refrains_to_numbered_psalm(self):
        content_dic = {
            "3 PSALM RESPONSORYJNY": [
                "Ps 42",
                "Refren: Jak łania pragnie wody.",
                "v1", "v2", "v3", "v4", "v5", "v6", "v7", "v8", "v9",
            ]
        }
        _add_psalm_refrains(content_dic)
        refrains = sum(1 for x in content_dic["3 PSALM RESPONSORYJNY"] if "Refren" in x)
        assert refrains > 1

    def test_handles_both_regular_and_numbered_psalms(self):
        content_dic = {
            "PSALM RESPONSORYJNY": [
                "Ps 1", "Refren: test.",
                "v1", "v2", "v3", "v4", "v5", "v6", "v7",
            ],
            "1 PSALM RESPONSORYJNY": [
                "Ps 2", "Refren: test2.",
                "v1", "v2", "v3", "v4", "v5", "v6", "v7",
            ],
        }
        _add_psalm_refrains(content_dic)
        r1 = sum(1 for x in content_dic["PSALM RESPONSORYJNY"] if "Refren" in x)
        r2 = sum(1 for x in content_dic["1 PSALM RESPONSORYJNY"] if "Refren" in x)
        assert r1 > 1
        assert r2 > 1


# ---------------------------------------------------------------------------
# _truncate_readings — vigil reading keys (TRZECIE, ÓSME, etc.)
# ---------------------------------------------------------------------------

class TestTruncateReadingsVigil:

    def test_truncates_trzecie_czytanie(self):
        content_dic = {
            "TRZECIE CZYTANIE": [
                "Wj 14, 15", "Czytanie", "Intro.",
                "Bóg rzekł do Mojżesza.",
                "Oto słowo Boże.",
                "extra text that should be gone",
            ]
        }
        _truncate_readings(content_dic)
        assert content_dic["TRZECIE CZYTANIE"][-1] == "Oto słowo Boże."

    def test_truncates_osme_czytanie(self):
        content_dic = {
            "ÓSME CZYTANIE": [
                "Rz 6, 3-11", "Czytanie", "Intro.",
                "Ochrzczeni w Chrystusie.",
                "Oto słowo Boże.",
                "should be removed",
            ]
        }
        _truncate_readings(content_dic)
        assert content_dic["ÓSME CZYTANIE"][-1] == "Oto słowo Boże."

    def test_truncates_with_period_variant(self):
        content_dic = {
            "PIĄTE CZYTANIE": [
                "Iz 55, 1", "Czytanie", "Treść.", "Oto słowo Boże.", "extra"
            ]
        }
        _truncate_readings(content_dic)
        assert content_dic["PIĄTE CZYTANIE"][-1] == "Oto słowo Boże."

    def test_all_seven_ot_readings_truncated(self, vigil_content_list):
        full = _parse_vigil_readings(vigil_content_list)
        _truncate_readings(full)
        ot_keys = [
            "PIERWSZE CZYTANIE", "DRUGIE CZYTANIE", "TRZECIE CZYTANIE",
            "CZWARTE CZYTANIE", "PIĄTE CZYTANIE", "SZÓSTE CZYTANIE", "SIÓDME CZYTANIE",
        ]
        for key in ot_keys:
            if key in full:
                assert full[key][-1] in ("Oto słowo Boże.", "Oto słowo Boże"), \
                    f"{key} not truncated correctly, ends with: {full[key][-1]!r}"


# ---------------------------------------------------------------------------
# Passion detection (integration: detect by Gospel length)
# ---------------------------------------------------------------------------

class TestPassionDetection:

    def test_long_gospel_detected_as_passion(self, passion_content_dict):
        from config import PASSION_SPLIT_THRESHOLD
        # Body paragraphs only (exclude 3 header items + 1 closing)
        gospel_body = len(passion_content_dict["EWANGELIA"]) - 4
        assert gospel_body > PASSION_SPLIT_THRESHOLD * 3, \
            "Fixture gospel should be long enough to trigger passion detection"

    def test_short_gospel_not_detected_as_passion(self):
        from config import PASSION_SPLIT_THRESHOLD
        short_gospel = ["J 20, 1-9", "Słowa Ewangelii", "Intro.", "Treść.", "Oto słowo Pańskie."]
        # Body paragraphs only (exclude 3 header items + 1 closing)
        body_count = max(len(short_gospel) - 4, 0)
        assert body_count <= PASSION_SPLIT_THRESHOLD * 3

    def test_medium_gospel_not_detected_as_passion(self):
        """A gospel with ~9 body paragraphs (like J 20, 11-18) should not be passion."""
        from config import PASSION_SPLIT_THRESHOLD
        medium_gospel = (
            ["J 20, 11-18", "Subtitle", "Intro bold"]
            + [f"Paragraph {i}." for i in range(9)]
            + ["Oto słowo Pańskie."]
        )
        body_count = max(len(medium_gospel) - 4, 0)
        assert body_count <= PASSION_SPLIT_THRESHOLD * 3

    def test_passion_header_normalization_accusative(self):
        """Accusative form 'Mękę...' is converted to nominative and moved to bold-intro slot."""
        from create_graphic import _normalize_passion_gospel_header
        content_dic = {
            "EWANGELIA": [
                "Mt 26, 14-27, 66",
                "Mękę naszego Pana Jezusa Chrystusa według świętego Mateusza",
                "Jezus rzekł do uczniów:",
                "Oto słowo Pańskie.",
            ]
        }
        _normalize_passion_gospel_header(content_dic)
        gospel = content_dic["EWANGELIA"]
        assert gospel[1] == "", "subtitle slot should be cleared"
        assert gospel[2] == "Męka naszego Pana Jezusa Chrystusa według świętego Mateusza"
        assert gospel[3] == "Jezus rzekł do uczniów:"

    def test_passion_rubric_lines_removed_by_clean(self):
        """Passion Gospel rubric/legend lines are removed during initial cleaning."""
        from create_graphic import _clean_content_list
        content = [
            "EWANGELIA",
            "J 18, 1 - 19, 42",
            "Mękę naszego Pana Jezusa Chrystusa według świętego Jana",
            "+ — słowa Chrystusa",
            "E — słowa Ewangelisty",
            "I — słowa innych osób pojedynczych",
            "T — słowa kilku osób lub tłumu",
            "Pojmanie Jezusa",
            "E. Po wieczerzy Jezus wyszedł z uczniami swymi za potok Cedron. Także i Judasz, który Go wydał.",
            "Przed Piłatem",
            "Od Kajfasza zaprowadzili Jezusa do pretorium.",
            "Oto słowo Pańskie.",
        ]
        result = _clean_content_list(content)
        # Rubric lines removed
        for item in result:
            assert "słowa Chrystusa" not in item
            assert "słowa Ewangelisty" not in item
        # Section headers removed
        assert "Pojmanie Jezusa" not in result
        assert "Przed Piłatem" not in result
        # Scripture paragraphs preserved (even those mentioning Judasz)
        assert any("Po wieczerzy" in item for item in result)
        assert any("Judasz" in item for item in result)
        assert any("Kajfasza" in item for item in result)

    def test_passion_header_normalization_nominative(self):
        """Nominative form 'Męka...' is moved to bold-intro slot without conversion."""
        from create_graphic import _normalize_passion_gospel_header
        content_dic = {
            "EWANGELIA": [
                "Łk 22, 14-23, 56",
                "Męka naszego Pana Jezusa Chrystusa według świętego Łukasza",
                "Jezusa postanowiono na śmierć.",
                "Oto słowo Pańskie.",
            ]
        }
        _normalize_passion_gospel_header(content_dic)
        gospel = content_dic["EWANGELIA"]
        assert gospel[1] == "", "subtitle slot should be cleared"
        assert gospel[2] == "Męka naszego Pana Jezusa Chrystusa według świętego Łukasza"
        assert gospel[3] == "Jezusa postanowiono na śmierć."


# ---------------------------------------------------------------------------
# publish() — passion day publishes as single carousel (Instagram limit = 20)
# ---------------------------------------------------------------------------

class TestPublishPassionSplit:

    def _make_reading_files(self, tmp_path, thedate):
        """Create dummy image files for a passion day."""
        post_dir = tmp_path / thedate
        post_dir.mkdir(parents=True)

        files = [
            "cover.jpg",
            "PIERWSZE CZYTANIE.jpg",
            "PSALM RESPONSORYJNY.jpg",
            "DRUGIE CZYTANIE.jpg",
            "EWANGELIA1.jpg",
            "EWANGELIA2.jpg",
            "EWANGELIA3.jpg",
        ]
        for f in files:
            (post_dir / f).write_bytes(b"fake")

        return post_dir

    @patch("create_graphic.WEB_DIR")
    @patch("create_graphic.login_user")
    def test_publishes_single_carousel_on_passion_day(self, mock_login, mock_web_dir, tmp_path):
        from create_graphic import publish
        from PIL import Image

        thedate = "2026-03-29"
        post_dir = self._make_reading_files(tmp_path, thedate)

        img = Image.new("RGB", (100, 100), "white")
        img.save(post_dir / "cover.jpg")

        mock_client = MagicMock()
        mock_client.album_upload.return_value = MagicMock(pk="123")
        mock_login.return_value = mock_client

        with patch("create_graphic.WEB_DIR", tmp_path):
            result = publish(thedate, "Test caption")

        assert mock_client.album_upload.call_count == 1

    @patch("create_graphic.WEB_DIR")
    @patch("create_graphic.login_user")
    def test_passion_carousel_contains_all_files(self, mock_login, mock_web_dir, tmp_path):
        from create_graphic import publish
        from PIL import Image

        thedate = "2026-03-29"
        post_dir = self._make_reading_files(tmp_path, thedate)

        img = Image.new("RGB", (100, 100), "white")
        img.save(post_dir / "cover.jpg")

        mock_client = MagicMock()
        mock_client.album_upload.return_value = MagicMock(pk="123")
        mock_login.return_value = mock_client

        with patch("create_graphic.WEB_DIR", tmp_path):
            publish(thedate, "Test caption")

        paths = mock_client.album_upload.call_args[1]["paths"]
        # All reading files should be in one carousel
        path_names = [p.split("\\")[-1].split("/")[-1] for p in paths]
        assert any("EWANGELIA" in n for n in path_names)
        assert any("PIERWSZE" in n for n in path_names)

    @patch("create_graphic.WEB_DIR")
    @patch("create_graphic.login_user")
    def test_passion_caption_has_no_part_numbers(self, mock_login, mock_web_dir, tmp_path):
        from create_graphic import publish
        from PIL import Image

        thedate = "2026-03-29"
        post_dir = self._make_reading_files(tmp_path, thedate)

        img = Image.new("RGB", (100, 100), "white")
        img.save(post_dir / "cover.jpg")

        mock_client = MagicMock()
        mock_client.album_upload.return_value = MagicMock(pk="123")
        mock_login.return_value = mock_client

        with patch("create_graphic.WEB_DIR", tmp_path):
            publish(thedate, "Test caption")

        caption = mock_client.album_upload.call_args[1]["caption"]
        assert "1/2" not in caption
        assert "2/2" not in caption


# ---------------------------------------------------------------------------
# _normalize_vigil_markers — Gospel year-variant headers
# ---------------------------------------------------------------------------

def _gospel_year_variants_content(roku_a: str, latach_bc: str):
    """Build a content list with two Gospel variants headed by the given markers."""
    return [
        "PIERWSZE CZYTANIE",
        "Dz 11, 1-18",
        "Czytanie z Dziejów Apostolskich",
        "Apostołowie usłyszeli, że poganie przyjęli słowo Boże.",
        "Oto słowo Boże.",
        "PSALM RESPONSORYJNY",
        "Ps 42",
        "Refren: Boga żywego pragnie dusza moja.",
        "Jak łania pragnie wody.",
        "Refren",
        roku_a,
        "J 10, 11-18",
        "Słowa Ewangelii według Świętego Jana",
        "Ja jestem dobrym pasterzem.",
        "Oto słowo Pańskie.",
        latach_bc,
        "J 10, 1-10",
        "Słowa Ewangelii według Świętego Jana",
        "Kto nie wchodzi do owczarni przez bramę.",
        "Oto słowo Pańskie.",
    ]


class TestNormalizeVigilMarkersGospelYearVariants:

    def test_year_b_keeps_latach_bc_variant(self):
        content = _gospel_year_variants_content(
            "EWANGELIA W ROKU A", "EWANGELIA W LATACH B i C"
        )
        result = _normalize_vigil_markers(content, "2027-04-26")  # 2027 % 3 == 2 → B
        assert "EWANGELIA" in result
        assert "EWANGELIA W ROKU A" not in result
        assert "EWANGELIA W LATACH B i C" not in result
        # Year B/C body kept, Year A body dropped
        assert "Kto nie wchodzi do owczarni przez bramę." in result
        assert "Ja jestem dobrym pasterzem." not in result

    def test_year_c_keeps_latach_bc_variant(self):
        content = _gospel_year_variants_content(
            "EWANGELIA W ROKU A", "EWANGELIA W LATACH B i C"
        )
        result = _normalize_vigil_markers(content, "2025-04-21")  # 2025 % 3 == 0 → C
        assert "EWANGELIA" in result
        assert "Kto nie wchodzi do owczarni przez bramę." in result
        assert "Ja jestem dobrym pasterzem." not in result

    def test_year_a_keeps_roku_a_variant(self):
        content = _gospel_year_variants_content(
            "EWANGELIA W ROKU A", "EWANGELIA W LATACH B i C"
        )
        result = _normalize_vigil_markers(content, "2026-04-27")  # 2026 % 3 == 1 → A
        assert "EWANGELIA" in result
        assert "EWANGELIA W ROKU A" not in result
        assert "EWANGELIA W LATACH B i C" not in result
        assert "Ja jestem dobrym pasterzem." in result
        assert "Kto nie wchodzi do owczarni przez bramę." not in result

    def test_three_single_year_variants_year_b(self):
        # Backwards compat: original "EWANGELIA W ROKU X" three-way still works.
        content = [
            "PIERWSZE CZYTANIE", "Iz 1, 1", "Czytanie", "Treść.", "Oto słowo Boże.",
            "PSALM RESPONSORYJNY", "Ps 1", "Refren: test.", "Werset.",
            "EWANGELIA W ROKU A", "Mt 1, 1", "Słowa", "Tekst A.", "Oto słowo Pańskie.",
            "EWANGELIA W ROKU B", "Mk 1, 1", "Słowa", "Tekst B.", "Oto słowo Pańskie.",
            "EWANGELIA W ROKU C", "Łk 1, 1", "Słowa", "Tekst C.", "Oto słowo Pańskie.",
        ]
        result = _normalize_vigil_markers(content, "2027-04-26")  # B
        assert "EWANGELIA" in result
        assert "EWANGELIA W ROKU A" not in result
        assert "EWANGELIA W ROKU B" not in result
        assert "EWANGELIA W ROKU C" not in result
        assert "Tekst B." in result
        assert "Tekst A." not in result
        assert "Tekst C." not in result

    def test_no_gospel_variants_passes_through(self):
        # Ordinary day: a single plain "EWANGELIA" header — nothing to rewrite.
        content = [
            "PIERWSZE CZYTANIE", "Iz 1, 1", "Czytanie", "Treść.", "Oto słowo Boże.",
            "PSALM RESPONSORYJNY", "Ps 1", "Refren: test.", "Werset.",
            "EWANGELIA", "J 1, 1", "Słowa", "Treść.", "Oto słowo Pańskie.",
        ]
        result = _normalize_vigil_markers(content, "2026-04-27")
        assert result.count("EWANGELIA") == 1
        assert "Treść." in result

    def test_full_pipeline_yields_ewangelia_key_for_2026_04_27(self):
        # End-to-end through normalize → clean → normalize_readings → parse:
        # the Gospel must end up in the readings dict for 2026-04-27 (Year A).
        from create_graphic import _clean_content_list

        content = _gospel_year_variants_content(
            "EWANGELIA W ROKU A", "EWANGELIA W LATACH B i C"
        )
        normalized = _normalize_vigil_markers(content, "2026-04-27")
        cleaned = _clean_content_list(normalized)
        normalized2 = _normalize_readings(cleaned)
        parsed = _parse_readings(normalized2)
        assert "EWANGELIA" in parsed
        assert "PIERWSZE CZYTANIE" in parsed
        assert "PSALM RESPONSORYJNY" in parsed
