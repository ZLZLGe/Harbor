#!/bin/bash
set -e

mkdir -p /root/workspace

cat > /root/workspace/scaffold_selection.py <<'EOF'
#!/usr/bin/env python3

import csv
import json
from pathlib import Path

from rdkit import Chem
from rdkit.Chem.Scaffolds import MurckoScaffold


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


def select_scaffold_representatives(panel_tsv_path):
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


def write_summary_tsv(report, output_path):
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "scaffold_rank",
                "scaffold_smiles",
                "member_count",
                "representative_id",
                "representative_name",
                "sidechain_heavy_atoms",
                "member_ids",
            ],
            delimiter="\t",
        )
        writer.writeheader()
        for group in report["scaffold_groups"]:
            writer.writerow(
                {
                    "scaffold_rank": group["scaffold_rank"],
                    "scaffold_smiles": group["scaffold_smiles"],
                    "member_count": group["member_count"],
                    "representative_id": group["representative"]["compound_id"],
                    "representative_name": group["representative"]["compound_name"],
                    "sidechain_heavy_atoms": group["representative"]["sidechain_heavy_atoms"],
                    "member_ids": "|".join(group["member_ids"]),
                }
            )


def main():
    report = select_scaffold_representatives(PANEL_PATH)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2))
    write_summary_tsv(report, SUMMARY_PATH)


if __name__ == "__main__":
    main()
EOF

chmod +x /root/workspace/scaffold_selection.py
