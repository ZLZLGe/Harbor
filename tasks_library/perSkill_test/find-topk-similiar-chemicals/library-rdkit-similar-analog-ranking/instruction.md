Rank the closest analogs in a local compound library.

You are given:
- `/root/compound_request.json`: the target compound and the requested `top_k`
- `/root/compound_library.csv`: candidate compounds with `compound_name` and `smiles` columns

Write your solution to `/root/workspace/analog_ranking.py`.

Your code must expose a function:

```python
rank_similar_analogs(target_record_path, library_csv_path, top_k) -> list[dict]
```

Requirements:
- Parse the target structure and every library structure from the provided files.
- Normalize each structure to canonical isomeric SMILES.
- Merge duplicate library rows that normalize to the same canonical isomeric SMILES.
- For each merged entry, keep:
  - `name`: the alphabetically smallest compound name in that merged group
  - `aliases`: all merged compound names sorted alphabetically
  - `canonical_smiles`
  - `similarity`
- Compute Morgan fingerprint similarity with these fixed settings:
  - radius = 2
  - fpSize = 2048
  - include chirality = true
  - similarity metric = Tanimoto
- Sort results by descending similarity. If two scores are equal, sort by `name` in ascending alphabetical order.
- Round each `similarity` value to 4 decimal places in the returned list.

When `/root/workspace/analog_ranking.py` is executed as a script with no arguments, it must:
1. Read `/root/compound_request.json`
2. Read `/root/compound_library.csv`
3. Write `/root/workspace/analog_report.json`

The JSON report must have this shape:

```json
{
  "target_name": "...",
  "target_canonical_smiles": "...",
  "top_k": 6,
  "results": [
    {
      "rank": 1,
      "name": "...",
      "aliases": ["...", "..."],
      "canonical_smiles": "...",
      "similarity": 1.0
    }
  ]
}
```

You may ignore CSV columns other than `compound_name` and `smiles`.
