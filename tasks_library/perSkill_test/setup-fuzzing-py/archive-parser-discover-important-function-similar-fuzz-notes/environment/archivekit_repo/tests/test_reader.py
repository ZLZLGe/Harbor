from __future__ import annotations

from io import BytesIO

from archivekit.reader import open_archive

from .helpers import build_header, pad_payload


def _make_archive() -> bytes:
    pax_payload = b"23 path=docs/guide.txt\n"
    file_payload = b"content\n"

    pax_header = build_header(b"pax", size=len(pax_payload), typeflag=b"x")
    file_header = build_header(b"guide.txt", size=len(file_payload))
    end = b"\0" * 1024
    return b"".join(
        [
            pax_header,
            pad_payload(pax_payload),
            file_header,
            pad_payload(file_payload),
            end,
        ]
    )


def test_iter_entries_applies_pax_headers() -> None:
    reader = open_archive(BytesIO(_make_archive()))
    entries = list(reader.iter_entries())

    assert len(entries) == 1
    assert entries[0].path == "guide.txt"
    assert entries[0].metadata["path"] == "docs/guide.txt"
    assert entries[0].payload == b"content\n"
