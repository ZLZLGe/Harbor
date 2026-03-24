#!/bin/bash

set -e

mkdir -p /root/workspace

cat > /root/workspace/substructure_triage.py <<'EOF'
#!/usr/bin/env python3

import csv
import json
from pathlib import Path

from rdkit import Chem


def canonicalize_smiles(smiles):
    molecule = Chem.MolFromSmiles(smiles.strip())
    if molecule is None:
        raise ValueError(f"Could not parse SMILES: {smiles}")
    return Chem.MolToSmiles(molecule, canonical=True, isomericSmiles=True)


def load_rules(rules_path):
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


def triage_candidates(candidate_panel_path, rules_path):
    panel = json.loads(Path(candidate_panel_path).read_text())
    compiled_rules = load_rules(rules_path)

    reviews = []
    approved_candidate_ids = []

    for entry in panel["candidates"]:
        molecule = Chem.MolFromSmiles(entry["smiles"])
        if molecule is None:
            raise ValueError(f"Could not parse SMILES: {entry['smiles']}")

        canonical_smiles = canonicalize_smiles(entry["smiles"])
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
                "canonical_smiles": canonical_smiles,
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


def write_outputs(
    candidate_panel_path="/root/candidate_panel.json",
    rules_path="/root/triage_rules.json",
    report_path="/root/workspace/substructure_triage_report.json",
    passed_csv_path="/root/workspace/passed_candidates.csv",
):
    report = triage_candidates(candidate_panel_path, rules_path)
    Path(report_path).write_text(json.dumps(report, indent=2) + "\n")

    passed_rows = [
        review
        for review in report["reviews"]
        if review["decision"] == "pass"
    ]
    passed_rows.sort(key=lambda row: row["candidate_id"])

    with open(passed_csv_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "candidate_id",
                "name",
                "canonical_smiles",
                "retain_hits",
            ],
        )
        writer.writeheader()
        for row in passed_rows:
            writer.writerow(
                {
                    "candidate_id": row["candidate_id"],
                    "name": row["name"],
                    "canonical_smiles": row["canonical_smiles"],
                    "retain_hits": "|".join(row["retain_hits"]),
                }
            )

    return report


def main():
    write_outputs()


if __name__ == "__main__":
    main()
EOF
