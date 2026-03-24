Review these files:
- `/root/marketplace_listings.jsonl`: one seller listing per line from a marketplace moderation export.
- `/root/restricted_catalog.csv`: canonical restricted products that must not be listed.

Write `/root/restricted_listing_matches.json` containing only the marketplace listings that should be treated as reliable matches to the restricted catalog.

Matching guidance:
1. Compare seller titles against the catalog titles, allowing for abbreviations, punctuation changes, token reordering, merged or split brand words, and small spelling errors.
2. Listing titles may include non-essential bundle or condition text such as `w/`, `with`, `bundle`, `combo`, `sealed`, `new`, `open box`, `charger`, `case`, or `pouch`. Ignore that noise when deciding whether a listing matches a restricted catalog item.
3. Include a listing only when one restricted catalog item is clearly the best candidate.
4. If a listing is ambiguous between multiple restricted catalog items, do not include it.
5. If a listing does not reliably match any restricted catalog item, do not include it.

Output requirements:
- Write a JSON array sorted by `listing_id` ascending.
- Preserve the original listing title in `listing_title`.
- Each object must use this exact structure:

```json
[
  {
    "listing_id": "ML-002",
    "seller_id": "S-101",
    "listing_title": "Asteron Nova X-2 sat phone w/ wall charger",
    "matched_catalog_id": "RC-101",
    "matched_canonical_title": "Asteron Nova X2 Satellite Phone",
    "restriction_reason": "Export Controlled Device"
  }
]
```

- Do not include safe listings or unresolved listings.
