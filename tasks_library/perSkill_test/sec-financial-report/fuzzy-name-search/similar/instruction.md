You are covering a quarterly 13F research handoff. The filing snapshots are already available in `/root/2025-q2` and `/root/2025-q3`.

Some names in the handoff note are misspelled. Resolve each item to the best matching filing manager or issuer and write the final answers to `/root/fuzzy_lookup_answers.json`.

Questions:

1. In `2025-q3`, which accession number best matches the manager query `renaisance technolgies`?
2. In `2025-q2`, which accession number best matches the manager query `berkshire hathawy`?
3. Which CUSIP best matches the issuer query `palantir techologies`?
4. Which CUSIP best matches the issuer query `micro stratagy`?

Write the output as JSON with this exact schema:

```json
{
  "q3_manager_accession": "string",
  "q2_manager_accession": "string",
  "palantir_cusip": "string",
  "microstrategy_cusip": "string"
}
```
