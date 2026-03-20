"""
Main content processor for Cyber Bible.
Handles scraping liturgical readings, generating images, and publishing to Instagram.
"""

import logging
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

        # Skip passion-specific content
        skip_phrases = [
            "Jezus przed Piłatem",
            "Droga krzyżowa",
            "Wszyscy klękają i przez chwilę zachowują milczenie.",
        ]
        if any(phrase in text for phrase in skip_phrases):
            continue

        # Strip whitespace
        cleaned.append(text.strip())

    return cleaned


def _normalize_readings(content_list: List[str]) -> List[str]:
    """Normalize reading names and handle shorter/longer versions."""
    result = content_list.copy()

    # Replacements for shorter versions
    replacements = [
        ("PIERWSZE CZYTANIE KRÓTSZE", "PIERWSZE CZYTANIE"),
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

    # Handle longer versions - prefer shorter
    try:
        if "PIERWSZE CZYTANIE KRÓTSZE" in result:
            start = result.index("PIERWSZE CZYTANIE KRÓTSZE")
            end = result.index("Oto słowo Boże", start) + 1
            result = result[start:end]
            result[0] = result[0].replace("PIERWSZE CZYTANIE KRÓTSZE", "PIERWSZE CZYTANIE")
    except ValueError:
        pass

    # Remove longer Gospel version if shorter exists
    try:
        longer_start = result.index("EWANGELIA DŁUŻSZA")
        longer_end = result.index("Oto słowo Pańskie.", longer_start) + 1
        del result[longer_start:longer_end]
        result = result[: result.index("Oto słowo Pańskie.") + 1]
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

    # Remove sequence
    try:
        seq_start = result.index("SEKWENCJA")
        seq_end = result.index("Amen. Alleluja.") + 1
        del result[seq_start - 1 : seq_end]
    except ValueError:
        pass

    # Remove optional sequence note
    try:
        result.remove("Można odmawiać sekwencję: Niech w święto radosne Paschalnej Ofiary.")
    except ValueError:
        pass

    return result


def _parse_readings(content_list: List[str]) -> Dict[str, List[str]]:
    """Parse content list into dictionary of readings."""
    # Determine cut points based on available readings
    if "EWANGELIA KRÓTSZA" in content_list:
        cut_points = ["PIERWSZE CZYTANIE", "PSALM RESPONSORYJNY", "DRUGIE CZYTANIE", "EWANGELIA KRÓTSZA"]
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


def _add_psalm_refrains(content_dic: Dict[str, List[str]]) -> None:
    """Add refrain markers to psalm if missing."""
    psalm_key = "PSALM RESPONSORYJNY"
    if psalm_key not in content_dic:
        return

    psalm = content_dic[psalm_key]
    refrain_count = reduce(lambda x, y: x + 1 if "Refren" in y else x, psalm, 0)

    if len(psalm) > 6 and refrain_count == 1:
        # Insert refrain markers at appropriate positions
        for pos in [16, 11, 6]:
            if pos < len(psalm):
                psalm.insert(pos, "Refren")


def _truncate_readings(content_dic: Dict[str, List[str]]) -> None:
    """Truncate readings at their closing phrases."""
    endings = {
        "PIERWSZE CZYTANIE": "Oto słowo Boże",
        "DRUGIE CZYTANIE": "Oto słowo Boże",
        "EWANGELIA": "Oto słowo Pańskie.",
    }

    for reading, ending in endings.items():
        if reading in content_dic:
            try:
                end_idx = content_dic[reading].index(ending) + 1
                content_dic[reading] = content_dic[reading][:end_idx]
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


def _generate_reading_images(
    content_dic: Dict[str, List[str]],
    background: Image.Image,
    output_path: Path,
    verse_break: int,
) -> List[str]:
    """Generate images for all readings with smart auto-pagination."""
    posts_list = []

    for reading_name in content_dic.keys():
        if reading_name == "PSALM RESPONSORYJNY":
            continue

        reading_content = content_dic[reading_name]
        font_size = FONT_SIZE_DEFAULT

        # Calculate optimal pagination
        num_pages, optimal_font, pages = _calculate_optimal_pagination(
            reading_content, font_size
        )

        logger.info(f"{reading_name}: {num_pages} page(s), font size {optimal_font}")

        if num_pages == 1:
            # Single page - use optimal font calculated by pagination
            result = draw_text(content_dic, background, reading_name, optimal_font)
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
    while any(r["drawn_y"] > IMAGE_SIZE - 20 for r in results) and font_size >= FONT_SIZE_MIN:
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
    # Conservative width estimate to avoid overflow
    width = int(70 - 0.35 * (25 / 12 * font_size))

    total_lines = 0

    # Header takes ~3 lines on first page
    if is_first_page:
        total_lines += 3

    for paragraph in content:
        wrapped = textwrap.wrap(paragraph, width=width)
        total_lines += max(len(wrapped), 1)

    return total_lines * line_height + (font_size * 2)  # Safe margin


def _calculate_optimal_pagination(
    content: List[str],
    font_size: int,
    max_height: int = IMAGE_SIZE - 40
) -> Tuple[int, int, List[List[str]]]:
    """
    Calculate optimal number of pages and content division.

    SMART AUTOFIT:
    - If content fits on 1 page with font >= 48, use 1 page
    - Otherwise split into 2 pages and find largest font that fills both well

    Returns:
        Tuple of (num_pages, optimal_font_size, list of content per page)
    """
    # Content structure: [reference, subtitle, intro, body..., closing]
    # First page gets: reference, subtitle, intro + some body
    # Middle pages get: body only
    # Last page gets: body + closing

    header_content = content[:3]  # reference, subtitle, intro
    body_content = content[3:-1]  # body paragraphs
    closing = content[-1:]  # closing phrase

    # Try 1 page only if it fits with a GOOD font size (>= 48)
    for test_font in range(FONT_SIZE_MAX, 46, -2):
        total_height = _estimate_text_height(content, test_font, is_first_page=True)
        if total_height <= max_height:
            return 1, test_font, [content]

    # Content needs 2 pages - find largest font for 2-page layout
    # Put more content on first page (60/40 split)
    split_point = max(1, int(len(body_content) * 0.6))
    page1_body = body_content[:split_point]
    page2_body = body_content[split_point:]

    pages = [
        header_content + page1_body,
        page2_body + closing
    ]

    # Find largest font that fits both pages
    for test_font in range(FONT_SIZE_MAX, FONT_SIZE_MIN - 1, -2):
        page1_height = _estimate_text_height(pages[0], test_font, is_first_page=True)
        page2_height = _estimate_text_height(pages[1], test_font, is_first_page=False)
        if page1_height <= max_height and page2_height <= max_height:
            return 2, test_font, pages

    # Fallback to minimum font
    font_size = FONT_SIZE_MIN

    # Calculate how many pages we need
    # First page has header overhead, estimate body capacity
    first_page_body_capacity = (max_height - _estimate_text_height(header_content, font_size, True)) // (int(1.2 * font_size) * 2)
    middle_page_capacity = max_height // (int(1.2 * font_size) * 2)
    last_page_overhead = _estimate_text_height(closing, font_size) + font_size * 2

    # Calculate paragraphs per page
    total_body_paragraphs = len(body_content)

    if total_body_paragraphs <= first_page_body_capacity + middle_page_capacity:
        # 2 pages enough
        num_pages = 2
        split_point = max(1, total_body_paragraphs // 2)

        page1_body = body_content[:split_point]
        page2_body = body_content[split_point:]

        pages = [
            header_content + page1_body,
            page2_body + closing
        ]
    elif total_body_paragraphs <= first_page_body_capacity + 2 * middle_page_capacity:
        # 3 pages
        num_pages = 3
        third = max(1, total_body_paragraphs // 3)

        pages = [
            header_content + body_content[:third],
            body_content[third:2*third],
            body_content[2*third:] + closing
        ]
    else:
        # 4 pages
        num_pages = 4
        quarter = max(1, total_body_paragraphs // 4)

        pages = [
            header_content + body_content[:quarter],
            body_content[quarter:2*quarter],
            body_content[2*quarter:3*quarter],
            body_content[3*quarter:] + closing
        ]

    return num_pages, font_size, pages


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

    while result_1["drawn_y"] > IMAGE_SIZE - 20 or result_2["drawn_y"] > IMAGE_SIZE - 20:
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
        r["drawn_y"] > IMAGE_SIZE - 20 for r in [result_1, result_2, result_3, result_6]
    ):
        font_size -= 1
        result_1 = draw_text_pagination_first(background, pages[keys[0]], font_size=font_size)
        result_2 = draw_text_pagination_middle(background, pages[keys[1]], font_size=font_size)
        result_3 = draw_text_pagination_middle(background, pages[keys[2]], font_size=font_size)
        result_6 = draw_text_pagination_second(background, pages[keys[3]], font_size=font_size)

    return {keys[0]: result_1, keys[1]: result_2, keys[2]: result_3, keys[3]: result_6}


def _generate_psalm_image(
    content_dic: Dict[str, List[str]], background: Image.Image, output_path: Path
) -> str:
    """Generate psalm image with automatic font size adjustment."""
    font_size = FONT_SIZE_PSALM
    result = draw_psalm(content_dic, background, font_size)

    while result["drawn_y"] > IMAGE_SIZE - 20:
        font_size -= 1
        result = draw_psalm(content_dic, background, font_size)

    filename = "PSALM RESPONSORYJNY.jpg"
    result["picture"].save(output_path / filename)
    return filename


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
    url = f"{LITURGY_URL_PL}/{thedate}"

    logger.info(f"Fetching readings for {thedate}")

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Failed to fetch readings: {e}")
        return []

    soup = BeautifulSoup(response.content, "html.parser")

    try:
        content_areas = soup.find_all("div", "txt__rich-area")
        if len(content_areas) < 2:
            logger.error("Could not find reading content on page")
            return []
        content_list = content_areas[1].get_text().split("\n")
    except (IndexError, AttributeError) as e:
        logger.error(f"Failed to parse page content: {e}")
        return []

    # Process content
    content_list = _clean_content_list(content_list)
    content_list = _normalize_readings(content_list)
    content_dic = _parse_readings(content_list)

    # Post-process readings
    _add_psalm_refrains(content_dic)
    _truncate_readings(content_dic)
    _clean_gospel_markers(content_dic)
    _remove_pre_gospel_from_reading(content_dic)

    # Create output directory
    output_path = WEB_DIR / thedate
    output_path.mkdir(parents=True, exist_ok=True)

    # Generate images
    background = _create_background()
    posts_list = _generate_reading_images(content_dic, background, output_path, verse_break)
    posts_list.append(_generate_psalm_image(content_dic, background, output_path))

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


@eel.expose
def publish(thedate: str, caption: str) -> bool:
    """
    Publish images to Instagram.

    Args:
        thedate: Date string for the post
        caption: Custom caption text

    Returns:
        True if successful, False otherwise
    """
    try:
        client = login_user()
    except Exception as e:
        logger.error(f"Failed to login to Instagram: {e}")
        return False

    working_path = WEB_DIR / thedate

    # Ensure all files have .jpg extension (fixed logic bug from original)
    for filename in os.listdir(working_path):
        if not filename.endswith((".jpg", ".webp", ".png")):
            old_path = working_path / filename
            new_path = working_path / (filename.split(".")[0] + ".jpg")
            os.rename(old_path, new_path)

    # Order files: Midjourney first, then readings in order
    general_order = ["mateusz", "PIERWSZE", "PSALM", "DRUGIE", "EWANGELIA"]
    ordered_files = []

    for prefix in general_order:
        for filename in os.listdir(working_path):
            if prefix in filename:
                ordered_files.append(working_path / filename)

    if not ordered_files:
        logger.error("No files found to publish")
        return False

    # Build caption
    hashtags = " ".join(DEFAULT_HASHTAGS)
    full_caption = f"""{caption}
***
Grafika wykonana za pomocą sztucznej inteligencji.

{thedate}

{hashtags}
"""

    alt_text = {
        "custom_accessibility_caption": (
            "Biblia, czytania, Duch Święty, Kościół Katolicki, "
            "czytania na dziś, AI, sztuczna inteligencja"
        )
    }

    try:
        client.album_upload(
            paths=[str(p) for p in ordered_files],
            caption=full_caption,
            extra_data=alt_text,
        )
        logger.info(f"Successfully published post for {thedate}")
        return True
    except Exception as e:
        logger.error(f"Failed to publish: {e}")
        return False


# =============================================================================
# MIDJOURNEY COVER GENERATION FUNCTIONS
# =============================================================================


def _get_readings_dict(thedate: str) -> Dict[str, List[str]]:
    """
    Fetch and parse readings for a given date.

    This is a helper that extracts the readings parsing logic
    so it can be reused by cover generation functions.
    """
    url = f"{LITURGY_URL_PL}/{thedate}"

    response = requests.get(url, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.content, "html.parser")
    content_areas = soup.find_all("div", "txt__rich-area")

    if len(content_areas) < 2:
        raise ValueError("Could not find reading content on page")

    content_list = content_areas[1].get_text().split("\n")
    content_list = _clean_content_list(content_list)
    content_list = _normalize_readings(content_list)
    content_dic = _parse_readings(content_list)

    _truncate_readings(content_dic)
    _clean_gospel_markers(content_dic)

    return content_dic


@eel.expose
def get_readings_for_cover(thedate: str) -> Dict[str, str]:
    """
    Get readings dictionary for user to select which one to use for cover.

    Returns dict with reading names as keys and preview text as values.
    """
    try:
        content_dic = _get_readings_dict(thedate)

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
