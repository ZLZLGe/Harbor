#!/bin/bash
set -euo pipefail

cd /workspace/text-normalizer

cat <<'EOF' > textnorm/normalizer.py
"""Utilities for preparing short display text."""

import re


def normalize_text(text: str) -> str:
    """Normalize user-facing labels before they are stored."""
    cleaned = text.replace("\u00a0", " ").strip()
    cleaned = re.sub(r"\s*[—–]\s*", " - ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned
EOF

cat <<'EOF' > tests/test_normalizer.py
import pytest

from textnorm.normalizer import normalize_text


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("  Monthly   Summary  ", "Monthly Summary"),
        ("Quarterly\nStatus", "Quarterly Status"),
        ("Client\u00a0Update", "Client Update"),
        ("Roadmap—Phase 2", "Roadmap - Phase 2"),
        ("Roadmap – Phase 2", "Roadmap - Phase 2"),
        ("Alpha\t\tBeta", "Alpha Beta"),
    ],
)
def test_normalize_text_normalizes_whitespace_and_unicode_dashes(raw, expected):
    assert normalize_text(raw) == expected


def test_normalize_text_leaves_existing_ascii_hyphen_spacing_alone():
    assert normalize_text("Q1 - update") == "Q1 - update"
EOF

mkdir -p artifacts
cat <<'EOF' > artifacts/normalizer-regression-notes.md
## Broken cases

The regression removed word boundaries when labels contained line breaks, and it did not normalize unicode dash variants back to the documented storage format.

## Test updates

I replaced the narrow tests with a parameterized regression set that covers repeated spaces, line breaks, tabs, non-breaking spaces, and both supported unicode dash characters.

## Implementation fix

The implementation now converts non-breaking spaces first, rewrites unicode dash variants to a space-padded ASCII hyphen, and collapses any remaining whitespace runs with a regex before returning the normalized label.
EOF
