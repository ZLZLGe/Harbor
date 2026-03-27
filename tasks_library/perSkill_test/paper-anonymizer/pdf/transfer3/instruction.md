Generate a keyword frequency inventory from three PDFs:
- `/root/paper1.pdf`
- `/root/paper2.pdf`
- `/root/paper3.pdf`

Write a markdown report to `/root/reports/transfer3_keyword_inventory.md`.

Required keywords: `voice`, `data`, `pruning`.

Report format:
1. Title line: `# Transfer3 Keyword Inventory`
2. A markdown table with header:
   `| keyword | paper1 | paper2 | paper3 | total |`
3. One row per required keyword.

Rules:
- Count keywords case-insensitively.
- Use text extracted from all pages.
- `total` must equal the sum of `paper1 + paper2 + paper3` for each row.
