from textnorm.normalizer import normalize_text


def test_normalize_text_collapses_extra_spaces():
    assert normalize_text("  Monthly   Summary  ") == "Monthly Summary"


def test_normalize_text_keeps_words_separated_across_line_breaks():
    assert normalize_text("Quarterly\nStatus") == "Quarterly Status"
