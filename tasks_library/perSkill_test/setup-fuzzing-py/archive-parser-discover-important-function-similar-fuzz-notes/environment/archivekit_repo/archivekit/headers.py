from __future__ import annotations

BLOCK_SIZE = 512


def _compute_checksum(block: bytes) -> int:
    if len(block) != BLOCK_SIZE:
        raise ValueError("header blocks must be exactly 512 bytes")

    masked = bytearray(block)
    masked[148:156] = b" " * 8
    return sum(masked)


def _parse_numeric_field(field: bytes, *, allow_empty: bool = False) -> int:
    field = field.rstrip(b"\0 ")
    if not field:
        if allow_empty:
            return 0
        raise ValueError("empty numeric field")

    # TAR allows base-256 values when the high bit is set.
    if field[0] & 0x80:
        raw = bytes([field[0] & 0x7F]) + field[1:]
        return int.from_bytes(raw, "big", signed=True)

    text = field.decode("ascii")
    if any(ch not in "01234567" for ch in text):
        raise ValueError(f"invalid octal value: {text!r}")
    return int(text, 8)


def parse_header_block(block: bytes) -> dict[str, object]:
    if len(block) != BLOCK_SIZE:
        raise ValueError("header blocks must be exactly 512 bytes")

    checksum = _parse_numeric_field(block[148:156], allow_empty=True)
    expected_checksum = _compute_checksum(block)
    if checksum != expected_checksum:
        raise ValueError("header checksum mismatch")

    typeflag = chr(block[156] or ord("0"))
    name = block[0:100].split(b"\0", 1)[0]
    prefix = block[345:500].split(b"\0", 1)[0]
    if prefix:
        name = prefix + b"/" + name

    return {
        "name": name,
        "mode": _parse_numeric_field(block[100:108], allow_empty=True),
        "uid": _parse_numeric_field(block[108:116], allow_empty=True),
        "gid": _parse_numeric_field(block[116:124], allow_empty=True),
        "size": _parse_numeric_field(block[124:136], allow_empty=True),
        "mtime": _parse_numeric_field(block[136:148], allow_empty=True),
        "checksum": checksum,
        "typeflag": typeflag,
        "linkname": block[157:257].split(b"\0", 1)[0],
    }
