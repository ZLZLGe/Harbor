from __future__ import annotations

from dataclasses import dataclass

from .filters import decode_member_path
from .headers import parse_header_block
from .metadata import parse_extended_headers
from .stream import BlockStream


@dataclass
class ArchiveEntry:
    path: str
    size: int
    typeflag: str
    metadata: dict[str, object]
    payload: bytes


class ArchiveReader:
    def __init__(self, fp) -> None:
        self.stream = BlockStream(fp)

    def iter_entries(self):
        pending_headers: dict[str, str] = {}

        while True:
            block = self.stream.read_block()
            if not block or block == b"\0" * len(block):
                return

            header = parse_header_block(block)
            size = int(header["size"])
            payload = self.stream.read_exact(size)
            self.stream.skip_padding(size)

            if header["typeflag"] == "x":
                pending_headers = parse_extended_headers(payload)
                continue

            metadata = dict(header)
            metadata.update(pending_headers)
            pending_headers = {}
            yield ArchiveEntry(
                path=decode_member_path(header["name"]),
                size=size,
                typeflag=str(header["typeflag"]),
                metadata=metadata,
                payload=payload,
            )


def open_archive(fp) -> ArchiveReader:
    return ArchiveReader(fp)
