"""
Template-based Midjourney prompt generator.

Generates prompts based on reading themes using templates.
User can edit the generated prompt before sending to Midjourney.
"""

import logging
import random
from typing import List, Optional

logger = logging.getLogger(__name__)

# Artistic style templates for sacred art
STYLE_TEMPLATES = [
    "sacred Renaissance painting style, divine light, golden hues",
    "Byzantine icon style, gold leaf, ethereal atmosphere",
    "Baroque religious art, dramatic chiaroscuro, emotional",
    "Pre-Raphaelite sacred art, rich colors, detailed",
    "classical Catholic art, reverent, painterly brushstrokes",
]

# Atmosphere/mood templates
ATMOSPHERE_TEMPLATES = [
    "divine radiance, heavenly glow, peaceful",
    "mystical fog, soft golden light, serene",
    "dramatic sky, rays of sunlight, majestic",
    "warm candlelight, intimate, contemplative",
    "ethereal clouds, celestial, transcendent",
]

# Base prompt structure
BASE_PROMPT_TEMPLATE = "{subject}, {style}, {atmosphere}, sacred Catholic liturgical art --ar 4:5 --v 6"


def extract_theme_keywords(reading_text: str) -> List[str]:
    """
    Extract potential visual themes from reading text.

    This is a simple keyword extraction - looks for common biblical imagery.
    """
    # Common biblical/liturgical themes and their visual representations
    theme_mappings = {
        # People
        "Jezus": "Jesus Christ",
        "Chrystus": "Christ",
        "Maryja": "Virgin Mary",
        "Maria": "Virgin Mary",
        "apostoł": "apostle",
        "uczni": "disciples",
        "prorok": "prophet",

        # Places/settings
        "świątyni": "temple",
        "góra": "mountain",
        "pustyni": "desert",
        "morze": "sea",
        "niebo": "heaven",
        "ogrod": "garden",

        # Actions/events
        "modlitw": "prayer",
        "błogosław": "blessing",
        "uzdrow": "healing",
        "zmartwychwsta": "resurrection",
        "wniebowstąpi": "ascension",
        "chrzest": "baptism",
        "przemieni": "transfiguration",
        "ukrzyżowan": "crucifixion",

        # Objects/symbols
        "chleb": "bread",
        "wino": "wine",
        "krzyż": "cross",
        "światł": "divine light",
        "ogień": "holy fire",
        "gołębic": "dove",
        "barank": "lamb",
        "korona": "crown",

        # Concepts
        "miłoś": "love",
        "wiar": "faith",
        "nadziej": "hope",
        "łask": "grace",
        "zbawien": "salvation",
        "pokój": "peace",
    }

    text_lower = reading_text.lower()
    found_themes = []

    for polish_key, english_theme in theme_mappings.items():
        if polish_key in text_lower:
            if english_theme not in found_themes:
                found_themes.append(english_theme)

    return found_themes[:5]  # Limit to 5 themes


def generate_midjourney_prompt(
    reading_text: str,
    reading_name: str,
    additional_context: Optional[str] = None,
) -> str:
    """
    Generate a Midjourney prompt from a Bible reading using templates.

    Args:
        reading_text: The full text of the reading
        reading_name: Name of the reading (e.g., "EWANGELIA", "PIERWSZE CZYTANIE")
        additional_context: Optional extra context

    Returns:
        A Midjourney-ready prompt string
    """
    # Extract themes from text
    themes = extract_theme_keywords(reading_text)

    if themes:
        subject = ", ".join(themes[:3])
    else:
        # Default subjects based on reading type
        if "EWANGELIA" in reading_name:
            subject = "Jesus Christ teaching, disciples listening"
        elif "PSALM" in reading_name:
            subject = "King David, harp, divine praise"
        else:
            subject = "biblical scene, prophets, sacred scripture"

    # Select random style and atmosphere
    style = random.choice(STYLE_TEMPLATES)
    atmosphere = random.choice(ATMOSPHERE_TEMPLATES)

    prompt = BASE_PROMPT_TEMPLATE.format(
        subject=subject,
        style=style,
        atmosphere=atmosphere,
    )

    logger.debug(f"Generated prompt: {prompt}")
    return prompt


def generate_prompt_variations(
    reading_text: str,
    reading_name: str,
    num_variations: int = 3,
) -> List[str]:
    """
    Generate multiple prompt variations for user to choose from.

    Args:
        reading_text: The full text of the reading
        reading_name: Name of the reading
        num_variations: Number of variations to generate

    Returns:
        List of Midjourney prompt strings
    """
    themes = extract_theme_keywords(reading_text)

    if not themes:
        if "EWANGELIA" in reading_name:
            themes = ["Jesus Christ", "disciples", "teaching"]
        elif "PSALM" in reading_name:
            themes = ["King David", "worship", "divine praise"]
        else:
            themes = ["biblical prophet", "sacred scroll", "divine message"]

    prompts = []

    # Generate variations with different style/atmosphere combinations
    used_styles = set()
    used_atmospheres = set()

    for i in range(num_variations):
        # Get unique style
        available_styles = [s for s in STYLE_TEMPLATES if s not in used_styles]
        if not available_styles:
            available_styles = STYLE_TEMPLATES
        style = random.choice(available_styles)
        used_styles.add(style)

        # Get unique atmosphere
        available_atmospheres = [a for a in ATMOSPHERE_TEMPLATES if a not in used_atmospheres]
        if not available_atmospheres:
            available_atmospheres = ATMOSPHERE_TEMPLATES
        atmosphere = random.choice(available_atmospheres)
        used_atmospheres.add(atmosphere)

        # Vary the subject slightly
        if len(themes) > 2:
            subject_themes = random.sample(themes, min(3, len(themes)))
        else:
            subject_themes = themes

        subject = ", ".join(subject_themes)

        prompt = BASE_PROMPT_TEMPLATE.format(
            subject=subject,
            style=style,
            atmosphere=atmosphere,
        )

        prompts.append(prompt)

    return prompts


def get_simple_prompt_template() -> str:
    """
    Return a simple editable prompt template for manual entry.
    """
    return "sacred Catholic art, [YOUR SUBJECT HERE], Renaissance painting style, divine light, ethereal atmosphere --ar 4:5 --v 6"
