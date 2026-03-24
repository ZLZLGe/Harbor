from __future__ import annotations

from archivekit.filters import decode_member_path, sanitize_destination


def test_decode_member_path_strips_null_padding() -> None:
    assert decode_member_path(b"./docs/readme.txt\0ignored") == "docs/readme.txt"


def test_sanitize_destination_rejects_parent_escape() -> None:
    try:
        sanitize_destination("../secrets.txt")
    except ValueError:
        return
    raise AssertionError("sanitize_destination should reject parent traversal")
