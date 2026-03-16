"""
Tests for draw_posts.py module.
"""

import pytest
from unittest.mock import patch, MagicMock

from draw_posts import (
    PageType,
    _calculate_layout,
    _load_fonts,
    draw_text,
    draw_text_page,
    draw_psalm,
    draw_text_pagination_first,
    draw_text_pagination_middle,
    draw_text_pagination_second,
)


class TestPageType:
    """Tests for PageType enum."""

    def test_enum_values(self):
        assert PageType.SINGLE.value == "single"
        assert PageType.FIRST.value == "first"
        assert PageType.MIDDLE.value == "middle"
        assert PageType.LAST.value == "last"

    def test_enum_members(self):
        members = list(PageType)
        assert len(members) == 4


class TestCalculateLayout:
    """Tests for _calculate_layout function."""

    def test_returns_dict_with_required_keys(self):
        result = _calculate_layout(44)

        assert "size_x_left" in result
        assert "size_x_right" in result
        assert "size_y" in result
        assert "width" in result
        assert "image_size" in result

    def test_layout_scales_with_font_size(self):
        small = _calculate_layout(30)
        large = _calculate_layout(50)

        assert small["size_x_left"] < large["size_x_left"]
        assert small["size_y"] < large["size_y"]

    def test_image_size_constant(self):
        result = _calculate_layout(44)
        assert result["image_size"] == 1080

    def test_default_font_size_layout(self):
        result = _calculate_layout(44)

        assert result["size_x_left"] > 0
        assert result["size_x_right"] > 0
        assert result["size_y"] > 0
        assert result["width"] > 0


class TestLoadFonts:
    """Tests for _load_fonts function."""

    @patch("draw_posts.ImageFont.truetype")
    def test_returns_three_fonts(self, mock_truetype):
        mock_font = MagicMock()
        mock_truetype.return_value = mock_font

        result = _load_fonts(44)

        assert len(result) == 3

    @patch("draw_posts.ImageFont.truetype")
    def test_loads_fonts_with_correct_sizes(self, mock_truetype):
        mock_font = MagicMock()
        mock_truetype.return_value = mock_font

        _load_fonts(44)

        # Should be called for regular, bold, and small fonts
        assert mock_truetype.call_count >= 3

    @patch("draw_posts.ImageFont.truetype")
    def test_falls_back_on_oserror(self, mock_truetype):
        mock_truetype.side_effect = OSError("Font not found")

        with patch("draw_posts.ImageFont.load_default") as mock_default:
            mock_default.return_value = MagicMock()
            result = _load_fonts(44)

            assert len(result) == 3


class TestDrawText:
    """Tests for draw_text function."""

    @patch("draw_posts.ImageDraw.Draw")
    @patch("draw_posts._load_fonts")
    def test_returns_dict_with_picture_and_y(self, mock_load_fonts, mock_draw_class, sample_background_image, sample_content_dict):
        mock_font = MagicMock()
        mock_load_fonts.return_value = (mock_font, mock_font, mock_font)
        mock_draw = MagicMock()
        mock_draw.textlength.return_value = 50
        mock_draw_class.return_value = mock_draw

        result = draw_text(
            sample_content_dict,
            sample_background_image,
            "PIERWSZE CZYTANIE",
            44
        )

        assert "drawn_y" in result
        assert "picture" in result

    @patch("draw_posts.ImageDraw.Draw")
    @patch("draw_posts._load_fonts")
    def test_returns_image(self, mock_load_fonts, mock_draw_class, sample_background_image, sample_content_dict):
        mock_font = MagicMock()
        mock_load_fonts.return_value = (mock_font, mock_font, mock_font)
        mock_draw = MagicMock()
        mock_draw.textlength.return_value = 50
        mock_draw_class.return_value = mock_draw

        result = draw_text(
            sample_content_dict,
            sample_background_image,
            "PIERWSZE CZYTANIE",
            44
        )

        assert result["picture"].size == (1080, 1080)


class TestDrawTextPage:
    """Tests for draw_text_page function."""

    @patch("draw_posts.ImageDraw.Draw")
    @patch("draw_posts._load_fonts")
    def test_first_page_type(self, mock_load_fonts, mock_draw_class, sample_background_image):
        mock_font = MagicMock()
        mock_load_fonts.return_value = (mock_font, mock_font, mock_font)
        mock_draw = MagicMock()
        mock_draw.textlength.return_value = 50
        mock_draw_class.return_value = mock_draw

        reading_list = ["TITLE", "Reference", "Subtitle", "Intro", "Content"]
        result = draw_text_page(sample_background_image, reading_list, PageType.FIRST, 44)

        assert "drawn_y" in result
        assert "picture" in result

    @patch("draw_posts.ImageDraw.Draw")
    @patch("draw_posts._load_fonts")
    def test_middle_page_type(self, mock_load_fonts, mock_draw_class, sample_background_image):
        mock_font = MagicMock()
        mock_load_fonts.return_value = (mock_font, mock_font, mock_font)
        mock_draw = MagicMock()
        mock_draw.textlength.return_value = 50
        mock_draw_class.return_value = mock_draw

        reading_list = ["Content line 1", "Content line 2"]
        result = draw_text_page(sample_background_image, reading_list, PageType.MIDDLE, 44)

        assert "drawn_y" in result
        assert "picture" in result

    @patch("draw_posts.ImageDraw.Draw")
    @patch("draw_posts._load_fonts")
    def test_last_page_type(self, mock_load_fonts, mock_draw_class, sample_background_image):
        mock_font = MagicMock()
        mock_load_fonts.return_value = (mock_font, mock_font, mock_font)
        mock_draw = MagicMock()
        mock_draw.textlength.return_value = 50
        mock_draw_class.return_value = mock_draw

        reading_list = ["Content", "Oto słowo Pańskie."]
        result = draw_text_page(sample_background_image, reading_list, PageType.LAST, 44)

        assert "drawn_y" in result
        assert "picture" in result


class TestDrawPsalm:
    """Tests for draw_psalm function."""

    @patch("draw_posts.ImageDraw.Draw")
    @patch("draw_posts._load_fonts")
    def test_returns_dict_with_picture(self, mock_load_fonts, mock_draw_class, sample_background_image, sample_content_dict):
        mock_font = MagicMock()
        mock_load_fonts.return_value = (mock_font, mock_font, mock_font)
        mock_draw = MagicMock()
        mock_draw.textlength.return_value = 50
        mock_draw_class.return_value = mock_draw

        result = draw_psalm(sample_content_dict, sample_background_image, 34)

        assert "drawn_y" in result
        assert "picture" in result

    @patch("draw_posts.ImageDraw.Draw")
    @patch("draw_posts._load_fonts")
    def test_handles_psalm_with_number(self, mock_load_fonts, mock_draw_class, sample_background_image):
        mock_font = MagicMock()
        mock_load_fonts.return_value = (mock_font, mock_font, mock_font)
        mock_draw = MagicMock()
        mock_draw.textlength.return_value = 50
        mock_draw_class.return_value = mock_draw

        content_dict = {
            "1 PSALM RESPONSORYJNY": [
                "Ps 104",
                "Refren: Test",
                "Verse 1",
            ]
        }
        result = draw_psalm(content_dict, sample_background_image, 34, num=1)

        assert "picture" in result


class TestPaginationWrappers:
    """Tests for pagination wrapper functions."""

    @patch("draw_posts.draw_text_page")
    def test_pagination_first_calls_draw_text_page(self, mock_draw_text_page, sample_background_image):
        mock_draw_text_page.return_value = {"drawn_y": 100, "picture": sample_background_image}

        reading_list = ["Title", "Ref", "Sub", "Intro", "Content"]
        draw_text_pagination_first(sample_background_image, reading_list, font_size=44)

        mock_draw_text_page.assert_called_once()
        call_args = mock_draw_text_page.call_args
        assert call_args[0][2] == PageType.FIRST

    @patch("draw_posts.draw_text_page")
    def test_pagination_middle_calls_draw_text_page(self, mock_draw_text_page, sample_background_image):
        mock_draw_text_page.return_value = {"drawn_y": 100, "picture": sample_background_image}

        reading_list = ["Content 1", "Content 2"]
        draw_text_pagination_middle(sample_background_image, reading_list, font_size=44)

        mock_draw_text_page.assert_called_once()
        call_args = mock_draw_text_page.call_args
        assert call_args[0][2] == PageType.MIDDLE

    @patch("draw_posts.draw_text_page")
    def test_pagination_second_calls_draw_text_page(self, mock_draw_text_page, sample_background_image):
        mock_draw_text_page.return_value = {"drawn_y": 100, "picture": sample_background_image}

        reading_list = ["Content", "Ending"]
        draw_text_pagination_second(sample_background_image, reading_list, font_size=44)

        mock_draw_text_page.assert_called_once()
        call_args = mock_draw_text_page.call_args
        assert call_args[0][2] == PageType.LAST
