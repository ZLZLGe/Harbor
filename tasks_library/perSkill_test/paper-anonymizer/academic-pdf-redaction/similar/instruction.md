A program committee needs quick blind-review sanitization for three submissions: `/root/paper1.pdf`, `/root/paper2.pdf`, and `/root/paper3.pdf`.

Create redacted copies at:
- `/root/redacted/similar/paper1.pdf`
- `/root/redacted/similar/paper2.pdf`
- `/root/redacted/similar/paper3.pdf`

Requirements:
1. Remove author-identifying content in the main body, including personal names, affiliations, direct contact strings, and submission identifiers.
2. Keep the References section intact.
3. Preserve document structure (page counts must stay unchanged).
4. Write a JSON summary report to `/root/reports/similar_redaction_report.json` with one entry per output PDF, including `file`, `redaction_hits`, and `retained_ratio`.

The output should remain readable after redaction and must not be reduced to near-empty pages.
