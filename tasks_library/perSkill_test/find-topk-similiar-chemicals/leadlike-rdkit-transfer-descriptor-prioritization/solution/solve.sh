#!/bin/bash

set -e

mkdir -p /root/workspace

cat > /root/workspace/leadlike_prioritization.py <<'EOF'
#!/usr/bin/env python3

import csv
import json
from pathlib import Path

from rdkit import Chem
from rdkit.Chem import Descriptors


DESCRIPTOR_ORDER = [
    "molecular_weight",
    "logp",
    "tpsa",
    "hbd",
    "hba",
    "rotatable_bonds",
]

DEFAULT_LIBRARY_PATH = Path("/root/lead_batch.jsonl")
DEFAULT_RULES_PATH = Path("/root/prioritization_rules.json")
DEFAULT_REPORT_PATH = Path("/root/workspace/lead_prioritization_report.json")
DEFAULT_QUEUE_PATH = Path("/root/workspace/follow_up_queue.tsv")


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


def build_follow_up_queue(candidate_reviews, top_n):
    queued = [
        review
        for review in candidate_reviews
        if review["decision"] == "advance"
    ]
    queued.sort(key=lambda review: (-review["priority_score"], review["compound_id"]))

    return [
        {
            "rank": index,
            "compound_id": review["compound_id"],
            "name": review["name"],
            "priority_score": review["priority_score"],
            "canonical_smiles": review["canonical_smiles"],
            "preferred_matches": review["preferred_matches"],
        }
        for index, review in enumerate(queued[:top_n], start=1)
    ]


def prioritize_leads(candidate_library_path, rules_path):
    rules = load_rules(rules_path)
    candidates = load_candidates(candidate_library_path)
    candidate_reviews = [review_candidate(candidate, rules) for candidate in candidates]
    follow_up_queue = build_follow_up_queue(candidate_reviews, int(rules["top_n"]))

    advanced_candidates = sum(
        1
        for review in candidate_reviews
        if review["decision"] == "advance"
    )

    return {
        "campaign": rules["campaign"],
        "ruleset_name": rules["ruleset_name"],
        "summary": {
            "total_candidates": len(candidate_reviews),
            "advanced_candidates": advanced_candidates,
            "rejected_candidates": len(candidate_reviews) - advanced_candidates,
            "queued_candidates": len(follow_up_queue),
        },
        "candidate_reviews": candidate_reviews,
        "follow_up_queue": follow_up_queue,
    }


def write_follow_up_queue(queue_path, follow_up_queue):
    with open(queue_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "rank",
                "compound_id",
                "name",
                "priority_score",
                "preferred_matches",
                "canonical_smiles",
            ],
            delimiter="\t",
        )
        writer.writeheader()
        for entry in follow_up_queue:
            writer.writerow(
                {
                    "rank": entry["rank"],
                    "compound_id": entry["compound_id"],
                    "name": entry["name"],
                    "priority_score": entry["priority_score"],
                    "preferred_matches": "|".join(entry["preferred_matches"]),
                    "canonical_smiles": entry["canonical_smiles"],
                }
            )


def main():
    report = prioritize_leads(DEFAULT_LIBRARY_PATH, DEFAULT_RULES_PATH)
    DEFAULT_REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n")
    write_follow_up_queue(DEFAULT_QUEUE_PATH, report["follow_up_queue"])


if __name__ == "__main__":
    main()
EOF

chmod +x /root/workspace/leadlike_prioritization.py
