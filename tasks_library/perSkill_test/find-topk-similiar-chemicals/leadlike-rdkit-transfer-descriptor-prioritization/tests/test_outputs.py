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
from rdkit.Chem import Descriptors


WORKSPACE_MODULE = Path("/root/workspace/leadlike_prioritization.py")
LIBRARY_PATH = Path("/root/lead_batch.jsonl")
RULES_PATH = Path("/root/prioritization_rules.json")
REPORT_PATH = Path("/root/workspace/lead_prioritization_report.json")
QUEUE_PATH = Path("/root/workspace/follow_up_queue.tsv")

DESCRIPTOR_ORDER = [
    "molecular_weight",
    "logp",
    "tpsa",
    "hbd",
    "hba",
    "rotatable_bonds",
]


def load_candidates(candidate_library_path):
    candidates = []
    with open(candidate_library_path, encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if line:
                candidates.append(json.loads(line))
    return candidates


def load_rules(rules_path):
    return json.loads(Path(rules_path).read_text())


def canonicalize_smiles(smiles):
    molecule = Chem.MolFromSmiles(smiles)
    if molecule is None:
        raise ValueError(f"Could not parse SMILES: {smiles}")
    return Chem.MolToSmiles(molecule, canonical=True, isomericSmiles=True)


def descriptor_values(smiles):
    molecule = Chem.MolFromSmiles(smiles)
    if molecule is None:
        raise ValueError(f"Could not parse SMILES: {smiles}")
    return {
        "molecular_weight": round(Descriptors.MolWt(molecule), 2),
        "logp": round(Descriptors.MolLogP(molecule), 2),
        "tpsa": round(Descriptors.TPSA(molecule), 2),
        "hbd": int(Descriptors.NumHDonors(molecule)),
        "hba": int(Descriptors.NumHAcceptors(molecule)),
        "rotatable_bonds": int(Descriptors.NumRotatableBonds(molecule)),
    }


def in_range(value, range_config):
    return range_config["min"] <= value <= range_config["max"]


def decision_basis(preferred_matches, hard_failures):
    if hard_failures:
        return f"fails hard limits: {','.join(hard_failures)}"
    if preferred_matches:
        return f"passes hard limits; preferred matches: {','.join(preferred_matches)}"
    return "passes hard limits; preferred matches: none"


def review_candidate(candidate, rules):
    canonical_smiles = canonicalize_smiles(candidate["smiles"])
    descriptors = descriptor_values(canonical_smiles)

    preferred_matches = []
    hard_failures = []
    for descriptor_name in DESCRIPTOR_ORDER:
        value = descriptors[descriptor_name]
        if in_range(value, rules["preferred_ranges"][descriptor_name]):
            preferred_matches.append(descriptor_name)
        if not in_range(value, rules["hard_limits"][descriptor_name]):
            hard_failures.append(descriptor_name)

    return {
        "compound_id": candidate["compound_id"],
        "name": candidate["name"],
        "series": candidate["series"],
        "supplier": candidate["supplier"],
        "canonical_smiles": canonical_smiles,
        "descriptors": descriptors,
        "preferred_matches": preferred_matches,
        "hard_failures": hard_failures,
        "priority_score": len(preferred_matches),
        "decision": "advance" if not hard_failures else "reject",
        "decision_basis": decision_basis(preferred_matches, hard_failures),
    }


def reference_report(candidate_library_path, rules_path):
    rules = load_rules(rules_path)
    candidates = load_candidates(candidate_library_path)
    candidate_reviews = [review_candidate(candidate, rules) for candidate in candidates]

    advanced = [
        review
        for review in candidate_reviews
        if review["decision"] == "advance"
    ]
    advanced.sort(key=lambda review: (-review["priority_score"], review["compound_id"]))

    follow_up_queue = [
        {
            "rank": index,
            "compound_id": review["compound_id"],
            "name": review["name"],
            "priority_score": review["priority_score"],
            "canonical_smiles": review["canonical_smiles"],
            "preferred_matches": review["preferred_matches"],
        }
        for index, review in enumerate(advanced[: int(rules["top_n"])], start=1)
    ]

    return {
        "campaign": rules["campaign"],
        "ruleset_name": rules["ruleset_name"],
        "summary": {
            "total_candidates": len(candidate_reviews),
            "advanced_candidates": len(advanced),
            "rejected_candidates": len(candidate_reviews) - len(advanced),
            "queued_candidates": len(follow_up_queue),
        },
        "candidate_reviews": candidate_reviews,
        "follow_up_queue": follow_up_queue,
    }


def reference_queue_rows(candidate_library_path, rules_path):
    report = reference_report(candidate_library_path, rules_path)
    rows = []
    for entry in report["follow_up_queue"]:
        rows.append(
            {
                "rank": str(entry["rank"]),
                "compound_id": entry["compound_id"],
                "name": entry["name"],
                "priority_score": str(entry["priority_score"]),
                "preferred_matches": "|".join(entry["preferred_matches"]),
                "canonical_smiles": entry["canonical_smiles"],
            }
        )
    return rows


def load_agent_module():
    if not WORKSPACE_MODULE.exists():
        raise FileNotFoundError("leadlike_prioritization.py was not created")

    spec = importlib.util.spec_from_file_location(
        "leadlike_prioritization",
        WORKSPACE_MODULE,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def assert_equal(actual, expected, label):
    if actual != expected:
        raise AssertionError(
            f"{label} mismatch\nExpected: {json.dumps(expected, indent=2)}\n"
            f"Actual: {json.dumps(actual, indent=2)}"
        )


def load_queue_rows(queue_path):
    with open(queue_path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def review_by_compound(report):
    return {
        review["compound_id"]: review
        for review in report["candidate_reviews"]
    }


def test_function_on_environment_assets(module):
    if not hasattr(module, "prioritize_leads"):
        raise AssertionError("prioritize_leads is missing")

    expected = reference_report(LIBRARY_PATH, RULES_PATH)
    actual = module.prioritize_leads(str(LIBRARY_PATH), str(RULES_PATH))
    assert_equal(actual, expected, "environment report")

    reviews = review_by_compound(actual)
    if reviews["LT-101"]["hard_failures"] != ["molecular_weight"]:
        raise AssertionError("LT-101 should fail only on molecular_weight")
    if reviews["LT-102"]["decision"] != "advance":
        raise AssertionError("LT-102 should advance")
    if len(actual["follow_up_queue"]) != 4:
        raise AssertionError("follow_up_queue should contain exactly 4 entries")


def test_function_on_temporary_assets(module):
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        library_path = tmp_path / "lead_batch.jsonl"
        rules_path = tmp_path / "rules.json"

        library_path.write_text(
            "\n".join(
                [
                    json.dumps(
                        {
                            "compound_id": "TMP-001",
                            "name": "Diethyl benzamide",
                            "series": "amide controls",
                            "supplier": "Aster",
                            "smiles": "CCN(CC)C(=O)c1ccccc1",
                        }
                    ),
                    json.dumps(
                        {
                            "compound_id": "TMP-002",
                            "name": "Morpholine sulfone",
                            "series": "sulfone solubilizers",
                            "supplier": "Aster",
                            "smiles": "CCS(=O)(=O)N1CCOCC1",
                        }
                    ),
                    json.dumps(
                        {
                            "compound_id": "TMP-003",
                            "name": "Methoxy morpholine benzamide",
                            "series": "solubilized amides",
                            "supplier": "Aster",
                            "smiles": "COc1ccc(cc1)C(=O)N1CCOCC1",
                        }
                    ),
                    json.dumps(
                        {
                            "compound_id": "TMP-004",
                            "name": "Acetanilide backup",
                            "series": "legacy anilides",
                            "supplier": "Aster",
                            "smiles": "CC(=O)Nc1ccccc1",
                        }
                    ),
                ]
            )
            + "\n"
        )

        rules_path.write_text(
            json.dumps(
                {
                    "campaign": "Temporary Prioritization",
                    "ruleset_name": "temporary_v1",
                    "top_n": 2,
                    "hard_limits": {
                        "molecular_weight": {"min": 150.0, "max": 420.0},
                        "logp": {"min": -0.5, "max": 4.5},
                        "tpsa": {"min": 20.0, "max": 120.0},
                        "hbd": {"min": 0, "max": 4},
                        "hba": {"min": 1, "max": 9},
                        "rotatable_bonds": {"min": 0, "max": 8}
                    },
                    "preferred_ranges": {
                        "molecular_weight": {"min": 180.0, "max": 320.0},
                        "logp": {"min": 0.5, "max": 3.5},
                        "tpsa": {"min": 30.0, "max": 90.0},
                        "hbd": {"min": 0, "max": 2},
                        "hba": {"min": 2, "max": 6},
                        "rotatable_bonds": {"min": 1, "max": 5}
                    }
                }
            )
        )

        expected = reference_report(library_path, rules_path)
        actual = module.prioritize_leads(str(library_path), str(rules_path))
        assert_equal(actual, expected, "temporary report")

        reviews = review_by_compound(actual)
        if reviews["TMP-004"]["decision"] != "reject":
            raise AssertionError("TMP-004 should be rejected")
        if reviews["TMP-002"]["decision_basis"] == "passes hard limits; preferred matches: none":
            raise AssertionError("TMP-002 should have at least one preferred match")
        if [entry["compound_id"] for entry in actual["follow_up_queue"]] != [
            entry["compound_id"] for entry in expected["follow_up_queue"]
        ]:
            raise AssertionError("temporary queue order is incorrect")


def test_script_outputs():
    subprocess.run(["python3", str(WORKSPACE_MODULE)], check=True)

    if not REPORT_PATH.exists():
        raise AssertionError("lead_prioritization_report.json was not created")
    if not QUEUE_PATH.exists():
        raise AssertionError("follow_up_queue.tsv was not created")

    expected_report = reference_report(LIBRARY_PATH, RULES_PATH)
    actual_report = json.loads(REPORT_PATH.read_text())
    assert_equal(actual_report, expected_report, "script report")

    expected_rows = reference_queue_rows(LIBRARY_PATH, RULES_PATH)
    actual_rows = load_queue_rows(QUEUE_PATH)
    assert_equal(actual_rows, expected_rows, "script queue rows")


def calculate_score():
    tests = [
        ("function on environment assets", test_function_on_environment_assets),
        ("function on temporary assets", test_function_on_temporary_assets),
        ("script outputs", lambda module: test_script_outputs()),
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
