#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RecordSpec:
    record_id: str
    length: int
    motif: str
    phase: int


SHORT_ALPHA_SPECS = [
    RecordSpec(
        record_id=f"alpha-read-{index:03d}",
        length=108 + (index % 6) * 11 + (index % 5) * 7,
        motif=("ACGTGCTA", "GGCATACC", "TTAGCGGA", "CCGTAAGT")[index % 4],
        phase=(index * 3) % 17,
    )
    for index in range(160)
]

SHORT_BETA_SPECS = [
    RecordSpec(
        record_id=f"beta-read-{index:03d}",
        length=116 + (index % 7) * 13 + (index % 4) * 9,
        motif=("TGCATGCA", "AACCGGTT", "GTATCGCA", "CGTTAAGC")[index % 4],
        phase=(index * 5) % 19,
    )
    for index in range(160)
]

ULTRA_SPECS = [
    RecordSpec("ultra-contig-00", 920_000, "ACGTACCGTTAGGCTA", 3),
    RecordSpec("ultra-contig-01", 860_000, "TTGCAAGGCCGTATCA", 7),
    RecordSpec("ultra-contig-02", 780_000, "CGATGCTTAGCGATGC", 11),
    RecordSpec("ultra-contig-03", 720_000, "GGCATTAACCGTGGCA", 5),
]

FILE_LAYOUT = [
    ("reads_alpha.fasta", SHORT_ALPHA_SPECS),
    ("reads_beta.fasta", SHORT_BETA_SPECS),
    ("ultra_fragments.fasta", ULTRA_SPECS),
]


def synthesize_sequence(length: int, motif: str, phase: int) -> str:
    bases = []
    motif_length = len(motif)
    for position in range(length):
        base = motif[(position + phase) % motif_length]
        if position % 97 == 0:
            base = "ACGT"[(phase + position // 97) % 4]
        elif position % 53 == 0:
            base = "TGCA"[(phase + position // 53) % 4]
        elif position % 31 == 0:
            base = "CATG"[(phase + position // 31) % 4]
        bases.append(base)
    return "".join(bases)


def wrap_fasta(sequence: str, width: int = 80) -> str:
    return "\n".join(sequence[start : start + width] for start in range(0, len(sequence), width))


def manifest_payload(root: str = "/root/workspace") -> dict:
    workspace = Path(root)
    genome_dir = workspace / "genomes"
    files = []
    total_sequences = 0
    total_bases = 0

    for file_name, specs in FILE_LAYOUT:
        total_sequences += len(specs)
        total_bases += sum(spec.length for spec in specs)
        files.append(
            {
                "path": str(genome_dir / file_name),
                "records": len(specs),
                "bases": sum(spec.length for spec in specs),
            }
        )

    return {
        "default_k": 6,
        "files": files,
        "total_sequences": total_sequences,
        "total_bases": total_bases,
    }
