Create a syntax-focused formula errata ledger in JSON format.

Input file:
- `/root/input/errata_candidates.json`

Output file:
- `/root/transfer1_formula_ledger.json`

Output schema:
- top-level JSON array
- each entry must contain:
  - `formula_id` (string)
  - `normalized_formula` (string)
  - `requires_fix` (boolean)
  - `fixed_formula` (string)
  - `reason` (string)

Rules:
1. Normalize formula text by removing `\\tag{...}` and trailing commas/periods.
2. Set `requires_fix=true` if the formula contains `\\left[` together with `\\right)`.
3. For `requires_fix=true`, fix only that bracket mismatch (`\\left[` -> `\\left(` and matching `\\right)` remains as the closing parenthesis).
4. Keep output entries in the same order as input.
5. Write valid UTF-8 JSON with two-space indentation.
