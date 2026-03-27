A chair wants a leakage-audit matrix for three submission PDFs.

Input files:
- `/root/paper1.pdf`
- `/root/paper2.pdf`
- `/root/paper3.pdf`

Produce these outputs:
- Redacted PDFs in `/root/redacted/transfer1/paper{1-3}.pdf`
- A CSV report at `/root/reports/transfer1_matrix.csv`

CSV requirements:
- Header: `file,author_hits,affiliation_hits,identifier_hits,total_hits,retained_ratio`
- One row per paper
- `retained_ratio` should be rounded to 4 decimals

Redaction requirements:
1. Remove identifying author, affiliation, contact, and submission-identifier strings from the document body.
2. Keep references section text available.
3. Keep each output PDF page count unchanged.
