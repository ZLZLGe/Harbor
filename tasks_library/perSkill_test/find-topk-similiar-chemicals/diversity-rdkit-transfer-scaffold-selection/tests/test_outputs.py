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
from rdkit.Chem.Scaffolds import MurckoScaffold


WORKSPACE_MODULE = Path("/root/workspace/scaffold_selection.py")
PANEL_PATH = Path("/root/scaffold_panel.tsv")
REPORT_PATH = Path("/root/workspace/scaffold_selection_report.json")
SUMMARY_PATH = Path("/root/workspace/scaffold_summary.tsv")
ACYCLIC_LABEL = "ACYCLIC"


def load_panel(panel_tsv_path):
    rows = []
    with open(panel_tsv_path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            rows.append(
                {
                    "compound_id": row["compound_id"],
                    "compound_name": row["compound_name"],
                    "series": row["series"],
                    "submission_order": int(row["submission_order"]),
                    "smiles": row["smiles"],
                }
            )
    return rows


def canonicalize_smiles(smiles):
    molecule = Chem.MolFromSmiles(smiles)
    if molecule is None:
        raise ValueError(f"Could not parse SMILES: {smiles}")
    return Chem.MolToSmiles(molecule, canonical=True, isomericSmiles=True)


def scaffold_data(canonical_smiles):
    molecule = Chem.MolFromSmiles(canonical_smiles)
    scaffold = MurckoScaffold.GetScaffoldForMol(molecule)
    if scaffold.GetNumAtoms() == 0:
        return ACYCLIC_LABEL, 0
    return (
        Chem.MolToSmiles(scaffold, canonical=True, isomericSmiles=True),
        scaffold.GetNumHeavyAtoms(),
    )


def reference_report(panel_tsv_path):
    enriched_rows = []
    for row in load_panel(panel_tsv_path):
        canonical_smiles = canonicalize_smiles(row["smiles"])
        molecule = Chem.MolFromSmiles(canonical_smiles)
        scaffold_smiles, scaffold_heavy_atom_count = scaffold_data(canonical_smiles)
        heavy_atom_count = molecule.GetNumHeavyAtoms()
        enriched_rows.append(
            {
                **row,
                "canonical_smiles": canonical_smiles,
                "scaffold_smiles": scaffold_smiles,
                "heavy_atom_count": heavy_atom_count,
                "scaffold_heavy_atom_count": scaffold_heavy_atom_count,
                "sidechain_heavy_atoms": heavy_atom_count - scaffold_heavy_atom_count,
            }
        )

    grouped = {}
    for row in enriched_rows:
        grouped.setdefault(row["scaffold_smiles"], []).append(row)

    scaffold_groups = []
    for scaffold_smiles, members in grouped.items():
        ordered_members = sorted(
            members,
            key=lambda member: (member["submission_order"], member["compound_id"]),
        )
        representative = min(
            ordered_members,
            key=lambda member: (
                member["sidechain_heavy_atoms"],
                member["submission_order"],
                member["compound_id"],
            ),
        )
        scaffold_groups.append(
            {
                "scaffold_smiles": scaffold_smiles,
                "member_count": len(ordered_members),
                "member_ids": [member["compound_id"] for member in ordered_members],
                "representative": {
                    "compound_id": representative["compound_id"],
                    "compound_name": representative["compound_name"],
                    "series": representative["series"],
                    "canonical_smiles": representative["canonical_smiles"],
                    "submission_order": representative["submission_order"],
                    "sidechain_heavy_atoms": representative["sidechain_heavy_atoms"],
                },
            }
        )

    scaffold_groups.sort(
        key=lambda group: (-group["member_count"], group["scaffold_smiles"]),
    )

    ranked_groups = []
    representative_set = []
    for index, group in enumerate(scaffold_groups, start=1):
        ranked_groups.append(
            {
                "scaffold_rank": index,
                **group,
            }
        )
        representative = group["representative"]
        representative_set.append(
            {
                "selection_rank": index,
                "scaffold_smiles": group["scaffold_smiles"],
                "compound_id": representative["compound_id"],
                "compound_name": representative["compound_name"],
                "canonical_smiles": representative["canonical_smiles"],
                "member_count": group["member_count"],
                "sidechain_heavy_atoms": representative["sidechain_heavy_atoms"],
            }
        )

    acyclic_members = sum(
        group["member_count"]
        for group in scaffold_groups
        if group["scaffold_smiles"] == ACYCLIC_LABEL
    )

    return {
        "summary": {
            "total_compounds": len(enriched_rows),
            "unique_scaffolds": len(scaffold_groups),
            "acyclic_members": acyclic_members,
            "largest_scaffold_size": max(
                (group["member_count"] for group in scaffold_groups),
                default=0,
            ),
        },
        "scaffold_groups": ranked_groups,
        "representative_set": representative_set,
    }


def reference_summary_rows(panel_tsv_path):
    report = reference_report(panel_tsv_path)
    rows = []
    for group in report["scaffold_groups"]:
        rows.append(
            {
                "scaffold_rank": str(group["scaffold_rank"]),
                "scaffold_smiles": group["scaffold_smiles"],
                "member_count": str(group["member_count"]),
                "representative_id": group["representative"]["compound_id"],
                "representative_name": group["representative"]["compound_name"],
                "sidechain_heavy_atoms": str(group["representative"]["sidechain_heavy_atoms"]),
                "member_ids": "|".join(group["member_ids"]),
            }
        )
    return rows


def load_agent_module():
    if not WORKSPACE_MODULE.exists():
        raise FileNotFoundError("scaffold_selection.py was not created")

    spec = importlib.util.spec_from_file_location("scaffold_selection", WORKSPACE_MODULE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def assert_equal(actual, expected, label):
    if actual != expected:
        raise AssertionError(
            f"{label} mismatch\nExpected: {json.dumps(expected, indent=2)}\n"
            f"Actual: {json.dumps(actual, indent=2)}"
        )


def load_summary_rows(summary_path):
    with open(summary_path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def scaffold_group_by_smiles(report):
    return {
        group["scaffold_smiles"]: group
        for group in report["scaffold_groups"]
    }


def test_function_on_environment_assets(module):
    if not hasattr(module, "select_scaffold_representatives"):
        raise AssertionError("select_scaffold_representatives is missing")

    expected = reference_report(PANEL_PATH)
    actual = module.select_scaffold_representatives(str(PANEL_PATH))
    assert_equal(actual, expected, "environment report")

    representative_ids = [
        entry["compound_id"]
        for entry in actual["representative_set"]
    ]
    if representative_ids != ["SCF-201", "SCF-101", "SCF-301", "SCF-401"]:
        raise AssertionError("environment representative order is incorrect")

    groups = scaffold_group_by_smiles(actual)
    if groups["ACYCLIC"]["representative"]["compound_id"] != "SCF-401":
        raise AssertionError("acyclic representative should be SCF-401")


def test_function_on_temporary_assets(module):
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        panel_path = tmp_path / "panel.tsv"
        panel_path.write_text(
            "\n".join(
                [
                    "compound_id\tcompound_name\tseries\tsubmission_order\tsmiles",
                    "TMP-003\tToluene temp\taromatic\t2\tCc1ccccc1",
                    "TMP-001\tChlorobenzene temp\taromatic\t1\tClc1ccccc1",
                    "TMP-002\tEthylbenzene temp\taromatic\t3\tCCc1ccccc1",
                    "TMP-004\tEthanol temp\tacyclic\t4\tCCO",
                    "TMP-005\tIsopropanol temp\tacyclic\t5\tCC(O)C",
                ]
            )
            + "\n"
        )

        expected = reference_report(panel_path)
        actual = module.select_scaffold_representatives(str(panel_path))
        assert_equal(actual, expected, "temporary report")

        if actual["summary"]["unique_scaffolds"] != 2:
            raise AssertionError("temporary panel should produce exactly 2 scaffolds")

        if actual["representative_set"][0]["compound_id"] != "TMP-001":
            raise AssertionError("submission_order tie-break did not choose TMP-001")

        if actual["representative_set"][1]["compound_id"] != "TMP-004":
            raise AssertionError("acyclic representative should be TMP-004")


def test_script_outputs():
    subprocess.run(["python3", str(WORKSPACE_MODULE)], check=True)

    if not REPORT_PATH.exists():
        raise AssertionError("scaffold_selection_report.json was not created")

    if not SUMMARY_PATH.exists():
        raise AssertionError("scaffold_summary.tsv was not created")

    expected_report = reference_report(PANEL_PATH)
    actual_report = json.loads(REPORT_PATH.read_text())
    assert_equal(actual_report, expected_report, "script report")

    expected_rows = reference_summary_rows(PANEL_PATH)
    actual_rows = load_summary_rows(SUMMARY_PATH)
    assert_equal(actual_rows, expected_rows, "summary TSV")


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
