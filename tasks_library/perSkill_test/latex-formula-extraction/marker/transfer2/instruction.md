Build a page-level formula summary CSV from block extraction data.

Input file:
- `/root/input/page_blocks.json`

Output file:
- `/root/transfer2_page_formula_counts.csv`

Rules:
1. Read all pages in input order.
2. Only count blocks where `type` is exactly `display_formula`.
3. For each page, emit one CSV row with columns:
   - `page`
   - `display_formula_count`
   - `formula_ids`
4. `formula_ids` must be a `;`-joined string of display formula IDs in appearance order.
5. Include CSV header.
