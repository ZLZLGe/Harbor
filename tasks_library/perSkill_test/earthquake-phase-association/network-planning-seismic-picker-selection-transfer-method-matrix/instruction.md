You are preparing a method recommendation matrix for a regional seismic monitoring program that runs several very different deployments.

Inputs are in `/root/planning_inputs/`:

- `deployment_matrix.csv`: one row per monitoring scenario with structured planning constraints.
- `scenario_briefs.md`: additional plain-text notes from the monitoring leads.

Your task is to choose the most appropriate method family for each scenario and write `/root/method_matrix.json`.

Rules:

1. Produce one recommendation for every `scenario_id` listed in `deployment_matrix.csv`.
2. Choose exactly one `recommended_method` per scenario from:
   - `sta_lta`
   - `deep_learning`
   - `template_matching`
   - `manual`
3. Write a JSON object with exactly these top-level keys:
   - `matrix_version`
   - `recommendations`
4. Set `matrix_version` to the string `1.0`.
5. `recommendations` must be a JSON array sorted by `scenario_id` ascending.
6. Each item in `recommendations` must be a JSON object with exactly these keys:
   - `scenario_id`
   - `recommended_method`
   - `reason`
7. `reason` must be plain text in 1 or 2 sentences. It must mention at least two concrete constraints from that scenario, such as latency, station type, template availability, analyst review requirements, or sensitivity goals.
8. Keep the recommendations scenario-specific. This is a planning exercise across multiple deployments, not a single universal default.

No extra output files are required.
