"""
Main content processor for Cyber Bible.
Handles scraping liturgical readings, generating images, and publishing to Instagram.
"""

import logging
import os
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

logger = logging.getLogger(__name__)


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
                    content_dic[cut_points[0]] = staging_list
                    staging_list = []
                    del cut_points[0]
                    break
                if item not in cut_points:
                    staging_list.append(item)
                else:
                    content_dic[cut_points[0]] = staging_list
                    staging_list = []
                    del cut_points[0]
                    break

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
    """Generate images for all readings."""
    posts_list = []

    for reading_name in content_dic.keys():
        if reading_name == "PSALM RESPONSORYJNY":
            continue

        font_size = FONT_SIZE_DEFAULT
        pagination_font_size = FONT_SIZE_DEFAULT
        result = draw_text(content_dic, background, reading_name, font_size)

        # Check if text fits on single page
        if result["drawn_y"] <= IMAGE_SIZE - 20:
            result["picture"].save(output_path / f"{reading_name}.jpg")
            posts_list.append(f"{reading_name}.jpg")
            continue

        # Try reducing font size first
        while result["drawn_y"] > IMAGE_SIZE - 20 and font_size >= FONT_SIZE_MIN:
            font_size -= 1
            result = draw_text(content_dic, background, reading_name, font_size)

        if result["drawn_y"] <= IMAGE_SIZE - 20:
            result["picture"].save(output_path / f"{reading_name}.jpg")
            posts_list.append(f"{reading_name}.jpg")
            continue

        # Need pagination
        reading_content = content_dic[reading_name]
        effective_break = verse_break if verse_break > 0 else 4

        if len(reading_content) > 20:
            # 4-page pagination for long readings
            pages = _create_four_page_pagination(
                reading_name, reading_content, effective_break
            )
            images = _render_four_pages(background, pages, pagination_font_size)

            for i, (name, img_result) in enumerate(images.items()):
                filename = f"{reading_name}{i + 1}.jpg"
                img_result["picture"].save(output_path / filename)
                posts_list.append(filename)
        else:
            # 2-page pagination
            pages = _create_two_page_pagination(
                reading_name, reading_content, effective_break
            )
            images = _render_two_pages(background, pages, pagination_font_size)

            for i, (name, img_result) in enumerate(images.items()):
                filename = f"{reading_name}{i + 1}.jpg"
                img_result["picture"].save(output_path / filename)
                posts_list.append(filename)

    return posts_list


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
    content_sections = soup.find_all("div", "section__content")[:2]

    return [
        [line.replace('"', "") for line in section.get_text().split("\n")]
        for section in content_sections
    ]


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


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    draw_post("2025-04-25", 8)
