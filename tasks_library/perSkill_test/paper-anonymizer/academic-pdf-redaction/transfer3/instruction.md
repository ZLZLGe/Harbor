Create a redaction manifest pipeline for three PDF submissions.

Inputs:
- `/root/paper1.pdf`
- `/root/paper2.pdf`
- `/root/paper3.pdf`

Outputs:
1. Redacted PDFs in `/root/redacted/transfer3/paper{1-3}.pdf`
2. Manifest JSON at `/root/reports/transfer3_manifest.json`

Manifest schema:
- top-level key: `documents` (array of 3 objects)
- each object must contain:
  - `file`
  - `author_tokens_removed`
  - `identifier_tokens_removed`
  - `retained_ratio`
  - `page_count_unchanged` (boolean)

Rules:
- Remove identifying names and identifiers from non-reference sections.
- Keep references section intact.
- Keep page counts unchanged.
- `retained_ratio` for every document must be at least 0.75.
