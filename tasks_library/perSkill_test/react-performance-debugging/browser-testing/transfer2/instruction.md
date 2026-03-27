Review the dashboard request evidence in `/root/data/` and write `/root/admin_dashboard_request_matrix.csv`.

The capture comes from an operations dashboard whose first paint is delayed by backend calls. Use the waterfall snapshot together with the request role notes to classify each request into an optimization matrix.

Requirements:
- Keep the CSV header exactly `request_url,duration_ms,loading_pattern,criticality,recommended_action`.
- Include one row for each captured backend request, in the same order as the waterfall.
- Use the normalized loading pattern and criticality labels from the evidence.
- Choose the single recommended action that best reduces first-paint latency for each row.

Output contract:
- Write CSV only.
- Save the final file exactly as `/root/admin_dashboard_request_matrix.csv`.
