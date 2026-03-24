#!/usr/bin/env python3
"""
Helpers for generating deterministic archive fixtures with highly skewed file sizes.
"""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path


def _pattern_block(label: str) -> bytes:
    seed = hashlib.sha256(label.encode("utf-8")).digest()
    block = bytearray()
    current = seed
    while len(block) < 8192:
        block.extend(current)
        current = hashlib.sha256(current).digest()
    return bytes(block[:8192])


def write_deterministic_file(path: str | Path, size_bytes: int, label: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    block = _pattern_block(label)
    remaining = size_bytes
    with open(target, "wb") as handle:
        while remaining > 0:
            piece = block[: min(len(block), remaining)]
            handle.write(piece)
            remaining -= len(piece)


def build_skewed_archive(
    root_dir: str | Path,
    *,
    seed: int = 0,
    small_count: int = 180,
    medium_count: int = 18,
    large_count: int = 8,
    giant_count: int = 2,
) -> Path:
    root_path = Path(root_dir)
    if root_path.exists():
        shutil.rmtree(root_path)
    root_path.mkdir(parents=True, exist_ok=True)

    for index in range(small_count):
        size_bytes = 2_048 + ((seed * 17 + index * 977) % 9_216)
        path = root_path / "metadata" / f"batch_{index % 9:02d}" / f"record_{index:04d}.json"
        write_deterministic_file(path, size_bytes, f"small::{seed}::{index}")

    for index in range(medium_count):
        size_bytes = 192_000 + ((seed * 29 + index * 31_337) % 160_000)
        path = root_path / "indexes" / f"segment_{index % 4:02d}" / f"segment_{index:03d}.idx"
        write_deterministic_file(path, size_bytes, f"medium::{seed}::{index}")

    for index in range(large_count):
        size_bytes = 2_500_000 + ((seed * 53 + index * 181_111) % 1_700_000)
        path = root_path / "payloads" / f"set_{index % 3:02d}" / f"payload_{index:03d}.bin"
        write_deterministic_file(path, size_bytes, f"large::{seed}::{index}")

    for index in range(giant_count):
        size_bytes = 8_000_000 + ((seed * 71 + index * 919_191) % 2_500_000)
        path = root_path / "payloads" / "deep" / f"giant_{index:02d}.bin"
        write_deterministic_file(path, size_bytes, f"giant::{seed}::{index}")

    return root_path
