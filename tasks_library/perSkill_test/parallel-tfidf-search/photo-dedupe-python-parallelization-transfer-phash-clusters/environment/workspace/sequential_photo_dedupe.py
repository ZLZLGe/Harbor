#!/usr/bin/env python3
"""
Sequential perceptual-hash photo dedupe baseline.
"""

from __future__ import annotations

import argparse
import math
import time
from dataclasses import dataclass, field

from photo_fixture import basename_id, discover_photo_paths, hamming_distance, read_pgm, resize_to_square


@dataclass(frozen=True)
class PhotoHashRecord:
    photo_id: str
    path: str
    hash_bits: str
    hash_value: int
    width: int
    height: int
    mean_luma: float


@dataclass
class PhotoHashIndex:
    hash_size: int
    photo_records: list[PhotoHashRecord] = field(default_factory=list)
    photo_lookup: dict[str, PhotoHashRecord] = field(default_factory=dict)


@dataclass(frozen=True)
class DuplicateCluster:
    cluster_id: str
    members: list[str]
    anchor: str
    average_distance: float
    max_distance: int


@dataclass
class BuildResult:
    index: PhotoHashIndex
    elapsed_time: float
    num_photos: int
    hash_size: int


_DCT_BASIS_CACHE: dict[int, list[list[float]]] = {}


def _dct_basis(size: int) -> list[list[float]]:
    basis = _DCT_BASIS_CACHE.get(size)
    if basis is not None:
        return basis

    generated: list[list[float]] = []
    for frequency in range(size):
        scale = math.sqrt(1.0 / size) if frequency == 0 else math.sqrt(2.0 / size)
        generated.append(
            [
                scale * math.cos((math.pi * (2 * sample + 1) * frequency) / (2.0 * size))
                for sample in range(size)
            ]
        )

    _DCT_BASIS_CACHE[size] = generated
    return generated


def _low_frequency_dct(resized_pixels: list[list[float]], hash_size: int, highfreq_factor: int = 4) -> list[list[float]]:
    size = hash_size * highfreq_factor
    basis = _dct_basis(size)
    coefficients: list[list[float]] = []

    for row_frequency in range(hash_size):
        row_basis = basis[row_frequency]
        coeff_row: list[float] = []
        for col_frequency in range(hash_size):
            col_basis = basis[col_frequency]
            total = 0.0
            for row_index in range(size):
                weighted_row = row_basis[row_index]
                row = resized_pixels[row_index]
                subtotal = 0.0
                for col_index in range(size):
                    subtotal += row[col_index] * col_basis[col_index]
                total += weighted_row * subtotal
            coeff_row.append(total)
        coefficients.append(coeff_row)

    return coefficients


def compute_perceptual_hash(photo_path: str, hash_size: int = 8) -> PhotoHashRecord:
    pixels = read_pgm(photo_path)
    resized = resize_to_square(pixels, hash_size * 4)
    coefficients = _low_frequency_dct(resized, hash_size=hash_size, highfreq_factor=4)

    flattened = [value for row in coefficients for value in row]
    median_source = flattened[1:] if len(flattened) > 1 else flattened
    threshold = sorted(median_source)[len(median_source) // 2] if median_source else 0.0
    hash_bits = "".join("1" if value >= threshold else "0" for value in flattened)
    mean_luma = round(sum(sum(row) for row in resized) / (len(resized) * len(resized[0])), 3)

    return PhotoHashRecord(
        photo_id=basename_id(photo_path),
        path=photo_path,
        hash_bits=hash_bits,
        hash_value=int(hash_bits, 2) if hash_bits else 0,
        width=len(pixels[0]) if pixels else 0,
        height=len(pixels),
        mean_luma=mean_luma,
    )


def build_photo_index_sequential(album_dir: str, hash_size: int = 8) -> BuildResult:
    start = time.perf_counter()
    photo_paths = discover_photo_paths(album_dir)
    records = [compute_perceptual_hash(photo_path, hash_size=hash_size) for photo_path in photo_paths]
    index = PhotoHashIndex(
        hash_size=hash_size,
        photo_records=records,
        photo_lookup={record.photo_id: record for record in records},
    )
    return BuildResult(
        index=index,
        elapsed_time=time.perf_counter() - start,
        num_photos=len(records),
        hash_size=hash_size,
    )


def cluster_duplicate_records(
    index: PhotoHashIndex,
    max_hamming_distance: int = 18,
    min_cluster_size: int = 2,
) -> list[DuplicateCluster]:
    parent = list(range(len(index.photo_records)))

    def find(node: int) -> int:
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    def union(left: int, right: int) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    for left in range(len(index.photo_records)):
        left_record = index.photo_records[left]
        for right in range(left + 1, len(index.photo_records)):
            right_record = index.photo_records[right]
            distance = hamming_distance(left_record.hash_value, right_record.hash_value)
            if distance <= max_hamming_distance:
                union(left, right)

    grouped_indices: dict[int, list[int]] = {}
    for record_index in range(len(index.photo_records)):
        grouped_indices.setdefault(find(record_index), []).append(record_index)

    clusters: list[DuplicateCluster] = []
    cluster_number = 1
    for member_indices in sorted(grouped_indices.values(), key=lambda group: index.photo_records[group[0]].photo_id):
        if len(member_indices) < min_cluster_size:
            continue

        member_ids = sorted(index.photo_records[member_index].photo_id for member_index in member_indices)
        distances: list[int] = []
        for left_offset, left_index in enumerate(member_indices):
            for right_index in member_indices[left_offset + 1 :]:
                distances.append(
                    hamming_distance(
                        index.photo_records[left_index].hash_value,
                        index.photo_records[right_index].hash_value,
                    )
                )

        average_distance = round(sum(distances) / len(distances), 3) if distances else 0.0
        max_distance = max(distances) if distances else 0
        clusters.append(
            DuplicateCluster(
                cluster_id=f"cluster-{cluster_number:03d}",
                members=member_ids,
                anchor=member_ids[0],
                average_distance=average_distance,
                max_distance=max_distance,
            )
        )
        cluster_number += 1

    return clusters


def build_duplicate_report(
    index: PhotoHashIndex,
    clusters: list[DuplicateCluster],
    elapsed_time: float,
    max_hamming_distance: int,
    num_workers: int,
    chunk_size: int,
) -> dict:
    duplicate_member_count = sum(len(cluster.members) for cluster in clusters)
    return {
        "total_photos": len(index.photo_records),
        "hash_size": index.hash_size,
        "requested_workers": num_workers,
        "chunk_size": chunk_size,
        "max_hamming_distance": max_hamming_distance,
        "elapsed_time": round(elapsed_time, 6),
        "ordered_photo_ids": [record.photo_id for record in index.photo_records],
        "cluster_count": len(clusters),
        "duplicate_photo_count": duplicate_member_count,
        "unique_photo_count": len(index.photo_records) - duplicate_member_count,
        "clusters": [
            {
                "cluster_id": cluster.cluster_id,
                "anchor": cluster.anchor,
                "members": cluster.members,
                "size": len(cluster.members),
                "average_distance": cluster.average_distance,
                "max_distance": cluster.max_distance,
            }
            for cluster in clusters
        ],
    }


def run_photo_dedupe_sequential(
    album_dir: str,
    hash_size: int = 8,
    max_hamming_distance: int = 18,
) -> dict:
    build_result = build_photo_index_sequential(album_dir, hash_size=hash_size)
    clusters = cluster_duplicate_records(build_result.index, max_hamming_distance=max_hamming_distance)
    return build_duplicate_report(
        build_result.index,
        clusters,
        elapsed_time=build_result.elapsed_time,
        max_hamming_distance=max_hamming_distance,
        num_workers=1,
        chunk_size=len(build_result.index.photo_records) or 1,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Sequential perceptual-hash photo dedupe baseline")
    parser.add_argument("album_dir", type=str, help="Directory containing .pgm photos")
    parser.add_argument("--hash-size", type=int, default=8)
    parser.add_argument("--distance", type=int, default=18)
    args = parser.parse_args()

    report = run_photo_dedupe_sequential(
        args.album_dir,
        hash_size=args.hash_size,
        max_hamming_distance=args.distance,
    )
    print(report)


if __name__ == "__main__":
    main()
