#!/usr/bin/env python3

import csv
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from rdkit import Chem
from rdkit import DataStructs
from rdkit.Chem import rdFingerprintGenerator


WORKSPACE_MODULE = Path("/root/workspace/analog_ranking.py")
TARGET_PATH = Path("/root/compound_request.json")
LIBRARY_PATH = Path("/root/compound_library.csv")
REPORT_PATH = Path("/root/workspace/analog_report.json")

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
    return {
        "target_name": payload["target_name"],
        "target_canonical_smiles": canonicalize_smiles(payload["smiles"]),
        "top_k": int(payload["top_k"]),
    }


def load_merged_library(library_csv_path):
    merged = {}
    with open(library_csv_path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            canonical_smiles = canonicalize_smiles(row["smiles"])
            aliases = merged.setdefault(canonical_smiles, set())
            aliases.add(row["compound_name"].strip())

    library = []
    for canonical_smiles, aliases in merged.items():
        sorted_aliases = sorted(aliases)
        library.append(
            {
                "name": sorted_aliases[0],
                "aliases": sorted_aliases,
                "canonical_smiles": canonical_smiles,
            }
        )
    return library


def fingerprint_from_smiles(smiles):
    return GENERATOR.GetFingerprint(Chem.MolFromSmiles(smiles))


def reference_rank(target_record_path, library_csv_path, top_k):
    target = load_target(target_record_path)
    target_fp = fingerprint_from_smiles(target["target_canonical_smiles"])

    ranked = []
    for entry in load_merged_library(library_csv_path):
        similarity = DataStructs.TanimotoSimilarity(
            target_fp,
            fingerprint_from_smiles(entry["canonical_smiles"]),
        )
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


def reference_report(target_record_path, library_csv_path):
    target = load_target(target_record_path)
    results = reference_rank(target_record_path, library_csv_path, target["top_k"])
    return {
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


def load_agent_module():
    if not WORKSPACE_MODULE.exists():
        raise FileNotFoundError("analog_ranking.py was not created")

    spec = importlib.util.spec_from_file_location("analog_ranking", WORKSPACE_MODULE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def assert_equal(actual, expected, label):
    if actual != expected:
        raise AssertionError(
            f"{label} mismatch\nExpected: {json.dumps(expected, indent=2)}\n"
            f"Actual: {json.dumps(actual, indent=2)}"
        )


def test_function_on_environment_assets(module):
    if not hasattr(module, "rank_similar_analogs"):
        raise AssertionError("rank_similar_analogs is missing")

    expected = reference_rank(TARGET_PATH, LIBRARY_PATH, 6)
    actual = module.rank_similar_analogs(str(TARGET_PATH), str(LIBRARY_PATH), 6)
    assert_equal(actual, expected, "environment ranking")

    top_entry = actual[0]
    if top_entry["aliases"] != ["Propanoic acid", "Propionic acid"]:
        raise AssertionError("duplicate merge for propionic acid is incorrect")


def test_function_on_temporary_assets(module):
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        target_path = tmp_path / "target.json"
        library_path = tmp_path / "library.csv"

        target_path.write_text(
            json.dumps(
                {
                    "target_name": "Acetic acid",
                    "smiles": "CC(=O)O",
                    "top_k": 4,
                }
            )
        )

        library_path.write_text(
            "\n".join(
                [
                    "compound_name,smiles,series",
                    "Acetic acid,CC(=O)O,A",
                    "Ethanoic acid,CC(=O)O,B",
                    "Propionic acid,CCC(=O)O,C",
                    "Glycolic acid,OCC(=O)O,D",
                    "Lactic acid (R),C[C@H](O)C(=O)O,E",
                    "Lactic acid (S),C[C@@H](O)C(=O)O,F",
                    "Ethanol,CCO,G",
                ]
            )
            + "\n"
        )

        expected = reference_rank(target_path, library_path, 4)
        actual = module.rank_similar_analogs(str(target_path), str(library_path), 4)
        assert_equal(actual, expected, "temporary ranking")


def test_script_report():
    subprocess.run(["python3", str(WORKSPACE_MODULE)], check=True)

    if not REPORT_PATH.exists():
        raise AssertionError("analog_report.json was not created")

    expected = reference_report(TARGET_PATH, LIBRARY_PATH)
    actual = json.loads(REPORT_PATH.read_text())
    assert_equal(actual, expected, "report output")


def calculate_score():
    tests = [
        ("function on environment assets", test_function_on_environment_assets),
        ("function on temporary assets", test_function_on_temporary_assets),
        ("script report", lambda module: test_script_report()),
    ]

    module = load_agent_module()
    passed = 0

    for label, test_fn in tests:
        print("=" * 70)
        print(f"Running test: {label}")
        print("=" * 70)
        try:
            test_fn(module)
            passed += 1
            print(f"[PASSED] {label}")
        except Exception as exc:
            print(f"[FAILED] {label}: {exc}")

    score = passed / len(tests)
    os.makedirs("/logs/verifier", exist_ok=True)
    Path("/logs/verifier/reward.txt").write_text(f"{score}\n")

    print("=" * 70)
    print(f"FINAL SCORE: {passed}/{len(tests)} = {score}")
    print("=" * 70)

    return score


if __name__ == "__main__":
    score = calculate_score()
    sys.exit(0 if score == 1.0 else 1)
