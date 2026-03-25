You have local cataloging scenarios at `/root/data/picker_scenarios.json`.

Create `/root/similar_picker_brief.json`.

Requirements:
1. Output valid JSON with top-level keys `scenario_count` and `recommendations`.
2. `recommendations` must be sorted by `scenario_id`.
3. Each recommendation must contain exactly these keys: `scenario_id`, `recommended_method`, `reason_code`, `needs_manual_review`.
4. Use these rules:
   - if `prior_templates` is `true` and `target_signal` is `small`, choose `template_matching`, `template-sensitive`, `false`
   - else if `network_density` is `sparse`, choose `deep_learning`, `sparse-network`, `false`
   - else if `urgency` is `realtime`, choose `sta_lta`, `realtime-large-signal`, `true`
   - otherwise choose `deep_learning`, `balanced-catalog`, `false`
5. Do not read anything from `/tests`.
