from __future__ import annotations

from pathlib import PurePosixPath


def decode_member_path(raw_name: bytes) -> str:
    decoded = raw_name.split(b"\0", 1)[0].decode("utf-8", errors="surrogateescape")
    normalized = PurePosixPath(decoded)
    return normalized.as_posix()


def sanitize_destination(path: str) -> str:
    normalized = PurePosixPath(path).as_posix()
    if normalized.startswith("../") or normalized == "..":
        raise ValueError("path escapes extraction root")
    return normalized.lstrip("./")
