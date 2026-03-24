You are cleaning up placeholder citations in a draft survey on computer vision backbones and detectors.

The notes file is located at `/root/review_notes/vision_review_placeholders.md`. Each note contains an incomplete citation clue copied from a rushed outline pass. Some notes can be resolved to a real paper using title fragments, author hints, venue hints, or year hints. One note is intentionally too vague and should be skipped unless you can confirm it uniquely.

Write the resolved results to `/root/resolved_placeholders.tsv`.

Requirements:
- Output a tab-separated file with this exact header:

```tsv
note_id	section	resolved_title	resolved_authors	year	venue	canonical_identifier
```

- Include one row per confidently resolved note
- Preserve the original `note_id` and `section`
- Use the confirmed paper title in `resolved_title`
- Use the full ordered author list in `resolved_authors`, separated by `; `
- Use a four-digit publication year in `year`
- Use a short venue label such as `CVPR` or `ICCV` in `venue`
- Use the paper's canonical DOI in `canonical_identifier` when available
- Skip notes that cannot be confirmed uniquely
- Sort output rows by `note_id` in ascending order
- Write only the TSV file to `/root/resolved_placeholders.tsv`
