Create a machine-readable profile for this PDF corpus:
- `/root/paper1.pdf`
- `/root/paper2.pdf`
- `/root/paper3.pdf`

Write one JSON file at `/root/reports/similar_document_profile.json` with this structure:
- top-level key `documents` (array of length 3)
- each object includes:
  - `file`
  - `page_count`
  - `text_chars`
  - `non_empty_pages`
  - `sample_excerpt` (first 120 characters of extracted text, whitespace-normalized)

Rules:
1. Keep file names exactly `paper1.pdf`, `paper2.pdf`, `paper3.pdf`.
2. `page_count` and `text_chars` must reflect extracted content from each PDF.
3. `sample_excerpt` must be non-empty for each document.
