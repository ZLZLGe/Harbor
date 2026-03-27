Prepare anonymized outputs for `/root/paper2.pdf` and `/root/paper3.pdf`.

Write redacted files to:
- `/root/redacted/transfer2/paper2.pdf`
- `/root/redacted/transfer2/paper3.pdf`

Then produce `/root/reports/transfer2_quality.md` with:
- A two-row table (`paper2.pdf`, `paper3.pdf`)
- Columns: `file`, `original_chars`, `redacted_chars`, `retained_ratio`, `status`
- `status` should be `PASS` when `retained_ratio >= 0.75`, otherwise `FAIL`

Rules:
1. Remove identifying names, affiliations, and explicit contact/venue strings from the body text.
2. Leave references text intact.
3. Keep page counts unchanged.
