You have ranking priorities at `/root/data/ranking_cases.csv`.

Create `/root/transfer1_method_ranking.csv`.

Requirements:
1. Preserve input row order.
2. Write exactly these columns: `case_id`, `first_choice`, `second_choice`, `third_choice`, `fourth_choice`.
3. Use this mapping:
   - `tiny-known` -> `template_matching`, `deep_learning`, `manual`, `sta_lta`
   - `sparse-unknown` -> `deep_learning`, `manual`, `sta_lta`, `template_matching`
   - `rapid-screen` -> `sta_lta`, `deep_learning`, `manual`, `template_matching`
   - `quality-audit` -> `manual`, `deep_learning`, `template_matching`, `sta_lta`
4. Do not read anything from `/tests`.
