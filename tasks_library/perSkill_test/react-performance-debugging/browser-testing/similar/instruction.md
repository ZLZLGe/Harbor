Review the measurement captures in `/root/data/` and write `/root/storefront_perf_diagnosis.json`.

Use the provided page, API, and bundle snapshots to summarize the storefront's current bottlenecks.

Requirements:
- Report `homepage_total_ms`, `products_api_total_ms`, `checkout_total_ms`, and `compare_initial_js_kb` as numbers.
- Set `top_bottleneck` to the single most urgent issue across the captures.
- Fill `root_causes` with the four normalized issue codes supported by the evidence.
- Fill `priority_order` with the three remediation actions in execution order.
- Preserve the two runtime constraints listed in `constraints.json` inside `must_preserve`.

Output contract:
- Write valid JSON only.
- Save the final file exactly as `/root/storefront_perf_diagnosis.json`.
