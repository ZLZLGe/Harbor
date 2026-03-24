You are reconciling two exported BibTeX libraries before a shared reading list is handed off to another lab.

The two source files are:
- `/root/merge_inputs/library_alpha.bib`
- `/root/merge_inputs/library_beta.bib`

Some records point to the same scholarly work but use different citation keys and slightly different metadata. Differences may include capitalization, punctuation, truncated author lists, or one export keeping an arXiv identifier while another does not.

Identify every duplicate cluster across the combined libraries and choose one canonical citation key for each cluster.

Write `/root/duplicate_map.json` using this schema:

```json
{
  "duplicate_map": {
    "canonical_key_one": ["duplicate_key_a", "duplicate_key_b"],
    "canonical_key_two": ["duplicate_key_c"]
  }
}
```

Requirements:
- Include only duplicate clusters with at least two total entries
- Each object key must be the canonical citation key for that cluster
- Each array must contain only the non-canonical keys that should be merged into that canonical entry
- Choose the canonical key from the duplicate cluster by selecting the entry with the most non-empty BibTeX metadata fields; if there is still a tie, choose the lexicographically smallest citation key
- Treat records as duplicates when their metadata clearly indicates the same paper, even if one export has lighter formatting or fewer fields
- Do not include unique, non-duplicate records anywhere in the output
- Sort canonical keys in ascending order and sort each merged-key array in ascending order
- Output valid JSON only to `/root/duplicate_map.json`
