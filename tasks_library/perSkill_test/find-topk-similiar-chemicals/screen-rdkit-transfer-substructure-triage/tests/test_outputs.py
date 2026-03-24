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


WORKSPACE_MODULE = Path("/root/workspace/substructure_triage.py")
PANEL_PATH = Path("/root/candidate_panel.json")
RULES_PATH = Path("/root/triage_rules.json")
REPORT_PATH = Path("/root/workspace/substructure_triage_report.json")
PASSED_CSV_PATH = Path("/root/workspace/passed_candidates.csv")


def canonicalize_smiles(smiles):
    molecule = Chem.MolFromSmiles(smiles.strip())
    if molecule is None:
        raise ValueError(f"Could not parse SMILES: {smiles}")
    return Chem.MolToSmiles(molecule, canonical=True, isomericSmiles=True)


def compile_rules(rules_path):
    payload = json.loads(Path(rules_path).read_text())
    compiled = {}
    for group_name in ("risk_groups", "retain_groups"):
        compiled[group_name] = []
        for rule in payload[group_name]:
            pattern = Chem.MolFromSmarts(rule["smarts"])
            if pattern is None:
                raise ValueError(f"Could not parse SMARTS: {rule['smarts']}")
            compiled[group_name].append(
                {
                    "label": rule["label"],
                    "pattern": pattern,
                }
            )
    return compiled


def match_labels(molecule, compiled_rules, group_name):
    labels = []
    for rule in compiled_rules[group_name]:
        if molecule.HasSubstructMatch(rule["pattern"]):
            labels.append(rule["label"])
    return sorted(labels)


def reference_report(candidate_panel_path, rules_path):
    panel = json.loads(Path(candidate_panel_path).read_text())
    compiled_rules = compile_rules(rules_path)

    reviews = []
    approved_candidate_ids = []

    for entry in panel["candidates"]:
        molecule = Chem.MolFromSmiles(entry["smiles"])
        if molecule is None:
            raise ValueError(f"Could not parse SMILES: {entry['smiles']}")

        risk_hits = match_labels(molecule, compiled_rules, "risk_groups")
        retain_hits = match_labels(molecule, compiled_rules, "retain_groups")

        if risk_hits:
            decision = "reject"
            decision_basis = "risk_match"
        elif retain_hits:
            decision = "pass"
            decision_basis = "retain_match"
            approved_candidate_ids.append(entry["candidate_id"])
        else:
            decision = "reject"
            decision_basis = "no_retain_match"

        reviews.append(
            {
                "candidate_id": entry["candidate_id"],
                "name": entry["name"],
                "canonical_smiles": canonicalize_smiles(entry["smiles"]),
                "risk_hits": risk_hits,
                "retain_hits": retain_hits,
                "decision": decision,
                "decision_basis": decision_basis,
            }
        )

    approved_candidate_ids = sorted(approved_candidate_ids)
    passed_candidates = len(approved_candidate_ids)
    total_candidates = len(reviews)

    return {
        "campaign": panel["campaign"],
        "summary": {
            "total_candidates": total_candidates,
            "passed_candidates": passed_candidates,
            "rejected_candidates": total_candidates - passed_candidates,
        },
        "approved_candidate_ids": approved_candidate_ids,
        "reviews": reviews,
    }


def reference_passed_rows(candidate_panel_path, rules_path):
    report = reference_report(candidate_panel_path, rules_path)
    rows = []
    for review in report["reviews"]:
        if review["decision"] == "pass":
            rows.append(
                {
                    "candidate_id": review["candidate_id"],
                    "name": review["name"],
                    "canonical_smiles": review["canonical_smiles"],
                    "retain_hits": "|".join(review["retain_hits"]),
                }
            )
    rows.sort(key=lambda row: row["candidate_id"])
    return rows


def load_agent_module():
    if not WORKSPACE_MODULE.exists():
        raise FileNotFoundError("substructure_triage.py was not created")

    spec = importlib.util.spec_from_file_location("substructure_triage", WORKSPACE_MODULE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def assert_equal(actual, expected, label):
    if actual != expected:
        raise AssertionError(
            f"{label} mismatch\nExpected: {json.dumps(expected, indent=2)}\n"
            f"Actual: {json.dumps(actual, indent=2)}"
        )


def load_csv_rows(csv_path):
    with open(csv_path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_function_on_environment_assets(module):
    if not hasattr(module, "triage_candidates"):
        raise AssertionError("triage_candidates is missing")

    expected = reference_report(PANEL_PATH, RULES_PATH)
    actual = module.triage_candidates(str(PANEL_PATH), str(RULES_PATH))
    assert_equal(actual, expected, "environment triage report")

    review_by_id = {
        review["candidate_id"]: review
        for review in actual["reviews"]
    }

    if review_by_id["C-103"]["retain_hits"] != ["morpholine_ring", "sulfonamide"]:
        raise AssertionError("C-103 should keep both retain motifs in alphabetical order")

    if review_by_id["C-107"]["decision_basis"] != "risk_match":
        raise AssertionError("risk matches must override retain matches")

    if actual["approved_candidate_ids"] != ["C-101", "C-103", "C-105", "C-106"]:
        raise AssertionError("approved candidate ids are incorrect")


def test_function_on_temporary_assets(module):
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        panel_path = tmp_path / "panel.json"
        rules_path = tmp_path / "rules.json"

        panel_path.write_text(
            json.dumps(
                {
                    "campaign": "Temporary Triage",
                    "candidates": [
                        {
                            "candidate_id": "T-003",
                            "name": "Morpholine keeper",
                            "series": "temp",
                            "smiles": "N1CCOCC1",
                        },
                        {
                            "candidate_id": "T-001",
                            "name": "Nitro amide reject",
                            "series": "temp",
                            "smiles": "CC(=O)Nc1ccc([N+](=O)[O-])cc1",
                        },
                        {
                            "candidate_id": "T-002",
                            "name": "Blank solvent mimic",
                            "series": "temp",
                            "smiles": "CCO",
                        },
                    ],
                }
            )
        )

        rules_path.write_text(
            json.dumps(
                {
                    "risk_groups": [
                        {"label": "aromatic_nitro", "smarts": "c[N+](=O)[O-]"}
                    ],
                    "retain_groups": [
                        {"label": "amide_core", "smarts": "C(=O)N"},
                        {"label": "morpholine_ring", "smarts": "N1CCOCC1"},
                    ],
                }
            )
        )

        expected = reference_report(panel_path, rules_path)
        actual = module.triage_candidates(str(panel_path), str(rules_path))
        assert_equal(actual, expected, "temporary triage report")

        review_by_id = {
            review["candidate_id"]: review
            for review in actual["reviews"]
        }

        if review_by_id["T-001"]["decision"] != "reject":
            raise AssertionError("T-001 should be rejected")

        if review_by_id["T-001"]["decision_basis"] != "risk_match":
            raise AssertionError("T-001 should be rejected because of a risk match")

        if review_by_id["T-002"]["decision_basis"] != "no_retain_match":
            raise AssertionError("T-002 should be rejected because it matches no retain rule")


def test_script_outputs():
    subprocess.run(["python3", str(WORKSPACE_MODULE)], check=True)

    if not REPORT_PATH.exists():
        raise AssertionError("substructure_triage_report.json was not created")

    if not PASSED_CSV_PATH.exists():
        raise AssertionError("passed_candidates.csv was not created")

    expected_report = reference_report(PANEL_PATH, RULES_PATH)
    actual_report = json.loads(REPORT_PATH.read_text())
    assert_equal(actual_report, expected_report, "script JSON report")

    expected_rows = reference_passed_rows(PANEL_PATH, RULES_PATH)
    actual_rows = load_csv_rows(PASSED_CSV_PATH)
    assert_equal(actual_rows, expected_rows, "passed candidates CSV")


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
