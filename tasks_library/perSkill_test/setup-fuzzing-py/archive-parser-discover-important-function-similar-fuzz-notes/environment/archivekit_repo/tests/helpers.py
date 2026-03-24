from __future__ import annotations

from archivekit.headers import BLOCK_SIZE


def encode_octal(value: int, width: int) -> bytes:
    text = format(value, "o").encode("ascii")
    return text.rjust(width - 1, b"0") + b"\0"


def build_header(name: bytes, *, size: int, typeflag: bytes = b"0", prefix: bytes = b"") -> bytes:
    block = bytearray(BLOCK_SIZE)
    block[0 : len(name)] = name
    block[100:108] = encode_octal(0o644, 8)
    block[108:116] = encode_octal(1000, 8)
    block[116:124] = encode_octal(1000, 8)
    block[124:136] = encode_octal(size, 12)
    block[136:148] = encode_octal(0, 12)
    block[148:156] = b" " * 8
    block[156:157] = typeflag
    block[257:263] = b"ustar\0"
    block[263:265] = b"00"
    block[345 : 345 + len(prefix)] = prefix

    checksum = sum(block)
    block[148:156] = encode_octal(checksum, 8)
    return bytes(block)


def pad_payload(data: bytes) -> bytes:
    padding = (-len(data)) % BLOCK_SIZE
    return data + (b"\0" * padding)
