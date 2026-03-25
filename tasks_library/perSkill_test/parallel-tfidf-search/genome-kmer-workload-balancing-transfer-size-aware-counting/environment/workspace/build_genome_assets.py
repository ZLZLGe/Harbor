#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path

from genome_fixture import FILE_LAYOUT, manifest_payload, synthesize_sequence, wrap_fasta


def main(root: str = "/root/workspace") -> None:
    workspace = Path(root)
    genome_dir = workspace / "genomes"
    genome_dir.mkdir(parents=True, exist_ok=True)

    for file_name, specs in FILE_LAYOUT:
        output_path = genome_dir / file_name
        with output_path.open("w", encoding="utf-8") as handle:
            for spec in specs:
                sequence = synthesize_sequence(spec.length, spec.motif, spec.phase)
                handle.write(f">{spec.record_id}\n")
                handle.write(wrap_fasta(sequence))
                handle.write("\n")

    manifest = manifest_payload(root)
    manifest_path = workspace / "genome_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    main()
