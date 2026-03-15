"""
Image text rendering engine for Cyber Bible.
Handles drawing biblical text on images with justified alignment and pagination.
"""

import copy
import logging
import textwrap
from enum import Enum
from typing import Dict, List, Optional, Any

from PIL import Image, ImageDraw, ImageFont

from config import (
    IMAGE_SIZE,
    FONT_SIZE_DEFAULT,
    FONT_SIZE_PSALM,
    FONT_REGULAR,
    FONT_BOLD,
    FONT_FALLBACK_REGULAR,
    FONT_FALLBACK_BOLD,
)

logger = logging.getLogger(__name__)


class PageType(Enum):
    """Type of page in a multi-page reading."""
    SINGLE = "single"
    FIRST = "first"
    MIDDLE = "middle"
    LAST = "last"


def _load_fonts(font_size: int) -> tuple:
    """
    Load fonts with fallback support.

    Returns:
        Tuple of (regular_font, bold_font, small_font)
    """
    font_size_small = int(0.75 * font_size)

    try:
        fnt = ImageFont.truetype(str(FONT_REGULAR), font_size)
        fnt_b = ImageFont.truetype(str(FONT_BOLD), font_size)
        fnt_s = ImageFont.truetype(str(FONT_REGULAR), font_size_small)
    except OSError:
        logger.warning(f"Could not load Tahoma fonts, using fallback")
        try:
            fnt = ImageFont.truetype(FONT_FALLBACK_REGULAR, font_size)
            fnt_b = ImageFont.truetype(FONT_FALLBACK_BOLD, font_size)
            fnt_s = ImageFont.truetype(FONT_FALLBACK_REGULAR, font_size_small)
        except OSError:
            logger.error("Could not load any fonts, using default")
            fnt = ImageFont.load_default()
            fnt_b = fnt
            fnt_s = fnt

    return fnt, fnt_b, fnt_s


def _calculate_layout(font_size: int) -> Dict[str, int]:
    """Calculate layout dimensions based on font size."""
    size_x_left = int(25 / 12 * font_size)
    return {
        "size_x_left": size_x_left,
        "size_x_right": IMAGE_SIZE - 2 * size_x_left,
        "size_y": int(1.2 * font_size),
        "width": int(75 - 0.325 * size_x_left),
        "image_size": IMAGE_SIZE,
    }


def _draw_justified_paragraph(
    draw: ImageDraw.Draw,
    paragraphs: List[str],
    start_y: int,
    layout: Dict[str, int],
    font: ImageFont.FreeTypeFont,
    indent_first_line: bool = True,
) -> int:
    """
    Draw paragraphs with justified text alignment.

    Args:
        draw: PIL ImageDraw object
        paragraphs: List of paragraph strings
        start_y: Starting Y coordinate
        layout: Layout dimensions dictionary
        font: Font to use
        indent_first_line: Whether to indent the first line of paragraphs

    Returns:
        Final Y coordinate after drawing
    """
    var_y = start_y
    size_x_left = layout["size_x_left"]
    size_x_right = layout["size_x_right"]
    size_y = layout["size_y"]
    width = layout["width"]

    for paragraph in paragraphs:
        lines = textwrap.wrap(paragraph, width=width, initial_indent="     ")
        if not lines:
            continue

        lines[0] = lines[0].strip()
        space_length_regular = 15

        for line_count, line in enumerate(lines):
            x_word = size_x_left
            x_word_indented = 2 * size_x_left
            words = line.split(" ")
            words_length = sum(draw.textlength(w, font=font) for w in words)

            # Handle single-word lines
            if len(words) == 1:
                words.append(" ")
                for word in words:
                    draw.text((x_word, var_y), word, font=font, fill="black", anchor="lm")
                    x_word += draw.textlength(word, font=font) + space_length_regular
                var_y += size_y
                continue

            # Last line - left-aligned, not justified
            if line_count == len(lines) - 1:
                if words_length + (len(words) - 1) * space_length_regular > size_x_right:
                    space_length_regular = (size_x_right - words_length) / (len(words) - 1)
                for word in words:
                    draw.text((x_word, var_y), word, font=font, fill="black", anchor="lm")
                    x_word += draw.textlength(word, font=font) + space_length_regular
                var_y += size_y
                continue

            # Calculate spacing for justified text
            space_length_indented = (size_x_right - x_word - words_length) / (len(words) - 1)
            space_length_regular = (size_x_right - words_length) / (len(words) - 1)

            # First line with indentation (except for special phrases)
            skip_indent = line == "Bracia:" or "Jezus powiedział" in line
            if line_count == 0 and indent_first_line and not skip_indent:
                for word in words:
                    draw.text((x_word_indented, var_y), word, font=font, fill="black", anchor="lm")
                    x_word_indented += draw.textlength(word, font=font) + space_length_indented
            else:
                for word in words:
                    draw.text((x_word, var_y), word, font=font, fill="black", anchor="lm")
                    x_word += draw.textlength(word, font=font) + space_length_regular

            var_y += size_y

    return var_y


def draw_text(
    content_dic: Dict[str, List[str]],
    background: Image.Image,
    name: str,
    font_size: int = FONT_SIZE_DEFAULT,
) -> Dict[str, Any]:
    """
    Draw a complete biblical reading on a single image.

    Args:
        content_dic: Dictionary with reading content
        background: Background image
        name: Key for the reading (e.g., "PIERWSZE CZYTANIE")
        font_size: Font size to use

    Returns:
        Dictionary with 'drawn_y' (final Y position) and 'picture' (drawn image)
    """
    fnt, fnt_b, fnt_s = _load_fonts(font_size)
    layout = _calculate_layout(font_size)

    out = copy.deepcopy(background)
    draw = ImageDraw.Draw(out)

    size_x_left = layout["size_x_left"]
    size_x_right = layout["size_x_right"]
    size_y = layout["size_y"]

    # Draw title and reference
    draw.text((size_x_left, size_x_left), name, font=fnt_b, fill="red", anchor="lm")
    draw.text(
        (size_x_right + size_x_left, size_x_left),
        content_dic[name][0],
        font=fnt_b,
        fill="red",
        anchor="rm",
    )

    # Draw subtitle
    var_y = size_x_left + size_y
    draw.text((size_x_left, var_y), content_dic[name][1], font=fnt_s, fill="black", anchor="lm")

    # Draw introduction paragraph in bold
    lines = textwrap.wrap(content_dic[name][2], width=layout["width"], initial_indent="     ")
    if lines:
        lines[0] = lines[0].strip()
        for line in lines:
            var_y += size_y
            draw.text((size_x_left, var_y), line, font=fnt_b, fill="black", anchor="lm")

    var_y += size_x_left

    # Draw body paragraphs
    body_paragraphs = content_dic[name][3:-1]
    var_y = _draw_justified_paragraph(draw, body_paragraphs, var_y, layout, fnt)

    # Draw closing phrase
    draw.text(
        (2 * size_x_left, var_y + size_y),
        content_dic[name][-1],
        font=fnt_b,
        fill="black",
        anchor="lm",
    )

    return {"drawn_y": var_y + size_y, "picture": out}


def draw_text_page(
    background: Image.Image,
    reading_list: List[str],
    page_type: PageType,
    font_size: int = FONT_SIZE_DEFAULT,
) -> Dict[str, Any]:
    """
    Draw a page of a multi-page reading.

    Args:
        background: Background image
        reading_list: Content for this page
        page_type: Type of page (first, middle, last)
        font_size: Font size to use

    Returns:
        Dictionary with 'drawn_y' and 'picture'
    """
    fnt, fnt_b, fnt_s = _load_fonts(font_size)
    layout = _calculate_layout(font_size)

    out = copy.deepcopy(background)
    draw = ImageDraw.Draw(out)

    size_x_left = layout["size_x_left"]
    size_x_right = layout["size_x_right"]
    size_y = layout["size_y"]

    var_y = size_x_left

    if page_type == PageType.FIRST:
        # Draw title and reference
        draw.text((size_x_left, size_x_left), reading_list[0], font=fnt_b, fill="red", anchor="lm")
        draw.text(
            (size_x_right + size_x_left, size_x_left),
            reading_list[1],
            font=fnt_b,
            fill="red",
            anchor="rm",
        )

        # Draw subtitle
        var_y = size_x_left + size_y
        draw.text((size_x_left, var_y), reading_list[2], font=fnt_s, fill="black", anchor="lm")

        # Draw introduction in bold
        lines = textwrap.wrap(reading_list[3], width=layout["width"], initial_indent="     ")
        if lines:
            lines[0] = lines[0].strip()
            for line in lines:
                var_y += size_y
                draw.text((size_x_left, var_y), line, font=fnt_b, fill="black", anchor="lm")

        var_y += size_x_left

        # Draw body paragraphs
        body = reading_list[4:]
        var_y = _draw_justified_paragraph(draw, body, var_y, layout, fnt)

    elif page_type == PageType.MIDDLE:
        # Just body paragraphs, no header
        var_y = _draw_justified_paragraph(draw, reading_list, var_y, layout, fnt)

    elif page_type == PageType.LAST:
        # Body paragraphs without the last element (closing phrase)
        body = reading_list[:-1] if reading_list else []
        var_y = _draw_justified_paragraph(draw, body, var_y, layout, fnt)

        # Draw closing phrase
        draw.text(
            (2 * size_x_left, var_y + size_y),
            "Oto Słowo Pańskie",
            font=fnt_b,
            fill="black",
            anchor="lm",
        )

    return {"drawn_y": var_y + size_y, "picture": out}


# Backward-compatible aliases
def draw_text_pagination_first(
    out: Image.Image,
    reading_list: List[str],
    size_x_left: int = None,
    size_y: int = None,
    font_size: int = FONT_SIZE_DEFAULT,
) -> Dict[str, Any]:
    """Draw first page of multi-page reading (backward compatible)."""
    return draw_text_page(out, reading_list, PageType.FIRST, font_size)


def draw_text_pagination_middle(
    out: Image.Image,
    reading_list: List[str],
    size_x_left: int = None,
    size_y: int = None,
    font_size: int = FONT_SIZE_DEFAULT,
) -> Dict[str, Any]:
    """Draw middle page of multi-page reading (backward compatible)."""
    return draw_text_page(out, reading_list, PageType.MIDDLE, font_size)


def draw_text_pagination_second(
    out: Image.Image,
    reading_list: List[str],
    size_x_left: int = None,
    size_y: int = None,
    font_size: int = FONT_SIZE_DEFAULT,
) -> Dict[str, Any]:
    """Draw last page of multi-page reading (backward compatible)."""
    return draw_text_page(out, reading_list, PageType.LAST, font_size)


def draw_psalm(
    content_dic: Dict[str, List[str]],
    background: Image.Image,
    font_size_psalm: int = FONT_SIZE_PSALM,
    num: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Draw Responsorial Psalm with refrain and acclamation.

    Args:
        content_dic: Dictionary with psalm content
        background: Background image
        font_size_psalm: Font size for psalm text
        num: Optional psalm number prefix

    Returns:
        Dictionary with 'drawn_y' and 'picture'
    """
    fnt_psalm, fnt_b_psalm, _ = _load_fonts(font_size_psalm)

    num_space = f"{num} " if num else ""
    psalm_key = f"{num_space}PSALM RESPONSORYJNY"

    # Clean up psalm reference if too long
    if len(content_dic[psalm_key][0]) > 30:
        content_dic[psalm_key][0] = content_dic[psalm_key][0].split(",")[0]

    # Remove optional sequence text
    try:
        seq_text = "Można odmawiać sekwencję: Niech w święto radosne Paschalnej Ofiary."
        if seq_text in content_dic[psalm_key]:
            content_dic[psalm_key].remove(seq_text)
    except ValueError:
        pass

    out = copy.deepcopy(background)
    draw = ImageDraw.Draw(out)

    y_distance = font_size_psalm
    y_further_distance = font_size_psalm * 0.7
    x_distance = font_size_psalm * 2

    # Draw title and reference
    draw.text(
        (x_distance, y_further_distance * 2),
        f"{num_space}PSALM RESPONSORYJNY",
        font=fnt_b_psalm,
        fill="red",
        anchor="lm",
    )
    draw.text(
        (1000, y_further_distance * 2),
        content_dic[psalm_key][0],
        font=fnt_b_psalm,
        fill="red",
        anchor="rm",
    )

    # Draw refrain
    draw.text(
        (x_distance, y_further_distance * 4),
        "Refren: ",
        font=fnt_b_psalm,
        fill="red",
        anchor="lm",
    )
    refrain_text = content_dic[psalm_key][1][7:] if content_dic[psalm_key][1].startswith("Refren") else content_dic[psalm_key][1]
    draw.text(
        (x_distance * 3, y_further_distance * 4),
        refrain_text,
        font=fnt_b_psalm,
        fill="black",
        anchor="lm",
    )

    y_text = y_further_distance * 6
    final_y_text = y_text

    for count, element in enumerate(content_dic[psalm_key][2:]):
        if "Refren" in element:
            draw.text((x_distance, y_text), "Refren: ", font=fnt_b_psalm, fill="red", anchor="lm")
            draw.text(
                (x_distance * 3, y_text),
                refrain_text,
                font=fnt_b_psalm,
                fill="black",
                anchor="lm",
            )
            y_text += y_further_distance

        elif "ŚPIEW PRZED EWANGELIĄ" in element:
            # Handle acclamation before Gospel
            acclamation = content_dic[psalm_key][count + 2 :]

            # Fix acclamation format if needed
            if not any(char.isdigit() for char in acclamation[1]):
                acclamation.insert(1, "")
            if len(acclamation) > 2 and "Aklamacja" in acclamation[2]:
                acclamation[2] = acclamation[2][10:]

            draw.text(
                (x_distance, y_text),
                "AKLAMACJA PRZED EWANGELIĄ",
                font=fnt_b_psalm,
                fill="red",
                anchor="lm",
            )
            if len(acclamation) > 1:
                draw.text(
                    (1000, y_text),
                    acclamation[1],
                    font=fnt_b_psalm,
                    fill="red",
                    anchor="rm",
                )

            if len(acclamation) > 2:
                draw.text(
                    (x_distance, y_text + y_further_distance * 2),
                    "Aklamacja: ",
                    font=fnt_b_psalm,
                    fill="red",
                    anchor="lm",
                )
                draw.text(
                    (x_distance * 4, y_text + y_further_distance * 2),
                    acclamation[2],
                    font=fnt_b_psalm,
                    fill="black",
                    anchor="lm",
                )

            # Draw acclamation text with wrapping if needed
            if len(acclamation) > 3:
                if len(acclamation[3]) > 50:
                    words = textwrap.wrap(acclamation[3], width=50)
                    draw.text(
                        (x_distance * 2, y_text + y_further_distance * 3 + y_distance),
                        words[0],
                        font=fnt_psalm,
                        fill="black",
                        anchor="lm",
                    )
                    if len(words) > 1:
                        draw.text(
                            (x_distance * 2, y_text + y_further_distance * 4 + y_distance),
                            words[1],
                            font=fnt_psalm,
                            fill="black",
                            anchor="lm",
                        )
                else:
                    draw.text(
                        (x_distance * 2, y_text + y_further_distance * 3 + y_distance),
                        acclamation[3],
                        font=fnt_psalm,
                        fill="black",
                        anchor="lm",
                    )

            if len(acclamation) > 4:
                draw.text(
                    (x_distance * 2, y_text + y_further_distance * 5 + y_distance),
                    acclamation[4],
                    font=fnt_psalm,
                    fill="black",
                    anchor="lm",
                )

            # Final acclamation
            if len(acclamation) > 2:
                draw.text(
                    (x_distance, y_text + y_further_distance * 7 + y_distance),
                    "Aklamacja: ",
                    font=fnt_b_psalm,
                    fill="red",
                    anchor="lm",
                )
                draw.text(
                    (x_distance * 4, y_text + y_further_distance * 7 + y_distance),
                    acclamation[2],
                    font=fnt_b_psalm,
                    fill="black",
                    anchor="lm",
                )

            final_y_text = y_text + y_further_distance * 7 + y_distance
            break

        elif "albo" in element:
            # Skip alternative readings
            continue

        else:
            draw.text(
                (x_distance * 2, y_text),
                element,
                font=fnt_psalm,
                fill="black",
                anchor="lm",
            )

        y_text += y_distance
        final_y_text = y_text

    return {"drawn_y": final_y_text, "picture": out}
