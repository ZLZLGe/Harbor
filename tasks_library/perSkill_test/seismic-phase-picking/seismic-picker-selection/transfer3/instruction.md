You have review cases at `/root/data/review_cases.csv`.

Create `/root/transfer3_review_policy.csv`.

Requirements:
1. Preserve input row order.
2. Write exactly these columns: `case_id`, `preferred_method`, `auto_use`, `manual_review_level`.
3. Use this mapping:
   - `sta_lta` -> `screening-only`, `high`
   - `deep_learning` -> `catalog-first-pass`, `medium`
   - `template_matching` -> `sequence-refinement`, `medium`
   - `manual` -> `manual-only`, `high`
4. Do not read anything from `/tests`.
