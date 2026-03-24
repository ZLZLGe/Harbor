#!/usr/bin/env python3
"""
Sequential archive checksum manifest builder used as the correctness baseline.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path


DEFAULT_BLOCK_SIZE = 256 * 1024


@dataclass(frozen=True)
class FileJob:
    index: int
    relative_path: str
    absolute_path: str
    size_bytes: int


@dataclass(frozen=True)
class ManifestEntry:
    relative_path: str
    size_bytes: int
    sha256: str
    block_digest: str


@dataclass
class ChecksumManifest:
    root_dir: str
    algorithm: str
    entries: list[ManifestEntry] = field(default_factory=list)
    total_files: int = 0
    total_size_bytes: int = 0


@dataclass
class ManifestBuildResult:
    manifest: ChecksumManifest
    elapsed_time: float
    num_files: int
    total_size_bytes: int


def discover_file_jobs(root_dir: str | Path) -> list[FileJob]:
    root_path = Path(root_dir).resolve()
    file_paths = sorted(path for path in root_path.rglob("*") if path.is_file())

    jobs: list[FileJob] = []
    for index, path in enumerate(file_paths):
        relative_path = path.relative_to(root_path).as_posix()
        jobs.append(
            FileJob(
                index=index,
                relative_path=relative_path,
                absolute_path=str(path),
                size_bytes=path.stat().st_size,
            )
        )
    return jobs


def hash_file(path: str | Path, block_size: int = DEFAULT_BLOCK_SIZE) -> tuple[str, str]:
    sha256_hasher = hashlib.sha256()
    block_hasher = hashlib.blake2b(digest_size=20)

    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(block_size)
            if not chunk:
                break
            sha256_hasher.update(chunk)
            block_hasher.update(hashlib.sha1(chunk).digest())

    return sha256_hasher.hexdigest(), block_hasher.hexdigest()


def build_checksum_manifest_sequential(
    root_dir: str | Path,
    algorithm: str = "sha256",
    block_size: int = DEFAULT_BLOCK_SIZE,
) -> ManifestBuildResult:
    if algorithm != "sha256":
        raise ValueError("Only sha256 manifests are supported in this task")

    start_time = time.perf_counter()
    jobs = discover_file_jobs(root_dir)

    entries: list[ManifestEntry] = []
    total_size_bytes = 0

    for job in jobs:
        sha256_digest, block_digest = hash_file(job.absolute_path, block_size=block_size)
        entries.append(
            ManifestEntry(
                relative_path=job.relative_path,
                size_bytes=job.size_bytes,
                sha256=sha256_digest,
                block_digest=block_digest,
            )
        )
        total_size_bytes += job.size_bytes

    manifest = ChecksumManifest(
        root_dir=str(Path(root_dir).resolve()),
        algorithm=algorithm,
        entries=entries,
        total_files=len(entries),
        total_size_bytes=total_size_bytes,
    )
    elapsed_time = time.perf_counter() - start_time
    return ManifestBuildResult(
        manifest=manifest,
        elapsed_time=elapsed_time,
        num_files=len(entries),
        total_size_bytes=total_size_bytes,
    )


def write_manifest_json(manifest: ChecksumManifest, output_path: str | Path) -> None:
    payload = {
        "root_dir": manifest.root_dir,
        "algorithm": manifest.algorithm,
        "total_files": manifest.total_files,
        "total_size_bytes": manifest.total_size_bytes,
        "entries": [asdict(entry) for entry in manifest.entries],
    }
    Path(output_path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a sequential archive checksum manifest.")
    parser.add_argument("root_dir", help="Archive directory to scan")
    parser.add_argument("--output", help="Optional JSON output path")
    args = parser.parse_args()

    result = build_checksum_manifest_sequential(args.root_dir)
    if args.output:
        write_manifest_json(result.manifest, args.output)
    else:
        print(json.dumps([asdict(entry) for entry in result.manifest.entries], indent=2))


if __name__ == "__main__":
    main()
