You have deployment constraints at `/root/data/deployment_cases.json`.

Create `/root/transfer2_deployment_plan.json`.

Requirements:
1. Output valid JSON with top-level keys `case_count` and `plans`.
2. `plans` must be sorted by `case_id`.
3. Each plan must contain exactly these keys: `case_id`, `preferred_method`, `secondary_method`, `why`.
4. Use these rules:
   - if `prior_templates` is `true`, choose `template_matching`, `deep_learning`, `template-available`
   - else if `compute_budget` is `low`, choose `sta_lta`, `manual`, `low-compute`
   - else if `network_density` is `sparse`, choose `deep_learning`, `manual`, `sparse-network`
   - otherwise choose `deep_learning`, `sta_lta`, `balanced-default`
5. Do not read anything from `/tests`.
