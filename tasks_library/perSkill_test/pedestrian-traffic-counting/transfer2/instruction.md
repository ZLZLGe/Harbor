A merged detection export is available at `/root/gate_counts.csv`.

Create `/root/transfer2_comparison.csv` with header:

`camera,in_count,out_count,net_flow,high_conf_unique`

Rules:
1. Use only rows where `kind == pedestrian`.
2. `in_count`: number of unique `person_id` with `direction == IN` per camera.
3. `out_count`: number of unique `person_id` with `direction == OUT` per camera.
4. `net_flow = in_count - out_count`.
5. `high_conf_unique`: number of unique `person_id` per camera where at least one row has `confidence >= 0.9`.
6. De-duplicate IDs according to the metric rules above.
7. Sort rows by `camera` ascending.
8. Output integers (no decimals).
