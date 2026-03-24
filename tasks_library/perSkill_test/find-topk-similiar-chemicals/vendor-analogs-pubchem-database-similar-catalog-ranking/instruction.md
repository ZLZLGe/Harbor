Read `/root/vendor_catalog.json`. It contains a lead compound name plus a supplier shortlist whose `listing_name` values may be aliases or systematic synonyms rather than normalized compound names.

Use an external chemistry database such as PubChem to normalize the lead and every catalog entry to a chemical structure. Then compute Morgan fingerprint Tanimoto similarity with radius `2` and chirality enabled for each candidate against the normalized lead structure.

Write `/root/workspace/analogue_ranking.json` with this shape:

```json
{
  "lead_input_name": "string",
  "lead_cid": 0,
  "lead_canonical_name": "string",
  "ranking": [
    {
      "rank": 1,
      "vendor_sku": "string",
      "supplier": "string",
      "input_name": "string",
      "cid": 0,
      "canonical_name": "string",
      "similarity": 1.0
    }
  ]
}
```

Requirements:

- Keep exactly the top `top_k` resolved candidates from the input file.
- Round each `similarity` value to 6 decimal places.
- Sort by descending similarity, then by `canonical_name` alphabetically, then by `vendor_sku` alphabetically.
- Use the normalized compound name from PubChem as `lead_canonical_name` and each candidate `canonical_name`.
- Do not hardcode a manual alias-to-CID mapping.
