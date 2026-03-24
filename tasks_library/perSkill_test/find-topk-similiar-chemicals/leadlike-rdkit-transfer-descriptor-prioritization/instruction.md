Prioritize which lead-like compounds should move into follow-up work from a local batch.

You are given:
- `/root/lead_batch.jsonl`: one JSON object per line with `compound_id`, `name`, `series`, `supplier`, and `smiles`
- `/root/prioritization_rules.json`: the campaign name, descriptor limits, preferred ranges, and requested `top_n`

Write your solution to `/root/workspace/leadlike_prioritization.py`.

Your code must expose a function:

```python
prioritize_leads(candidate_library_path, rules_path) -> dict
```

Requirements:
- Parse every candidate from the JSONL file.
- Normalize each structure to canonical isomeric SMILES.
- For every candidate, calculate these descriptors:
  - `molecular_weight`
  - `logp`
  - `tpsa`
  - `hbd`
  - `hba`
  - `rotatable_bonds`
- Round `molecular_weight`, `logp`, and `tpsa` to 2 decimal places.
- Evaluate descriptors against both `hard_limits` and `preferred_ranges`.
- Use this descriptor order everywhere a list of descriptor names is emitted:
  - `molecular_weight`
  - `logp`
  - `tpsa`
  - `hbd`
  - `hba`
  - `rotatable_bonds`
- For each candidate review, include:
  - `compound_id`
  - `name`
  - `series`
  - `supplier`
  - `canonical_smiles`
  - `descriptors`
  - `preferred_matches`
  - `hard_failures`
  - `priority_score`
  - `decision`
  - `decision_basis`
- Decision rules:
  - If `hard_failures` is empty, set `decision` to `"advance"`.
  - Otherwise, set `decision` to `"reject"`.
  - `priority_score` is the number of descriptors that fall inside `preferred_ranges`.
  - If a candidate is rejected, `decision_basis` must be `fails hard limits: ...` followed by the comma-separated `hard_failures`.
  - If a candidate advances and has one or more preferred matches, `decision_basis` must be `passes hard limits; preferred matches: ...` followed by the comma-separated `preferred_matches`.
  - If a candidate advances with no preferred matches, `decision_basis` must be exactly `passes hard limits; preferred matches: none`.
- Preserve input order for `candidate_reviews`.
- Build `follow_up_queue` from only the advancing candidates.
- Sort `follow_up_queue` by descending `priority_score`, then ascending `compound_id`.
- Truncate `follow_up_queue` to `top_n`.
- Each `follow_up_queue` entry must contain:
  - `rank`
  - `compound_id`
  - `name`
  - `priority_score`
  - `canonical_smiles`
  - `preferred_matches`
- The returned dictionary must have this shape:

```json
{
  "campaign": "...",
  "ruleset_name": "...",
  "summary": {
    "total_candidates": 8,
    "advanced_candidates": 5,
    "rejected_candidates": 3,
    "queued_candidates": 4
  },
  "candidate_reviews": [
    {
      "compound_id": "LT-101",
      "name": "...",
      "series": "...",
      "supplier": "...",
      "canonical_smiles": "...",
      "descriptors": {
        "molecular_weight": 135.17,
        "logp": 1.23,
        "tpsa": 29.1,
        "hbd": 1,
        "hba": 1,
        "rotatable_bonds": 1
      },
      "preferred_matches": ["logp"],
      "hard_failures": ["molecular_weight"],
      "priority_score": 1,
      "decision": "reject",
      "decision_basis": "fails hard limits: molecular_weight"
    }
  ],
  "follow_up_queue": [
    {
      "rank": 1,
      "compound_id": "LT-102",
      "name": "...",
      "priority_score": 5,
      "canonical_smiles": "...",
      "preferred_matches": ["molecular_weight", "logp"]
    }
  ]
}
```

When `/root/workspace/leadlike_prioritization.py` is executed as a script with no arguments, it must:
1. Read `/root/lead_batch.jsonl`
2. Read `/root/prioritization_rules.json`
3. Write `/root/workspace/lead_prioritization_report.json`
4. Write `/root/workspace/follow_up_queue.tsv`

`/root/workspace/follow_up_queue.tsv` must contain only the queued candidates, in queue order, with this header:

```text
rank	compound_id	name	priority_score	preferred_matches	canonical_smiles
```

For the TSV output, join multiple `preferred_matches` with `|`.
