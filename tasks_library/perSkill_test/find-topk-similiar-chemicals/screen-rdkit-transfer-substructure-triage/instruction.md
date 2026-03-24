Review a local candidate panel with structure-query rules and prepare a triage package.

You are given:
- `/root/candidate_panel.json`: the screening campaign name and a list of candidates with `candidate_id`, `name`, `series`, and `smiles`
- `/root/triage_rules.json`: `risk_groups` and `retain_groups`, each containing rule objects with `label` and `smarts`

Write your solution to `/root/workspace/substructure_triage.py`.

Your code must expose a function:

```python
triage_candidates(candidate_panel_path, rules_path) -> dict
```

Requirements:
- Parse every candidate structure and normalize it to canonical isomeric SMILES.
- Treat every rule pattern as a structure query and test whether each candidate matches it.
- For each candidate, collect:
  - `candidate_id`
  - `name`
  - `canonical_smiles`
  - `risk_hits`: matched risk-group labels sorted alphabetically
  - `retain_hits`: matched retain-group labels sorted alphabetically
  - `decision`
  - `decision_basis`
- Decision logic:
  - If a candidate matches one or more `risk_groups`, set `decision` to `"reject"` and `decision_basis` to `"risk_match"`.
  - Otherwise, if it matches one or more `retain_groups`, set `decision` to `"pass"` and `decision_basis` to `"retain_match"`.
  - Otherwise, set `decision` to `"reject"` and `decision_basis` to `"no_retain_match"`.
- Preserve the input order for `reviews`.
- Include `approved_candidate_ids` sorted by ascending `candidate_id`.
- `summary` must contain:
  - `total_candidates`
  - `passed_candidates`
  - `rejected_candidates`

When `/root/workspace/substructure_triage.py` is executed as a script with no arguments, it must:
1. Read `/root/candidate_panel.json`
2. Read `/root/triage_rules.json`
3. Write `/root/workspace/substructure_triage_report.json`
4. Write `/root/workspace/passed_candidates.csv`

The JSON report must have this shape:

```json
{
  "campaign": "...",
  "summary": {
    "total_candidates": 8,
    "passed_candidates": 4,
    "rejected_candidates": 4
  },
  "approved_candidate_ids": ["C-101"],
  "reviews": [
    {
      "candidate_id": "C-101",
      "name": "...",
      "canonical_smiles": "...",
      "risk_hits": [],
      "retain_hits": ["amide_core"],
      "decision": "pass",
      "decision_basis": "retain_match"
    }
  ]
}
```

`/root/workspace/passed_candidates.csv` must contain only the passed candidates, sorted by `candidate_id`, with this header:

```text
candidate_id,name,canonical_smiles,retain_hits
```

For the CSV output, join multiple `retain_hits` with `|`.
