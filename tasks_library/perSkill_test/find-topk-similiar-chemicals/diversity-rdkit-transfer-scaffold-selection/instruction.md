Prepare a scaffold-diversity representative set from a local molecule panel.

You are given:
- `/root/scaffold_panel.tsv`: tab-separated rows with `compound_id`, `compound_name`, `series`, `submission_order`, and `smiles`

Write your solution to `/root/workspace/scaffold_selection.py`.

Your code must expose a function:

```python
select_scaffold_representatives(panel_tsv_path) -> dict
```

Requirements:
- Parse every molecule from the TSV file.
- Normalize each structure to canonical isomeric SMILES.
- Extract the Bemis-Murcko scaffold for each molecule.
- If a molecule has no scaffold atoms, use the exact scaffold label `"ACYCLIC"`.
- For every molecule, calculate:
  - `heavy_atom_count`
  - `scaffold_heavy_atom_count`
  - `sidechain_heavy_atoms`
- Group molecules by `scaffold_smiles`.
- Within each scaffold group, order members by ascending `submission_order`, then ascending `compound_id`.
- Select exactly one representative per scaffold using these tie-breakers in order:
  1. smallest `sidechain_heavy_atoms`
  2. smallest `submission_order`
  3. smallest `compound_id`
- Sort `scaffold_groups` by descending `member_count`, then ascending `scaffold_smiles`.
- `representative_set` must follow the same scaffold-group order and assign `selection_rank` starting from 1.

Return a dictionary with this shape:

```json
{
  "summary": {
    "total_compounds": 11,
    "unique_scaffolds": 4,
    "acyclic_members": 2,
    "largest_scaffold_size": 3
  },
  "scaffold_groups": [
    {
      "scaffold_rank": 1,
      "scaffold_smiles": "C1CCCCC1",
      "member_count": 3,
      "member_ids": ["SCF-201", "SCF-202", "SCF-203"],
      "representative": {
        "compound_id": "SCF-201",
        "compound_name": "Cyclohexane core",
        "series": "alicyclic",
        "canonical_smiles": "C1CCCCC1",
        "submission_order": 40,
        "sidechain_heavy_atoms": 0
      }
    }
  ],
  "representative_set": [
    {
      "selection_rank": 1,
      "scaffold_smiles": "C1CCCCC1",
      "compound_id": "SCF-201",
      "compound_name": "Cyclohexane core",
      "canonical_smiles": "C1CCCCC1",
      "member_count": 3,
      "sidechain_heavy_atoms": 0
    }
  ]
}
```

When `/root/workspace/scaffold_selection.py` is executed as a script with no arguments, it must:
1. Read `/root/scaffold_panel.tsv`
2. Write `/root/workspace/scaffold_selection_report.json`
3. Write `/root/workspace/scaffold_summary.tsv`

`/root/workspace/scaffold_summary.tsv` must contain one row per scaffold group in scaffold rank order, with this header:

```text
scaffold_rank	scaffold_smiles	member_count	representative_id	representative_name	sidechain_heavy_atoms	member_ids
```

For the TSV output, join multiple `member_ids` with `|`.
