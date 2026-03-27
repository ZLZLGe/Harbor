Prepare a structured extraction artifact from `/root/latex_paper.pdf`.

Write `/root/transfer1_formula_catalog.json` using this schema:

- top-level object with keys:
  - `paper` (string)
  - `entries` (array)
- each entry object must include:
  - `id` (string, e.g., F1)
  - `page` (integer)
  - `latex` (string, wrapped in `$$...$$`)
  - `contains_sum` (boolean)
  - `contains_product` (boolean)
  - `status` ("original" or "corrected")

Rules:
1. Include the standalone formulas in reading order.
2. Add one extra corrected formula entry to fix the mismatched bracket typo in the Hamiltonian expression.
3. Keep JSON valid UTF-8 and deterministic (no comments, no trailing commas).
4. Do not output any files other than `/root/transfer1_formula_catalog.json`.
