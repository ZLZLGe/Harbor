"""Utilities for preparing short display text."""


_DASH_TRANSLATION = str.maketrans({"—": "-", "–": "-", "\u00a0": " "})


def normalize_text(text: str) -> str:
    """Normalize user-facing labels before they are stored."""
    cleaned = text.strip().translate(_DASH_TRANSLATION)
    cleaned = cleaned.replace("\n", "")
    cleaned = cleaned.replace("\t", " ")

    while "  " in cleaned:
        cleaned = cleaned.replace("  ", " ")

    return cleaned
