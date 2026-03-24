from __future__ import annotations

from .headers import BLOCK_SIZE


class BlockStream:
    def __init__(self, fp) -> None:
        self.fp = fp

    def read_block(self) -> bytes:
        block = self.fp.read(BLOCK_SIZE)
        if block and len(block) != BLOCK_SIZE:
            raise EOFError("truncated archive block")
        return block

    def read_exact(self, size: int) -> bytes:
        data = self.fp.read(size)
        if len(data) != size:
            raise EOFError("truncated archive payload")
        return data

    def skip_padding(self, size: int) -> None:
        padding = (-size) % BLOCK_SIZE
        if padding:
            ignored = self.fp.read(padding)
            if len(ignored) != padding:
                raise EOFError("truncated archive padding")
