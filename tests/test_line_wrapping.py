"""Tests for line wrapping rules in draw_posts."""

from draw_posts import wrap_text


TEXT = (
    "Jezus powiedział do swoich uczniów: Idźcie i nauczajcie wszystkie narody "
    "— a Ja jestem z wami w każdym dniu aż do skończenia świata : i w domu „A teraz"
)


def _bad_ending(line: str) -> bool:
    last = line.split()[-1].lstrip("„\"'«(")
    return (len(last) == 1 and last.isalpha()) or not any(c.isalnum() for c in last)


class TestWrapText:
    def test_no_line_ends_with_one_letter_word_or_punctuation(self):
        for width in range(15, 60):
            lines = wrap_text(TEXT, width)
            assert all(not _bad_ending(line) for line in lines[:-1]), (width, lines)

    def test_keeps_all_words_in_order(self):
        for width in range(15, 60):
            assert " ".join(wrap_text(TEXT, width)) == " ".join(TEXT.split())

    def test_one_letter_word_moves_to_next_line(self):
        assert wrap_text("idźcie i nauczajcie", 8) == ["idźcie", "i nauczajcie"]

    def test_chained_one_letter_words_move_together(self):
        assert wrap_text("jestem a w domu", 10) == ["jestem", "a w domu"]

    def test_lone_dash_and_colon_move_to_next_line(self):
        assert wrap_text("narody — a Ja", 9) == ["narody", "— a Ja"]
        assert wrap_text("świata : koniec", 8) == ["świata", ": koniec"]

    def test_first_line_indent_shortens_first_line(self):
        assert wrap_text("aaaa bbbb cccc", 9, first_line_indent=5) == ["aaaa", "bbbb cccc"]

    def test_empty_text(self):
        assert wrap_text("", 20) == []
