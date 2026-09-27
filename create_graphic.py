"""
Main content processor for Cyber Bible.
Handles scraping liturgical readings, generating images, and publishing to Instagram.
"""

import itertools
import logging
import math
import os
import re
from functools import reduce
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import eel
import requests
from bs4 import BeautifulSoup
from PIL import Image

from config import (
    BACKGROUND_IMAGE,
    IMAGE_SIZE,
    FONT_SIZE_DEFAULT,
    FONT_SIZE_MAX,
    FONT_SIZE_PSALM,
    FONT_SIZE_MIN,
    WEB_DIR,
    LITURGY_URL_PL,
    LITURGY_URL_EN,
    DEFAULT_HASHTAGS,
    MAX_CAROUSEL_IMAGES,
    EASTER_VIGIL_OT_READING_INDICES,
    PASSION_SPLIT_THRESHOLD,
)
from draw_posts import (
    draw_text,
    draw_text_pagination_first,
    draw_text_pagination_middle,
    draw_text_pagination_second,
    draw_psalm,
)
from login import login_user
from midjourney_wrapper import MidjourneyWrapper
from prompt_generator import generate_midjourney_prompt, generate_prompt_variations

logger = logging.getLogger(__name__)

# Polish to English Bible book name mapping
POLISH_TO_ENGLISH_BOOKS = {
    # Old Testament
    "Rdz": "Genesis", "Wj": "Exodus", "Kpł": "Leviticus", "Lb": "Numbers",
    "Pwt": "Deuteronomy", "Joz": "Joshua", "Sdz": "Judges", "Rt": "Ruth",
    "1 Sm": "1 Samuel", "2 Sm": "2 Samuel", "1 Krl": "1 Kings", "2 Krl": "2 Kings",
    "1 Krn": "1 Chronicles", "2 Krn": "2 Chronicles", "Ezd": "Ezra", "Ne": "Nehemiah",
    "Tb": "Tobit", "Jdt": "Judith", "Est": "Esther", "1 Mch": "1 Maccabees",
    "2 Mch": "2 Maccabees", "Hi": "Job", "Ps": "Psalms", "Prz": "Proverbs",
    "Koh": "Ecclesiastes", "Pnp": "Song of Solomon", "Mdr": "Wisdom", "Syr": "Sirach",
    "Iz": "Isaiah", "Jr": "Jeremiah", "Lm": "Lamentations", "Ba": "Baruch",
    "Ez": "Ezekiel", "Dn": "Daniel", "Oz": "Hosea", "Jl": "Joel", "Am": "Amos",
    "Ab": "Obadiah", "Jon": "Jonah", "Mi": "Micah", "Na": "Nahum", "Ha": "Habakkuk",
    "So": "Zephaniah", "Ag": "Haggai", "Za": "Zechariah", "Ml": "Malachi",
    # New Testament
    "Mt": "Matthew", "Mk": "Mark", "Łk": "Luke", "J": "John",
    "Dz": "Acts", "Rz": "Romans", "1 Kor": "1 Corinthians", "2 Kor": "2 Corinthians",
    "Ga": "Galatians", "Ef": "Ephesians", "Flp": "Philippians", "Kol": "Colossians",
    "1 Tes": "1 Thessalonians", "2 Tes": "2 Thessalonians", "1 Tm": "1 Timothy",
    "2 Tm": "2 Timothy", "Tt": "Titus", "Flm": "Philemon", "Hbr": "Hebrews",
    "Jk": "James", "1 P": "1 Peter", "2 P": "2 Peter", "1 J": "1 John",
    "2 J": "2 John", "3 J": "3 John", "Jud": "Jude", "Ap": "Revelation",
}


def _create_background() -> Image.Image:
    """Create tiled background image from paper texture."""
    if not BACKGROUND_IMAGE.exists():
        logger.warning(f"Background image not found: {BACKGROUND_IMAGE}")
        return Image.new("RGB", (IMAGE_SIZE, IMAGE_SIZE), "white")

    with Image.open(BACKGROUND_IMAGE) as texture:
        background = Image.new("RGB", (IMAGE_SIZE, IMAGE_SIZE), "white")
        tex_width, tex_height = texture.size

        x = 0
        while x < IMAGE_SIZE:
            y = 0
            while y < IMAGE_SIZE:
                background.paste(texture, (x, y))
                y += tex_height
            x += tex_width

    return background


def _get_liturgical_year(date_str: str) -> str:
    """Determine liturgical year (A, B, or C) from date string.

    Sunday cycle: Year A=2023/2026/2029, Year B=2024/2027/2030, Year C=2025/2028/2031,
    i.e. year % 3 maps 1→A, 2→B, 0→C.
    """
    year = int(date_str[:4])
    return {0: "C", 1: "A", 2: "B"}[year % 3]


# Matches Gospel year-variant headers: "EWANGELIA W ROKU B" or "EWANGELIA W LATACH B i C".
_GOSPEL_VARIANT_RE = re.compile(
    r"^EWANGELIA W (?:ROKU|LATACH)\s+([ABC](?:\s*(?:,|i)\s*[ABC])*)\s*$"
)


def _scrape_content_list(thedate: str) -> List[str]:
    """Fetch raw content list for a given date, handling paginated vigil pages."""
    url = f"{LITURGY_URL_PL}/{thedate}"
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.content, "html.parser")
    content_areas = soup.find_all("div", "txt__rich-area")

    if len(content_areas) < 2:
        raise ValueError("Could not find reading content on page")

    # Check for vigil pagination (content_index div with sub-page links)
    idx_div = soup.find("div", "content_index")
    if idx_div:
        links = idx_div.find_all("a", href=True)
        page_nums = set()
        for a in links:
            # Skip old lectionary link
            if "STAREGO" in a.get_text().upper():
                continue
            match = re.search(r"/(\d+)#", a["href"])
            if match:
                page_nums.add(int(match.group(1)))

        if len(page_nums) > 1:
            logger.info(f"Vigil pagination detected: {len(page_nums)} sub-pages")
            combined: List[str] = []
            for page_num in sorted(page_nums):
                page_url = f"{LITURGY_URL_PL}/{thedate}/{page_num}"
                page_resp = requests.get(page_url, timeout=30)
                page_resp.raise_for_status()
                page_soup = BeautifulSoup(page_resp.content, "html.parser")
                page_areas = page_soup.find_all("div", "txt__rich-area")
                if len(page_areas) >= 2:
                    area = page_areas[1]
                    # Remove content_index TOC to avoid duplicate markers
                    for ci in area.find_all("div", "content_index"):
                        ci.decompose()
                    combined.extend(area.get_text().split("\n"))
            return combined

    return content_areas[1].get_text().split("\n")


def _normalize_vigil_markers(content_list: List[str], thedate: str) -> List[str]:
    """Normalize vigil-specific markers and content before standard processing."""
    result = content_list.copy()
    liturgical_year = _get_liturgical_year(thedate)

    # Remove noise lines (embedded video/social references)
    result = [
        line for line in result
        if line.strip() != "Maskacjusz TV"
        and not line.strip().startswith("#")
        and line.strip() != "Nie mówi się: Oto słowo Boże."
    ]

    # Uppercase variant suffixes so _normalize_readings can handle them
    variant_replacements = [
        ("PIERWSZE CZYTANIE dłuższe", "PIERWSZE CZYTANIE DŁUŻSZE"),
        ("PIERWSZE CZYTANIE krótsze", "PIERWSZE CZYTANIE KRÓTSZE"),
        ("DRUGIE CZYTANIE dłuższe", "DRUGIE CZYTANIE DŁUŻSZE"),
        ("DRUGIE CZYTANIE krótsze", "DRUGIE CZYTANIE KRÓTSZE"),
    ]
    for old, new in variant_replacements:
        for i, text in enumerate(result):
            if text.strip() == old:
                result[i] = new

    # Normalize epistle marker
    for i, text in enumerate(result):
        if "ÓSME CZYTANIE" in text and "EPISTOŁA" in text.upper():
            result[i] = "ÓSME CZYTANIE"

    # Select correct Gospel year variant, remove others.
    # Markers come in two shapes:
    #   "EWANGELIA W ROKU X"        (single year)
    #   "EWANGELIA W LATACH X i Y"  (two years; rarer: "X, Y i Z")
    # Find every variant header, parse the set of years it covers, keep the
    # one that includes the current liturgical_year, drop the rest.
    variants = []
    for i, text in enumerate(result):
        m = _GOSPEL_VARIANT_RE.match(text.strip())
        if m:
            years = set(re.findall(r"[ABC]", m.group(1)))
            variants.append((i, years))

    keep_idx = next((i for i, ys in variants if liturgical_year in ys), None)
    if keep_idx is not None:
        result[keep_idx] = "EWANGELIA"

    # Delete other variants' sections (reverse order so earlier indices stay valid)
    for i, _ys in sorted(variants, key=lambda v: v[0], reverse=True):
        if i == keep_idx:
            continue
        end = i + 1
        for j in range(i + 1, len(result)):
            line = result[j].strip()
            if line == "Oto słowo Pańskie.":
                end = j + 1
                break
            if line == "EWANGELIA" or _GOSPEL_VARIANT_RE.match(line):
                end = j
                break
        del result[i:end]

    return result


def _clean_content_list(content_list: List[str]) -> List[str]:
    """Clean and normalize the scraped content list."""
    # Remove empty trailing elements
    while content_list and content_list[-1] == "":
        content_list.pop()

    cleaned = []
    for text in content_list:
        # Skip liturgy headers and empty strings
        if "Liturgia Słowa" in text or text == "":
            continue

        # Skip passion-specific content (section headers / rubrics, not scripture)
        # Substring matches — phrases specific enough to never appear in scripture
        skip_phrases = [
            "Jezus przed Piłatem",
            "Droga krzyżowa",
            "Wszyscy klękają i przez chwilę zachowują milczenie.",
            # Palm Sunday (Mt 26/27) section headers
            "Jezus odrzucony przez swój naród",
            "Król wyszydzony",
            "Wyszydzenie na krzyżu",
            "Śmierć Jezusa",
            "Ukrzyżowanie Jezusa",
            "Pojmanie Jezusa",
            "Jezus przed Sanhedrynem",
            "Zaparcie się Piotra",
            "Jezus przed Annaszem",
            "Jezus wydany na śmierć",
            "Przebicie boku Jezusa",
            # Passion Gospel rubric / legend lines (speaker marker explanations)
            "słowa Chrystusa",
            "słowa Ewangelisty",
            "słowa innych osób pojedynczych",
            "słowa kilku osób lub tłumu",
        ]
        # Exact-match headers — short names that could appear in scripture text
        skip_headers_exact = {
            "Judasz",
            "Ukrzyżowanie",
            "Złożenie do grobu",
            # Good Friday (J 18/19) section headers
            "Przed Piłatem",
            "Przesłuchanie",
            "\u201eOto człowiek\u201d",
            "Wyrok",
            "Testament dany z krzyża",
            "Przebicie serca",
            "Złożenie Jezusa do grobu",
            "Droga krzyżowa i ukrzyżowanie",
            "Przed Annaszem. Zaparcie się Piotra",
        }
        if text.strip() in skip_headers_exact:
            continue
        if any(phrase in text for phrase in skip_phrases):
            continue

        # Strip whitespace
        cleaned.append(text.strip())

    return cleaned


def _normalize_readings(content_list: List[str]) -> List[str]:
    """Normalize reading names and handle shorter/longer versions."""
    result = content_list.copy()

    # Handle longer/shorter Gospel versions FIRST - prefer shorter, preserve subtitle
    # Must run before replacements that change marker names
    try:
        if "EWANGELIA DŁUŻSZA" in result and "EWANGELIA KRÓTSZA" in result:
            # Find longer Gospel section boundaries
            longer_idx = result.index("EWANGELIA DŁUŻSZA")
            longer_end = result.index("Oto słowo Pańskie.", longer_idx) + 1

            # Extract subtitle from longer version
            # Structure: marker → reference → [subtitle] → "Słowa Ewangelii..."
            longer_subtitle = None
            for i in range(longer_idx + 2, min(longer_idx + 4, longer_end)):
                line = result[i].strip()
                if line.startswith("Słowa Ewangelii"):
                    break  # No subtitle found
                if line:
                    longer_subtitle = line
                    break

            # Find shorter Gospel section
            shorter_idx = result.index("EWANGELIA KRÓTSZA")

            # Check if shorter version is missing subtitle
            # (line after reference immediately starts with "Słowa Ewangelii...")
            shorter_needs_subtitle = False
            for i in range(shorter_idx + 2, min(shorter_idx + 4, len(result))):
                line = result[i].strip()
                if line.startswith("Słowa Ewangelii"):
                    shorter_needs_subtitle = True
                    break
                if line:
                    break  # Has subtitle already

            # Insert subtitle into shorter version if missing
            if longer_subtitle and shorter_needs_subtitle:
                for i in range(shorter_idx + 1, len(result)):
                    if result[i].startswith("Słowa Ewangelii"):
                        result.insert(i, longer_subtitle)
                        logger.debug(f"Copied subtitle '{longer_subtitle}' to shorter Gospel")
                        break

            # Remove entire longer Gospel section
            del result[longer_idx:longer_end]
            logger.debug(f"Removed longer Gospel (lines {longer_idx}-{longer_end})")
    except ValueError:
        pass

    # Handle longer/shorter First Reading versions - prefer shorter, preserve subtitle
    # Must run before replacements that change marker names
    try:
        if "PIERWSZE CZYTANIE DŁUŻSZE" in result and "PIERWSZE CZYTANIE KRÓTSZE" in result:
            # Find longer First Reading section boundaries
            longer_idx = result.index("PIERWSZE CZYTANIE DŁUŻSZE")
            longer_end = result.index("Oto słowo Boże.", longer_idx) + 1

            # Extract subtitle from longer version
            # Structure: marker → reference → [subtitle] → "Czytanie z Księgi..."
            longer_subtitle = None
            for i in range(longer_idx + 2, min(longer_idx + 5, longer_end)):
                line = result[i].strip()
                if line.startswith("Czytanie z"):
                    break  # No subtitle found
                if line:
                    longer_subtitle = line
                    break

            # Find shorter First Reading section
            shorter_idx = result.index("PIERWSZE CZYTANIE KRÓTSZE")
            shorter_end = result.index("Oto słowo Boże.", shorter_idx) + 1

            # Check if shorter version is missing subtitle
            shorter_needs_subtitle = False
            for i in range(shorter_idx + 2, min(shorter_idx + 5, shorter_end)):
                line = result[i].strip()
                if line.startswith("Czytanie z"):
                    shorter_needs_subtitle = True
                    break
                if line:
                    break  # Has subtitle already

            # Insert subtitle into shorter version if missing
            if longer_subtitle and shorter_needs_subtitle:
                for i in range(shorter_idx + 1, shorter_end):
                    if result[i].startswith("Czytanie z"):
                        result.insert(i, longer_subtitle)
                        logger.debug(f"Copied subtitle '{longer_subtitle}' to shorter First Reading")
                        break

            # Remove entire longer First Reading section
            del result[longer_idx:longer_end]
            logger.debug(f"Removed longer First Reading (lines {longer_idx}-{longer_end})")
    except ValueError:
        pass

    # Handle combined longer/shorter Second Reading format - prefer shorter.
    # Same stacked-header shape as the combined Gospel above, on Sundays that
    # offer both pericopes in one body:
    #   DRUGIE CZYTANIE DŁUŻSZE / <longer ref> / KRÓTSZE / <shorter ref> /
    #   [subtitle] / Czytanie z... / text... / Koniec krótszej perykopy. /
    #   text... / Oto słowo Boże.
    # Without this the marker never matches a cut point and the whole reading
    # is swallowed by the preceding psalm.
    try:
        if "DRUGIE CZYTANIE DŁUŻSZE" in result and "DRUGIE CZYTANIE KRÓTSZE" not in result:
            longer_idx = result.index("DRUGIE CZYTANIE DŁUŻSZE")
            krotsza_idx = result.index("KRÓTSZE", longer_idx)
            reading_end = result.index("Oto słowo Boże.", krotsza_idx)
            if krotsza_idx - longer_idx <= 3:
                shorter_ref = result[krotsza_idx + 1]
                try:
                    # Cut at the inline shorter-pericope end marker
                    body_end = result.index("Koniec krótszej perykopy.", krotsza_idx)
                    rebuilt = (
                        ["DRUGIE CZYTANIE", shorter_ref]
                        + result[krotsza_idx + 2:body_end]
                        + ["Oto słowo Boże."]
                    )
                except ValueError:
                    # No inline marker — fall back to the full (longer) text
                    rebuilt = (
                        ["DRUGIE CZYTANIE", result[longer_idx + 1]]
                        + result[krotsza_idx + 2:reading_end]
                        + ["Oto słowo Boże."]
                    )
                result[longer_idx:reading_end + 1] = rebuilt
                logger.debug("Collapsed combined longer/shorter Second Reading header")
    except ValueError:
        pass

    # Handle longer/shorter Second Reading versions (Easter Vigil) - prefer shorter
    try:
        if "DRUGIE CZYTANIE DŁUŻSZE" in result and "DRUGIE CZYTANIE KRÓTSZE" in result:
            longer_idx = result.index("DRUGIE CZYTANIE DŁUŻSZE")
            longer_end = result.index("Oto słowo Boże.", longer_idx) + 1
            del result[longer_idx:longer_end]
            logger.debug(f"Removed longer Second Reading (lines {longer_idx}-{longer_end})")
    except ValueError:
        pass

    # Replacements for shorter versions
    replacements = [
        ("PIERWSZE CZYTANIE KRÓTSZE", "PIERWSZE CZYTANIE"),
        ("DRUGIE CZYTANIE KRÓTSZE", "DRUGIE CZYTANIE"),
        ("EWANGELIA KRÓTSZA", "EWANGELIA"),
        (".PSALM RESPONSORYJNY", "PSALM RESPONSORYJNY"),
        ("PSALM RESPONSORYJNY ", "PSALM RESPONSORYJNY"),
        ("EWANGELIA DŁUŻSZA ", "EWANGELIA DŁUŻSZA"),
        ("EWANGELIA ", "EWANGELIA"),
    ]

    for old, new in replacements:
        for i, text in enumerate(result):
            if old in text:
                result[i] = text.replace(old, new)
                logger.debug(f"Replaced '{old}' with '{new}'")

    # Fallback: Handle shorter first reading without longer version
    try:
        if "PIERWSZE CZYTANIE KRÓTSZE" in result:
            start = result.index("PIERWSZE CZYTANIE KRÓTSZE")
            end = result.index("Oto słowo Boże.", start) + 1
            result = result[start:end]
            result[0] = result[0].replace("PIERWSZE CZYTANIE KRÓTSZE", "PIERWSZE CZYTANIE")
    except ValueError:
        pass

    # Drop malformed "lub" alternative First Reading variant.
    # Optional-memorial pages on liturgia.wiara.pl sometimes list two first-reading
    # options separated by "lub". Occasionally the first variant omits the
    # "Czytanie z..." intro line, which would land scripture text in the bold-intro
    # slot when rendered. When that happens, drop the malformed variant so the
    # second (well-formed) variant is used instead.
    try:
        first_idx = result.index("PIERWSZE CZYTANIE")
        lub_idx = next(
            (i for i in range(first_idx + 1, len(result)) if result[i].strip() == "lub"),
            None,
        )
        if lub_idx is not None:
            second_idx = result.index("PIERWSZE CZYTANIE", lub_idx)
            first_has_intro = any(
                line.strip().startswith("Czytanie z")
                for line in result[first_idx + 1:lub_idx]
            )
            if not first_has_intro:
                del result[first_idx:lub_idx + 1]
                logger.debug("Dropped first-reading variant lacking 'Czytanie z' intro")
    except ValueError:
        pass

    # Remove processional Gospel (Palm Sunday - not part of Liturgia Słowa)
    try:
        proc_start = result.index("PROCESJA Z PALMAMI")
        proc_end = result.index("PIERWSZE CZYTANIE", proc_start)
        del result[proc_start:proc_end]
    except ValueError:
        pass

    # Handle alternative readings
    try:
        alt_idx = result.index("albo do wyboru:")
        gospel_idx = result.index("EWANGELIA", alt_idx)
        del result[alt_idx:gospel_idx]
    except ValueError:
        pass

    try:
        alt_idx = result.index("albo:")
        psalm_idx = result.index("PSALM RESPONSORYJNY", alt_idx)
        del result[alt_idx:psalm_idx]
    except ValueError:
        pass

    # Remove optional sequence note (appears before SEKWENCJA marker, not part of content)
    try:
        result.remove("Można odmawiać sekwencję: Niech w święto radosne Paschalnej Ofiary.")
    except ValueError:
        pass

    return result


def _parse_readings(content_list: List[str]) -> Dict[str, List[str]]:
    """Parse content list into dictionary of readings."""
    # Determine cut points based on available readings
    has_sekwencja = "SEKWENCJA" in content_list
    if "EWANGELIA KRÓTSZA" in content_list:
        cut_points = ["PIERWSZE CZYTANIE", "PSALM RESPONSORYJNY", "DRUGIE CZYTANIE", "EWANGELIA KRÓTSZA"]
    elif "DRUGIE CZYTANIE" in content_list and has_sekwencja:
        cut_points = ["PIERWSZE CZYTANIE", "PSALM RESPONSORYJNY", "DRUGIE CZYTANIE", "SEKWENCJA", "EWANGELIA"]
    elif "DRUGIE CZYTANIE" in content_list:
        cut_points = ["PIERWSZE CZYTANIE", "PSALM RESPONSORYJNY", "DRUGIE CZYTANIE", "EWANGELIA"]
    else:
        cut_points = ["PIERWSZE CZYTANIE", "PSALM RESPONSORYJNY", "EWANGELIA"]

    content_dic = {}
    staging_list = []

    for text in content_list:
        if text in cut_points:
            # Start collecting content for this reading
            idx = content_list.index(text)
            for item in content_list[idx + 1 :]:
                if item == "":
                    continue
                if item == "albo:":
                    if cut_points:
                        content_dic[cut_points[0]] = staging_list
                        staging_list = []
                        del cut_points[0]
                    break
                if item not in cut_points:
                    staging_list.append(item)
                else:
                    if cut_points:
                        content_dic[cut_points[0]] = staging_list
                        staging_list = []
                        del cut_points[0]
                    break

            if cut_points:
                content_dic[cut_points[0]] = staging_list

    return content_dic


def _parse_vigil_readings(content_list: List[str]) -> Dict[str, List[str]]:
    """Parse Easter Vigil readings with all 7 OT readings + Epistle + Gospel."""
    all_markers = [
        "PIERWSZE CZYTANIE",
        "1 PSALM RESPONSORYJNY",
        "DRUGIE CZYTANIE",
        "2 PSALM RESPONSORYJNY",
        "TRZECIE CZYTANIE",
        "3 PSALM RESPONSORYJNY",
        "CZWARTE CZYTANIE",
        "4 PSALM RESPONSORYJNY",
        "PIĄTE CZYTANIE",
        "5 PSALM RESPONSORYJNY",
        "SZÓSTE CZYTANIE",
        "6 PSALM RESPONSORYJNY",
        "SIÓDME CZYTANIE",
        "7 PSALM RESPONSORYJNY",
        "ÓSME CZYTANIE",
        "8 PSALM RESPONSORYJNY",
        "PSALM RESPONSORYJNY",  # fallback if Epistle psalm is unnumbered
        "EWANGELIA",
    ]

    # Find present markers sorted by their position in content_list
    marker_positions = []
    seen = set()
    for marker in all_markers:
        if marker in seen:
            continue
        try:
            pos = content_list.index(marker)
            marker_positions.append((pos, marker))
            seen.add(marker)
        except ValueError:
            pass
    marker_positions.sort()

    content_dic = {}
    for i, (pos, marker) in enumerate(marker_positions):
        end_pos = marker_positions[i + 1][0] if i + 1 < len(marker_positions) else len(content_list)
        content_dic[marker] = [item for item in content_list[pos + 1:end_pos] if item.strip()]

    return content_dic


def _filter_easter_vigil(content_dic: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """Keep only selected OT readings + Epistle + Gospel from Easter Vigil."""
    ot_reading_keys = [
        "PIERWSZE CZYTANIE", "DRUGIE CZYTANIE", "TRZECIE CZYTANIE",
        "CZWARTE CZYTANIE", "PIĄTE CZYTANIE", "SZÓSTE CZYTANIE", "SIÓDME CZYTANIE",
    ]

    result: Dict[str, List[str]] = {}

    for idx in EASTER_VIGIL_OT_READING_INDICES:
        if idx >= len(ot_reading_keys):
            continue
        reading_key = ot_reading_keys[idx]
        psalm_key = f"{idx + 1} PSALM RESPONSORYJNY"

        if reading_key in content_dic:
            result[reading_key] = content_dic[reading_key]
        if psalm_key in content_dic:
            result[psalm_key] = content_dic[psalm_key]

    # Always include Epistle and its psalm
    if "ÓSME CZYTANIE" in content_dic:
        result["ÓSME CZYTANIE"] = content_dic["ÓSME CZYTANIE"]
    for epistle_psalm in ("8 PSALM RESPONSORYJNY", "PSALM RESPONSORYJNY"):
        if epistle_psalm in content_dic:
            result[epistle_psalm] = content_dic[epistle_psalm]
            break

    # Always include Gospel
    if "EWANGELIA" in content_dic:
        result["EWANGELIA"] = content_dic["EWANGELIA"]

    return result


_ALT_REFRAIN_RE = re.compile(r"^\d+\.\s+(.+)$")


def _collapse_alternative_refrains(psalm: List[str]) -> None:
    """
    Some days liturgia.wiara.pl offers multiple alternative refrains as numbered lines
    directly under a bare ``Refren:`` marker, e.g.::

        Refren:
        1. Kościół nie zginie, Bóg jest w jego wnętrzu.
        2. Tyś wielką chlubą Kościoła świętego.

        [stanzas...]

    The parser leaves ``psalm[1] == 'Refren:'`` (empty refrain text) and the numbered
    alternatives bleed into the stanza area. Pick the first alternative as the refrain
    text and drop the rest so the rendered image shows a real refrain and clean stanzas.
    """
    if len(psalm) < 3:
        return
    if psalm[1].strip().rstrip(":").strip() != "Refren":
        return
    match = _ALT_REFRAIN_RE.match(psalm[2].strip())
    if not match:
        return
    psalm[1] = f"Refren: {match.group(1)}"
    end = 3
    while end < len(psalm) and _ALT_REFRAIN_RE.match(psalm[end].strip()):
        end += 1
    del psalm[2:end]


def _add_psalm_refrains(content_dic: Dict[str, List[str]]) -> None:
    """Add refrain markers to psalm(s) if missing. Handles both regular and numbered vigil psalms."""
    psalm_keys = ["PSALM RESPONSORYJNY"] + [f"{i} PSALM RESPONSORYJNY" for i in range(1, 9)]

    for psalm_key in psalm_keys:
        if psalm_key not in content_dic:
            continue
        psalm = content_dic[psalm_key]
        _collapse_alternative_refrains(psalm)
        refrain_count = reduce(lambda x, y: x + 1 if "Refren" in y else x, psalm, 0)
        if len(psalm) > 6 and refrain_count == 1:
            for pos in [16, 11, 6]:
                if pos < len(psalm):
                    psalm.insert(pos, "Refren")


def _normalize_passion_gospel_header(content_dic: Dict[str, List[str]]) -> None:
    """
    For Passion Gospels the scraped subtitle contains 'naszego Pana' (unique to the
    Passion title).  Normalise to nominative 'Męka' (converting accusative 'Mękę' if
    needed), move the title to the bold-intro slot (index 2), and clear the subtitle
    slot (index 1).  Safe no-op for all non-Passion readings.
    """
    gospel = content_dic.get("EWANGELIA", [])
    if len(gospel) < 2:
        return
    subtitle = gospel[1]
    if "naszego Pana" in subtitle:
        passion_title = subtitle.replace("Mękę", "Męka", 1)
        content_dic["EWANGELIA"] = [gospel[0], ""] + [passion_title] + gospel[2:]


def _ensure_gospel_subtitle_slot(content_dic: Dict[str, List[str]]) -> None:
    """
    Some Gospel readings lack a thematic subtitle — the formula
    'Słowa Ewangelii...' sits directly at index 1 instead of index 2.
    Insert an empty subtitle so the structure is always:
      [0] reference, [1] subtitle (may be empty), [2] bold intro formula, ...
    """
    gospel = content_dic.get("EWANGELIA", [])
    if len(gospel) < 2:
        return
    if gospel[1].startswith("Słowa Ewangelii"):
        content_dic["EWANGELIA"] = [gospel[0], ""] + gospel[1:]


def _split_long_paragraphs(content_dic: Dict[str, List[str]], max_chars: int = 350) -> None:
    """
    Split body paragraphs longer than max_chars at sentence boundaries.

    The paginator only breaks BETWEEN paragraphs — a single paragraph that
    exceeds what fits at FONT_SIZE_MIN overflows the image because the fallback
    even-split can't divide one paragraph in half. Applies to every reading
    (Gospel and the CZYTANIA), since long Pauline/Acts passages (e.g. Paul's
    Areopagus speech) hit the same problem the Passion Gospel does.
    """
    # Sentence boundary: period/exclamation/question followed by space + uppercase or quote
    sentence_end = re.compile(r'(?<=[.!?])\s+(?=[A-ZŁŚŻŹĆĄĘÓŃ«"\u201c\u201e])')

    for key, reading in list(content_dic.items()):
        if "CZYTANIE" not in key and key not in ("EWANGELIA", "EWANGELIA KRÓTSZA"):
            continue
        if len(reading) < 4:
            continue

        new_body: List[str] = []
        for para in reading[3:-1]:
            if len(para) <= max_chars:
                new_body.append(para)
                continue
            # Split at sentence boundaries, keeping chunks under max_chars
            sentences = sentence_end.split(para)
            chunk = ""
            for sent in sentences:
                candidate = (chunk + " " + sent).strip() if chunk else sent
                if len(candidate) <= max_chars:
                    chunk = candidate
                else:
                    if chunk:
                        new_body.append(chunk)
                    chunk = sent
            if chunk:
                new_body.append(chunk)

        content_dic[key] = reading[:3] + new_body + reading[-1:]


def _normalize_sekwencja_content(content_dic: Dict[str, List[str]]) -> None:
    """Wrap SEKWENCJA content into standard reading structure for draw_text()."""
    if "SEKWENCJA" not in content_dic:
        return

    lines = content_dic["SEKWENCJA"]

    # Strip any ŚPIEW PRZED EWANGELIĄ that may have been collected after the sequence
    try:
        spiew_idx = lines.index("ŚPIEW PRZED EWANGELIĄ")
        lines = lines[:spiew_idx]
    except ValueError:
        pass

    # Remove empty lines
    lines = [l for l in lines if l.strip()]

    if not lines:
        del content_dic["SEKWENCJA"]
        return

    # Ensure closing phrase is at the end
    closing = "Amen. Alleluja."
    if closing in lines:
        lines.remove(closing)
    lines.append(closing)

    # Wrap to standard reading structure: [reference, subtitle, intro_bold, body..., closing]
    # [0]=empty ref, [1]=empty subtitle, [2]=first poem line (bold), [3:-1]=rest, [-1]=closing
    content_dic["SEKWENCJA"] = ["", ""] + lines


def _truncate_readings(content_dic: Dict[str, List[str]]) -> None:
    """Truncate readings at their closing phrases."""
    gospel_endings = {"EWANGELIA", "EWANGELIA KRÓTSZA"}

    for key, content in list(content_dic.items()):
        if key in gospel_endings:
            try:
                end_idx = content.index("Oto słowo Pańskie.") + 1
                content_dic[key] = content[:end_idx]
            except ValueError:
                pass
        elif "CZYTANIE" in key:
            # Handles PIERWSZE, DRUGIE, and all vigil readings (TRZECIE…ÓSME)
            for ending in ("Oto słowo Boże.", "Oto słowo Boże"):
                try:
                    end_idx = content.index(ending) + 1
                    content_dic[key] = content[:end_idx]
                    break
                except ValueError:
                    pass


def _clean_gospel_markers(content_dic: Dict[str, List[str]]) -> None:
    """Remove speaker markers from Gospel text (for dramatic readings)."""
    gospel_keys = ["EWANGELIA", "EWANGELIA KRÓTSZA"]

    for key in gospel_keys:
        if key not in content_dic:
            continue

        markers = ["I.", "T.", "E.", "+"]
        content_dic[key] = [
            reduce(lambda text, marker: text.replace(marker, ""), markers, item)
            for item in content_dic[key]
        ]


def _remove_pre_gospel_from_reading(content_dic: Dict[str, List[str]]) -> None:
    """Remove pre-Gospel acclamation from second reading if present."""
    if "DRUGIE CZYTANIE" not in content_dic:
        return

    reading = content_dic["DRUGIE CZYTANIE"]
    if "ŚPIEW PRZED EWANGELIĄ" in reading:
        content_dic["DRUGIE CZYTANIE"] = reading[:-6]


def _remove_liturgical_notes(content_dic: Dict[str, List[str]]) -> None:
    """Remove liturgical year notes like 'W roku C...' from Gospel."""
    if "EWANGELIA" not in content_dic:
        return

    content_dic["EWANGELIA"] = [
        line for line in content_dic["EWANGELIA"]
        if not line.strip().startswith("W roku")
    ]


def _generate_reading_images(
    content_dic: Dict[str, List[str]],
    background: Image.Image,
    output_path: Path,
    verse_break: int,
    passion_mode: bool = False,
) -> List[str]:
    """Generate images for all readings with smart auto-pagination."""
    posts_list = []

    for reading_name in content_dic.keys():
        if "PSALM" in reading_name or reading_name == "ŚPIEW PRZED EWANGELIĄ":
            continue

        reading_content = content_dic[reading_name]
        font_size = FONT_SIZE_DEFAULT

        # Passion Gospels get extended page limit; regular Gospels use standard limit
        if passion_mode and reading_name == "EWANGELIA":
            pages_limit = MAX_PAGES_GOSPEL
        else:
            pages_limit = MAX_PAGES_PER_READING

        # Calculate optimal pagination
        # Passion mode: prefer larger font (more readable) over fewer pages
        prefer_readability = passion_mode and reading_name == "EWANGELIA"
        num_pages, optimal_font, pages = _calculate_optimal_pagination(
            reading_content, font_size, reading_name=reading_name, max_pages=pages_limit,
            prefer_readability=prefer_readability,
        )

        logger.info(f"{reading_name}: {num_pages} page(s), font size {optimal_font}")

        if num_pages == 1:
            # Single page - use optimal font calculated by pagination
            result = draw_text(content_dic, background, reading_name, optimal_font)

            # The estimator can be optimistic (it counts characters via textwrap,
            # not real glyph widths). Verify the rendered text actually fits and
            # shrink the font if the closing line would clip the bottom edge.
            while not _text_fits(result["drawn_y"], optimal_font) and optimal_font > FONT_SIZE_MIN:
                optimal_font -= 1
                result = draw_text(content_dic, background, reading_name, optimal_font)

            if not _text_fits(result["drawn_y"], optimal_font):
                logger.warning(
                    f"{reading_name}: text overflows at min font {optimal_font} "
                    f"(drawn_y={result['drawn_y']})"
                )

            logger.info(f"  {reading_name} final font: {optimal_font}")
            result["picture"].save(output_path / f"{reading_name}.jpg")
            posts_list.append(f"{reading_name}.jpg")

        else:
            # Multi-page - render each page with optimal font
            rendered_pages = _render_smart_pages(
                background, reading_name, pages, optimal_font
            )

            for i, img_result in enumerate(rendered_pages):
                filename = f"{reading_name}{i + 1}.jpg"
                img_result["picture"].save(output_path / filename)
                posts_list.append(filename)

    return posts_list


def _render_smart_pages(
    background: Image.Image,
    reading_name: str,
    pages: List[List[str]],
    font_size: int
) -> List[dict]:
    """
    Render multiple pages with consistent font size.

    Args:
        background: Background image
        reading_name: Name of the reading (for first page header)
        pages: List of content for each page
        font_size: Starting font size

    Returns:
        List of rendered page results
    """
    num_pages = len(pages)
    results = []

    # First render pass
    for i, page_content in enumerate(pages):
        if i == 0:
            # First page with header
            page_data = [reading_name] + page_content
            result = draw_text_pagination_first(background, page_data, font_size=font_size)
        elif i == num_pages - 1:
            # Last page with closing
            result = draw_text_pagination_second(background, page_content, font_size=font_size)
        else:
            # Middle page
            result = draw_text_pagination_middle(background, page_content, font_size=font_size)

        results.append(result)

    # Check if all pages fit, reduce font size if needed
    while any(not _text_fits(r["drawn_y"], font_size) for r in results) and font_size >= FONT_SIZE_MIN:
        font_size -= 1
        results = []

        for i, page_content in enumerate(pages):
            if i == 0:
                page_data = [reading_name] + page_content
                result = draw_text_pagination_first(background, page_data, font_size=font_size)
            elif i == num_pages - 1:
                result = draw_text_pagination_second(background, page_content, font_size=font_size)
            else:
                result = draw_text_pagination_middle(background, page_content, font_size=font_size)

            results.append(result)

    logger.info(f"  Final font size: {font_size}")
    return results


def _estimate_text_height(content: List[str], font_size: int, is_first_page: bool = False) -> int:
    """
    Estimate the height needed to render content at given font size.

    Args:
        content: List of paragraphs/lines
        font_size: Font size to use
        is_first_page: If True, accounts for header space

    Returns:
        Estimated pixel height
    """
    import textwrap

    line_height = int(1.2 * font_size)
    # Based on _calculate_layout() in draw_posts.py, minus safety margin
    # for proportional font width variation (wide Polish chars like W, Ś, ą)
    size_x_left = int(25 / 12 * font_size)
    width = int(75 - 0.325 * size_x_left) - 3

    total_lines = 0

    if is_first_page:
        # Title row: reading_name + reference on one line
        total_lines += 1
        # Subtitle: skip if empty (Passion Gospel)
        subtitle = content[1] if len(content) > 1 else ""
        if subtitle:
            total_lines += 1
        # Bold intro: count wrapped lines using a tighter width — bold glyphs
        # render ~10% wider per char than the regular font this width is calibrated for
        intro = content[2] if len(content) > 2 else ""
        if intro:
            bold_width = max(int(width * 0.9), 1)
            total_lines += max(len(textwrap.wrap(intro, width=bold_width)), 1)
        # Gap between header and body
        total_lines += 1
        body_start = 3
    else:
        body_start = 0

    for paragraph in content[body_start:]:
        wrapped = textwrap.wrap(paragraph, width=width)
        total_lines += max(len(wrapped), 1)

    return total_lines * line_height + (font_size * 2)  # Safe margin


MAX_PAGES_PER_READING = 4
MAX_PAGES_GOSPEL = 14  # Passion Gospels spread across more pages for readability

# Filename substrings that identify generated reading images. Anything else in
# a date folder (cover.jpg, mateusztront.jpg, midjourney drops) is treated as a
# cover and must be preserved when text graphics are regenerated.
READING_PREFIXES = (
    "PIERWSZE", "PSALM", "DRUGIE", "TRZECIE", "CZWARTE",
    "PIĄTE", "SZÓSTE", "SIÓDME", "ÓSME",
    "SEKWENCJA", "EWANGELIA",
)


def _text_fits(drawn_y: int, font_size: int) -> bool:
    """
    Check whether the rendered text fits inside the image without clipping.

    drawn_y points at the anchor of the last drawn line (anchor="lm" puts the
    text middle there), so glyphs extend ~font_size/2 below it. We require a
    full font-size margin so descenders and accented Polish chars stay clear of
    the bottom edge.
    """
    return drawn_y <= IMAGE_SIZE - font_size


def _build_pages(header_content, body_content, closing, split_indices):
    """Build page list from split indices into body_content."""
    pages = []
    prev = 0
    for i, idx in enumerate(split_indices):
        chunk = body_content[prev:idx]
        pages.append((header_content + chunk) if i == 0 else chunk)
        prev = idx
    last_chunk = body_content[prev:]
    pages.append(last_chunk + closing)
    return pages


def _calculate_optimal_pagination(
    content: List[str],
    font_size: int,
    max_height: int = IMAGE_SIZE - 40,
    reading_name: str = "",
    max_pages: int = MAX_PAGES_PER_READING,
    prefer_readability: bool = False,
) -> Tuple[int, int, List[List[str]]]:
    """
    Find the split (num_pages + font) that maximises font size.

    Uses greedy packing: for each font size (large→small), greedily fill pages
    until all content fits within max_pages.  O(fonts × paragraphs) — no
    combinatorial explosion.

    When prefer_readability is True (Passion Gospels), the algorithm picks the
    largest font that fits within the page limit — accepting more pages for
    better readability.  Otherwise it minimises pages first.

    Returns:
        Tuple of (num_pages, optimal_font_size, list of content per page)
    """
    header_content = content[:3]   # reference, subtitle, intro
    body_content = content[3:-1]   # body paragraphs
    closing = content[-1:]         # closing phrase
    n = len(body_content)

    # --- 1 page ---
    for test_font in range(FONT_SIZE_MAX, FONT_SIZE_MIN - 1, -2):
        if _estimate_text_height(content, test_font, is_first_page=True) <= max_height:
            return 1, test_font, [content]

    # --- multi-page: greedy packing, prefer fewest pages then largest font ---
    import textwrap

    best_num = max_pages + 1
    best_font = FONT_SIZE_MIN - 1
    best_pages = None

    for test_font in range(FONT_SIZE_MAX, FONT_SIZE_MIN - 1, -2):
        line_height = int(1.2 * test_font)
        size_x_left = int(25 / 12 * test_font)
        width = int(75 - 0.325 * size_x_left) - 3
        para_lines = [max(len(textwrap.wrap(p, width=width)), 1) for p in body_content]

        # Header height for first page
        header_lines = 1
        if len(content) > 1 and content[1]:
            header_lines += 1
        if len(content) > 2 and content[2]:
            bold_width = max(int(width * 0.9), 1)
            header_lines += max(len(textwrap.wrap(content[2], width=bold_width)), 1)
        header_lines += 1  # gap
        margin = test_font * 2
        max_lines = (max_height - margin) // line_height

        # Greedy packing
        pages: List[List[str]] = []
        current_page: List[str] = list(header_content)
        current_lines = header_lines

        for i, para in enumerate(body_content):
            lines_needed = para_lines[i]
            if current_lines + lines_needed > max_lines and current_page:
                pages.append(current_page)
                current_page = []
                current_lines = 0
            current_page.append(para)
            current_lines += lines_needed

        if closing:
            current_page.extend(closing)
        if current_page:
            pages.append(current_page)

        num_pages = len(pages)
        if num_pages > max_pages:
            continue

        # Verify all pages actually fit
        fits = all(
            _estimate_text_height(p, test_font, is_first_page=(i == 0)) <= max_height
            for i, p in enumerate(pages)
        )
        if not fits:
            continue

        if prefer_readability:
            # Passion mode: largest font first (we iterate large→small, so first valid wins)
            return num_pages, test_font, pages

        # Prefer fewer pages; among equal page counts prefer larger font
        if num_pages < best_num or (num_pages == best_num and test_font > best_font):
            best_num = num_pages
            best_font = test_font
            best_pages = pages

    if best_pages:
        return best_num, best_font, best_pages

    # Fallback: even split at minimum font
    pages_needed = min(max_pages, n + 1)
    chunk_size = math.ceil(n / max(pages_needed - 1, 1))
    fallback_pages = []
    for i in range(0, n, chunk_size):
        chunk = body_content[i:i + chunk_size]
        if i == 0:
            chunk = header_content + chunk
        fallback_pages.append(chunk)
    if closing and fallback_pages:
        fallback_pages[-1].extend(closing)
    return len(fallback_pages), FONT_SIZE_MIN, fallback_pages


def _create_two_page_pagination(
    name: str, content: List[str], break_point: int
) -> Dict[str, List[str]]:
    """Create pagination dictionary for 2-page split."""
    return {
        f"{name} cz.1": [name] + content[:break_point],
        f"{name} cz.2": content[break_point:],
    }


def _create_four_page_pagination(
    name: str, content: List[str], break_point: int
) -> Dict[str, List[str]]:
    """Create pagination dictionary for 4-page split."""
    bp = break_point + 2
    return {
        f"{name} cz.1": [name] + content[:bp],
        f"{name} cz.2": content[bp : 2 * bp - 2],
        f"{name} cz.3": content[2 * bp - 2 : 3 * bp - 4],
        f"{name} cz.6": content[3 * bp - 4 :],
    }


def _render_two_pages(
    background: Image.Image, pages: Dict[str, List[str]], font_size: int
) -> Dict[str, dict]:
    """Render 2-page pagination with font size adjustment."""
    keys = list(pages.keys())

    result_1 = draw_text_pagination_first(background, pages[keys[0]], font_size=font_size)
    result_2 = draw_text_pagination_second(background, pages[keys[1]], font_size=font_size)

    while not _text_fits(result_1["drawn_y"], font_size) or not _text_fits(result_2["drawn_y"], font_size):
        font_size -= 1
        result_1 = draw_text_pagination_first(background, pages[keys[0]], font_size=font_size)
        result_2 = draw_text_pagination_second(background, pages[keys[1]], font_size=font_size)

    return {keys[0]: result_1, keys[1]: result_2}


def _render_four_pages(
    background: Image.Image, pages: Dict[str, List[str]], font_size: int
) -> Dict[str, dict]:
    """Render 4-page pagination with font size adjustment."""
    keys = list(pages.keys())

    result_1 = draw_text_pagination_first(background, pages[keys[0]], font_size=font_size)
    result_2 = draw_text_pagination_middle(background, pages[keys[1]], font_size=font_size)
    result_3 = draw_text_pagination_middle(background, pages[keys[2]], font_size=font_size)
    result_6 = draw_text_pagination_second(background, pages[keys[3]], font_size=font_size)

    while any(
        not _text_fits(r["drawn_y"], font_size) for r in [result_1, result_2, result_3, result_6]
    ):
        font_size -= 1
        result_1 = draw_text_pagination_first(background, pages[keys[0]], font_size=font_size)
        result_2 = draw_text_pagination_middle(background, pages[keys[1]], font_size=font_size)
        result_3 = draw_text_pagination_middle(background, pages[keys[2]], font_size=font_size)
        result_6 = draw_text_pagination_second(background, pages[keys[3]], font_size=font_size)

    return {keys[0]: result_1, keys[1]: result_2, keys[2]: result_3, keys[3]: result_6}


def _generate_psalm_image(
    content_dic: Dict[str, List[str]],
    background: Image.Image,
    output_path: Path,
    psalm_key: str = "PSALM RESPONSORYJNY",
) -> str:
    """Generate psalm image with automatic font size adjustment."""
    # Extract numeric prefix for numbered vigil psalms (e.g. "3 PSALM RESPONSORYJNY" → num=3)
    num = None
    if psalm_key != "PSALM RESPONSORYJNY":
        try:
            num = int(psalm_key.split()[0])
        except (ValueError, IndexError):
            pass

    font_size = FONT_SIZE_PSALM
    result = draw_psalm(content_dic, background, font_size, num=num)

    while not _text_fits(result["drawn_y"], font_size):
        font_size -= 1
        result = draw_psalm(content_dic, background, font_size, num=num)

    filename = f"{psalm_key}.jpg"
    result["picture"].save(output_path / filename)
    return filename


def _generate_vigil_images(
    content_dic: Dict[str, List[str]],
    background: Image.Image,
    output_path: Path,
) -> List[str]:
    """Generate images for Easter Vigil readings interleaved with their psalms."""
    posts_list = []

    for key in content_dic:
        if "PSALM" in key:
            filename = _generate_psalm_image(content_dic, background, output_path, psalm_key=key)
            posts_list.append(filename)
        else:
            # Regular reading
            num_pages, optimal_font, pages = _calculate_optimal_pagination(
                content_dic[key], FONT_SIZE_DEFAULT, reading_name=key
            )
            logger.info(f"{key}: {num_pages} page(s), font size {optimal_font}")

            if num_pages == 1:
                result = draw_text(content_dic, background, key, optimal_font)
                result["picture"].save(output_path / f"{key}.jpg")
                posts_list.append(f"{key}.jpg")
            else:
                rendered = _render_smart_pages(background, key, pages, optimal_font)
                for i, img_result in enumerate(rendered):
                    filename = f"{key}{i + 1}.jpg"
                    img_result["picture"].save(output_path / filename)
                    posts_list.append(filename)

    return posts_list


@eel.expose
def draw_post(thedate: str, verse_break: int = 0) -> List[str]:
    """
    Create post graphics for a given date.

    Args:
        thedate: Date string in YYYY-MM-DD format
        verse_break: Manual break point for pagination (0 for auto)

    Returns:
        List of generated file paths
    """
    verse_break = int(verse_break)

    logger.info(f"Fetching readings for {thedate}")

    try:
        content_list = _scrape_content_list(thedate)
    except (requests.RequestException, ValueError) as e:
        logger.error(f"Failed to fetch readings: {e}")
        return []

    # Process content
    content_list = _normalize_vigil_markers(content_list, thedate)
    content_list = _clean_content_list(content_list)
    content_list = _normalize_readings(content_list)

    # Detect special Easter week days
    is_vigil = "TRZECIE CZYTANIE" in content_list

    if is_vigil:
        content_dic = _parse_vigil_readings(content_list)
        content_dic = _filter_easter_vigil(content_dic)
    else:
        content_dic = _parse_readings(content_list)

    # Post-process readings
    _add_psalm_refrains(content_dic)
    _truncate_readings(content_dic)
    _clean_gospel_markers(content_dic)
    _remove_pre_gospel_from_reading(content_dic)
    _remove_liturgical_notes(content_dic)
    _normalize_sekwencja_content(content_dic)

    # Normalise Gospel header structure
    _ensure_gospel_subtitle_slot(content_dic)
    _normalize_passion_gospel_header(content_dic)
    # Detect Passion Gospel (Palm Sunday / Good Friday) — very long Gospel
    # Count body paragraphs only (exclude 3 header items + 1 closing) to avoid
    # false positives on normal-length Gospels with many short paragraphs
    gospel_body_count = max(len(content_dic.get("EWANGELIA", [])) - 4, 0)
    is_passion = gospel_body_count > PASSION_SPLIT_THRESHOLD * 3
    # Split overlong body paragraphs (any reading) so the paginator can place
    # them without overflowing — needed for long Pauline speeches as well as
    # Passion Gospels.
    _split_long_paragraphs(content_dic)

    # Create output directory and clear stale reading images from previous runs.
    # Preserve cover images (anything not matching a reading prefix) so users can
    # regenerate text graphics without losing a cover they've already prepared.
    output_path = WEB_DIR / thedate
    output_path.mkdir(parents=True, exist_ok=True)
    for stale in output_path.glob("*.jpg"):
        if any(p in stale.name for p in READING_PREFIXES):
            stale.unlink()

    # Generate images
    background = _create_background()

    if is_vigil:
        posts_list = _generate_vigil_images(content_dic, background, output_path)
        # Save ordering file so publish() can use the correct sequence
        order_file = output_path / "_order.txt"
        order_file.write_text("\n".join(posts_list), encoding="utf-8")
        logger.info(f"Easter Vigil: {len(posts_list)} images, order saved to _order.txt")
    else:
        posts_list = _generate_reading_images(content_dic, background, output_path, verse_break, passion_mode=is_passion)
        posts_list.append(_generate_psalm_image(content_dic, background, output_path))

    if is_passion:
        logger.info(f"Passion Gospel detected — Gospel will use extended pagination")

    logger.info(f"Generated {len(posts_list)} images")

    return ["/" + thedate + "/"] + posts_list


@eel.expose
def readings_eng(thedate: str) -> List[List[str]]:
    """Fetch English readings from Vatican News."""
    url = f"{LITURGY_URL_EN}/{thedate.replace('-', '/')}.html"

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Failed to fetch English readings: {e}")
        return []

    soup = BeautifulSoup(response.content, "html.parser")
    content_sections = soup.find_all("div", "section__content")

    return [
        [line.replace('"', "") for line in section.get_text().split("\n")]
        for section in content_sections
    ]


def _parse_polish_reference(reference: str) -> Optional[str]:
    """
    Parse Polish Bible reference to English format for bible-api.com.

    Example: "J 5, 1-16" -> "John 5:1-16"
             "Rdz 1, 1-5" -> "Genesis 1:1-5"
    """
    # Clean up the reference
    ref = reference.strip()

    # Pattern: Book Chapter, Verses (e.g., "J 5, 1-16" or "1 Kor 12, 3-7")
    # Handle books with numbers like "1 Kor", "2 Sm"
    pattern = r"^(\d?\s?[A-Za-zżźćńółęąśŻŹĆŃÓŁĘĄŚ]+)\s+(\d+),?\s*([\d\-\.a-z]+)"
    match = re.match(pattern, ref, re.IGNORECASE)

    if not match:
        logger.warning(f"Could not parse reference: {ref}")
        return None

    book_pl = match.group(1).strip()
    chapter = match.group(2)
    verses_raw = match.group(3).replace(" ", "")

    # Strip letter suffixes (a, b, c) from verse numbers - API doesn't support them
    verses_raw = re.sub(r'[a-z]', '', verses_raw)

    # Handle complex verse references (e.g., "16.18-21.24" -> "16-24")
    # Bible API only supports simple ranges, so extract min and max verse
    all_numbers = re.findall(r'\d+', verses_raw)
    if all_numbers:
        min_verse = min(int(n) for n in all_numbers)
        max_verse = max(int(n) for n in all_numbers)
        if min_verse == max_verse:
            verses = str(min_verse)
        else:
            verses = f"{min_verse}-{max_verse}"
    else:
        verses = verses_raw

    # Find English book name
    book_en = POLISH_TO_ENGLISH_BOOKS.get(book_pl)
    if not book_en:
        # Try case-insensitive match
        for pl, en in POLISH_TO_ENGLISH_BOOKS.items():
            if pl.lower() == book_pl.lower():
                book_en = en
                break

    if not book_en:
        logger.warning(f"Unknown book abbreviation: {book_pl}")
        return None

    return f"{book_en} {chapter}:{verses}"


def _fetch_english_bible_text(reference: str) -> Optional[str]:
    """
    Fetch English Bible text from bible-api.com.

    Args:
        reference: English Bible reference (e.g., "John 5:1-16")

    Returns:
        Bible text as string, or None on error
    """
    try:
        # bible-api.com format: https://bible-api.com/john+3:16
        url = f"https://bible-api.com/{reference.replace(' ', '+')}"
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        data = response.json()
        text = None
        if "text" in data:
            text = data["text"].strip()
        elif "verses" in data:
            # Combine verses if returned as array
            text = " ".join(v.get("text", "") for v in data["verses"]).strip()

        if text:
            # Clean text for Midjourney - remove quotation marks that cause text rendering
            text = text.replace('"', '').replace("'", '').replace('"', '').replace('"', '')
            text = text.replace("'", "").replace("'", "")
            # Remove verse numbers
            text = re.sub(r'\d+\s*', '', text)
            return text.strip()

        return None
    except Exception as e:
        logger.error(f"Failed to fetch Bible text for {reference}: {e}")
        return None


@eel.expose
def get_english_reading_text(thedate: str, reading_name: str) -> str:
    """
    Get English reading text by parsing Polish reference and fetching from Bible API.

    Args:
        thedate: Date string in YYYY-MM-DD format
        reading_name: Polish reading name (e.g., "EWANGELIA", "PIERWSZE CZYTANIE")

    Returns:
        English Bible text for the reading
    """
    try:
        # Get Polish reading to extract reference
        content_dic = _get_readings_dict(thedate)

        if reading_name not in content_dic:
            return f"Reading '{reading_name}' not found"

        reading_lines = content_dic[reading_name]
        if not reading_lines:
            return "No reading content"

        # First line contains the reference (e.g., "J 5, 1-16")
        polish_ref = reading_lines[0]
        logger.info(f"Polish reference: {polish_ref}")

        # Parse to English format
        english_ref = _parse_polish_reference(polish_ref)
        if not english_ref:
            return f"Could not parse reference: {polish_ref}"

        logger.info(f"English reference: {english_ref}")

        # Fetch from Bible API
        english_text = _fetch_english_bible_text(english_ref)
        if not english_text:
            return f"Could not fetch text for: {english_ref}"

        return english_text

    except Exception as e:
        logger.error(f"Failed to get English reading: {e}")
        return f"Error: {e}"


@eel.expose
def readings_pol(thedate: str) -> List[str]:
    """Fetch Polish readings."""
    url = f"{LITURGY_URL_PL}/{thedate}"

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Failed to fetch Polish readings: {e}")
        return []

    soup = BeautifulSoup(response.content, "html.parser")

    try:
        content_list = soup.find_all("div", "txt__rich-area")[1].get_text().split("\n")
        return content_list[3:]
    except (IndexError, AttributeError) as e:
        logger.error(f"Failed to parse Polish readings: {e}")
        return []


def _build_caption(caption: str, thedate: str) -> str:
    """Build the full Instagram caption from user text and metadata."""
    hashtags = " ".join(DEFAULT_HASHTAGS)
    clean_caption = caption.split("\n***\n")[0].rstrip()
    return f"""{clean_caption}
***
Grafika wykonana za pomocą sztucznej inteligencji.

{thedate}

{hashtags}
"""


@eel.expose
def publish(thedate: str, caption: str) -> str:
    """
    Publish images to Instagram.

    Args:
        thedate: Date string for the post
        caption: Custom caption text

    Returns:
        Empty string if successful, error message otherwise
    """
    try:
        client = login_user()
    except Exception as e:
        msg = f"Failed to login to Instagram: {e}"
        logger.error(msg)
        return msg

    working_path = WEB_DIR / thedate

    # Detect Easter week special days
    is_vigil = (working_path / "_order.txt").exists()

    # Order files: cover first (any non-reading image), then readings in order
    # SEKWENCJA is between DRUGIE and EWANGELIA
    reading_prefixes = READING_PREFIXES
    all_images = sorted(f for f in os.listdir(working_path) if f.endswith((".jpg", ".webp", ".png", ".jpeg")))

    # Convert cover images to 1080x1080 JPEG (Instagram requires consistent dimensions)
    cover_files = []
    for filename in all_images:
        if not any(p in filename for p in reading_prefixes):
            src = working_path / filename
            dst = working_path / "cover.jpg"
            img = Image.open(src).convert("RGB")
            img = img.resize((IMAGE_SIZE, IMAGE_SIZE), Image.LANCZOS)
            img.save(dst, "JPEG", quality=95)
            if src != dst:
                src.unlink()
            cover_files.append(dst)

    if not cover_files:
        msg = f"No cover image found — add a file starting with 'cover' or 'mateusztront' to web/{thedate}/"
        logger.error(msg)
        return msg

    if is_vigil:
        # Use the ordering file written by draw_post()
        order_file = working_path / "_order.txt"
        ordered_reading_files = [
            working_path / f for f in order_file.read_text(encoding="utf-8").splitlines() if f.strip()
        ]
        ordered_files = list(cover_files) + ordered_reading_files
    else:
        ordered_files = list(cover_files)
        for prefix in reading_prefixes:
            for filename in all_images:
                if prefix in filename:
                    ordered_files.append(working_path / filename)

    if not ordered_files:
        msg = "No files found to publish"
        logger.error(msg)
        return msg

    if len(ordered_files) > MAX_CAROUSEL_IMAGES:
        msg = f"Too many images ({len(ordered_files)}) — Instagram limit is {MAX_CAROUSEL_IMAGES}"
        logger.error(msg)
        return msg

    # Build caption
    full_caption = _build_caption(caption, thedate)

    alt_text = {
        "custom_accessibility_caption": (
            "Biblia, czytania, Duch Święty, Kościół Katolicki, "
            "czytania na dziś, AI, sztuczna inteligencja"
        )
    }

    logger.info(f"Publishing {len(ordered_files)} images for {thedate}")
    try:
        client.album_upload(
            paths=[str(p) for p in ordered_files],
            caption=full_caption,
            extra_data=alt_text,
        )
    except Exception as e:
        msg = f"Failed to publish: {e}"
        logger.error(msg)
        return msg

    logger.info(f"Successfully published post for {thedate}")
    return ""


# =============================================================================
# MIDJOURNEY COVER GENERATION FUNCTIONS
# =============================================================================


def _get_readings_dict(thedate: str) -> Dict[str, List[str]]:
    """
    Fetch and parse readings for a given date.

    This is a helper that extracts the readings parsing logic
    so it can be reused by cover generation functions.
    """
    content_list = _scrape_content_list(thedate)
    content_list = _normalize_vigil_markers(content_list, thedate)
    content_list = _clean_content_list(content_list)
    content_list = _normalize_readings(content_list)

    is_vigil = "TRZECIE CZYTANIE" in content_list
    if is_vigil:
        content_dic = _parse_vigil_readings(content_list)
        content_dic = _filter_easter_vigil(content_dic)
    else:
        content_dic = _parse_readings(content_list)

    _add_psalm_refrains(content_dic)
    _truncate_readings(content_dic)
    _clean_gospel_markers(content_dic)
    _remove_pre_gospel_from_reading(content_dic)
    _remove_liturgical_notes(content_dic)
    _normalize_sekwencja_content(content_dic)
    _ensure_gospel_subtitle_slot(content_dic)

    return content_dic


@eel.expose
def get_readings_for_cover(thedate: str) -> Dict[str, str]:
    """
    Get readings dictionary for user to select which one to use for cover.

    Returns dict with reading names as keys and preview text as values.
    """
    try:
        content_dic = _get_readings_dict(thedate)
        logger.info(f"get_readings_for_cover({thedate}) -> {list(content_dic.keys())}")

        # Return preview (first few lines) of each reading
        return {
            name: " ".join(text[:3])[:200] + "..."
            for name, text in content_dic.items()
        }
    except Exception as e:
        logger.error(f"Failed to get readings for cover: {e}")
        return {}


@eel.expose
def get_full_reading_text(thedate: str, reading_name: str) -> str:
    """Get the full text of a specific reading."""
    try:
        content_dic = _get_readings_dict(thedate)
        if reading_name in content_dic:
            return "\n".join(content_dic[reading_name])
        return ""
    except Exception as e:
        logger.error(f"Failed to get reading text: {e}")
        return ""


@eel.expose
def generate_cover_prompt(reading_text: str, reading_name: str) -> str:
    """
    Generate a Midjourney prompt from reading text using LLM.

    Returns the generated prompt for user to edit.
    """
    try:
        return generate_midjourney_prompt(reading_text, reading_name)
    except Exception as e:
        logger.error(f"Failed to generate prompt: {e}")
        return f"Error generating prompt: {e}"


@eel.expose
def generate_cover_prompt_variations(
    reading_text: str, reading_name: str, num_variations: int = 3
) -> List[str]:
    """
    Generate multiple prompt variations for user to choose from.

    Returns list of prompts.
    """
    try:
        return generate_prompt_variations(reading_text, reading_name, num_variations)
    except Exception as e:
        logger.error(f"Failed to generate prompt variations: {e}")
        return [f"Error: {e}"]


@eel.expose
def generate_cover_image(thedate: str, prompt: str) -> str:
    """
    Generate cover image via Midjourney with the given prompt.

    Returns path to the saved image, or error message.
    """
    try:
        logger.info(f"Generating cover for {thedate} with prompt: {prompt[:50]}...")

        output_path = WEB_DIR / thedate
        output_path.mkdir(parents=True, exist_ok=True)

        mj = MidjourneyWrapper()
        cover_path = mj.generate(
            prompt=prompt,
            save_path=output_path / "mateusztront.jpg",
            auto_upscale=True,
        )

        logger.info(f"Cover generated: {cover_path}")
        return f"/{thedate}/mateusztront.jpg"

    except Exception as e:
        logger.error(f"Failed to generate cover: {e}")
        return f"Error: {e}"


@eel.expose
def check_cover_exists(thedate: str) -> bool:
    """Check if a cover image already exists for the given date."""
    cover_path = WEB_DIR / thedate / "mateusztront.jpg"
    return cover_path.exists()


def _extract_upscale_buttons(components: list) -> dict:
    """Extract U1-U4 button custom_ids from Midjourney response components."""
    buttons = {}
    for row in components:
        if "components" in row:
            for button in row["components"]:
                label = button.get("label", "")
                if label in ["U1", "U2", "U3", "U4"]:
                    buttons[label] = button.get("custom_id", "")
    return buttons


@eel.expose
def generate_cover_grid(thedate: str, prompt: str) -> dict:
    """
    Generate 4-image grid via Midjourney without upscaling.

    Returns dict with grid_url, message_id, and buttons for user selection.
    """
    try:
        logger.info(f"Generating grid for {thedate} with prompt: {prompt[:50]}...")

        output_path = WEB_DIR / thedate
        output_path.mkdir(parents=True, exist_ok=True)

        mj = MidjourneyWrapper()
        result = mj.generate_grid(prompt)

        grid_url = result.get("attachments", [{}])[0].get("url", "")
        message_id = result.get("id", "")
        buttons = _extract_upscale_buttons(result.get("components", []))

        logger.info(f"Grid generated: {grid_url[:50]}...")

        return {
            "grid_url": grid_url,
            "message_id": message_id,
            "buttons": buttons,
        }

    except Exception as e:
        logger.error(f"Failed to generate grid: {e}")
        return {"error": str(e)}


@eel.expose
def upscale_cover(thedate: str, message_id: str, custom_id: str) -> str:
    """
    Upscale selected variant and save as cover image.

    Args:
        thedate: Date for output directory
        message_id: Discord message ID from generate_cover_grid
        custom_id: Button custom_id for selected variant (U1-U4)

    Returns:
        Path to saved image or error message
    """
    try:
        logger.info(f"Upscaling variant for {thedate}...")

        output_path = WEB_DIR / thedate
        output_path.mkdir(parents=True, exist_ok=True)
        save_path = output_path / "mateusztront.jpg"

        mj = MidjourneyWrapper()
        mj.upscale_variant(message_id, custom_id, save_path)

        logger.info(f"Cover upscaled: {save_path}")
        return f"/{thedate}/mateusztront.jpg"

    except Exception as e:
        logger.error(f"Failed to upscale: {e}")
        return f"Error: {e}"


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    draw_post("2025-04-25", 8)
