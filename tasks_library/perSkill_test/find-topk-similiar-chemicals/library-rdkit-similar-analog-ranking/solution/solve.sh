#!/bin/bash

set -e

mkdir -p /root/workspace

cat > /root/workspace/analog_ranking.py <<'EOF'
#!/usr/bin/env python3

import csv
import json
from pathlib import Path

from rdkit import Chem
from rdkit import DataStructs
from rdkit.Chem import rdFingerprintGenerator


GENERATOR = rdFingerprintGenerator.GetMorganGenerator(
    radius=2,
    fpSize=2048,
    includeChirality=True,
)


def canonicalize_smiles(smiles):
    molecule = Chem.MolFromSmiles(smiles.strip())
    if molecule is None:
        raise ValueError(f"Could not parse SMILES: {smiles}")
    return Chem.MolToSmiles(molecule, canonical=True, isomericSmiles=True)


def load_target(target_record_path):
    payload = json.loads(Path(target_record_path).read_text())
    canonical_smiles = canonicalize_smiles(payload["smiles"])
    return {
        "target_name": payload["target_name"],
        "target_canonical_smiles": canonical_smiles,
        "top_k": int(payload["top_k"]),
    }


def load_library(library_csv_path):
    merged = {}
    with open(library_csv_path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            canonical_smiles = canonicalize_smiles(row["smiles"])
            names = merged.setdefault(canonical_smiles, set())
            names.add(row["compound_name"].strip())

    library = []
    for canonical_smiles, names in merged.items():
        aliases = sorted(names)
        library.append(
            {
                "name": aliases[0],
                "aliases": aliases,
                "canonical_smiles": canonical_smiles,
            }
        )
    return library


def fingerprint_from_smiles(smiles):
    molecule = Chem.MolFromSmiles(smiles)
    return GENERATOR.GetFingerprint(molecule)


def rank_similar_analogs(target_record_path, library_csv_path, top_k):
    target = load_target(target_record_path)
    target_fp = fingerprint_from_smiles(target["target_canonical_smiles"])

    ranked = []
    for entry in load_library(library_csv_path):
        candidate_fp = fingerprint_from_smiles(entry["canonical_smiles"])
        similarity = DataStructs.TanimotoSimilarity(target_fp, candidate_fp)
        ranked.append(
            {
                "name": entry["name"],
                "aliases": entry["aliases"],
                "canonical_smiles": entry["canonical_smiles"],
                "similarity": round(similarity, 4),
            }
        )

    ranked.sort(key=lambda item: (-item["similarity"], item["name"]))
    return ranked[:top_k]


def write_report(
    target_record_path="/root/compound_request.json",
    library_csv_path="/root/compound_library.csv",
    output_path="/root/workspace/analog_report.json",
):
    target = load_target(target_record_path)
    results = rank_similar_analogs(target_record_path, library_csv_path, target["top_k"])
    report = {
        "target_name": target["target_name"],
        "target_canonical_smiles": target["target_canonical_smiles"],
        "top_k": target["top_k"],
        "results": [
            {
                "rank": index,
                "name": entry["name"],
                "aliases": entry["aliases"],
                "canonical_smiles": entry["canonical_smiles"],
                "similarity": entry["similarity"],
            }
            for index, entry in enumerate(results, start=1)
        ],
    }
    Path(output_path).write_text(json.dumps(report, indent=2) + "\n")
    return report


def main():
    write_report()


if __name__ == "__main__":
    main()
EOF
