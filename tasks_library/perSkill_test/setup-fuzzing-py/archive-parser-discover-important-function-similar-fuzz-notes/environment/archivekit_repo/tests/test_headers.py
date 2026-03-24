from __future__ import annotations

from archivekit.headers import _parse_numeric_field, parse_header_block

from .helpers import build_header


def test_parse_header_block_reads_basic_fields() -> None:
    block = build_header(b"docs/readme.txt", size=7)
    parsed = parse_header_block(block)

    assert parsed["name"] == b"docs/readme.txt"
    assert parsed["size"] == 7
    assert parsed["typeflag"] == "0"


def test_parse_numeric_field_supports_base256_values() -> None:
    field = bytes([0x80, 0, 0, 0, 0, 0, 0, 25])
    assert _parse_numeric_field(field) == 25
