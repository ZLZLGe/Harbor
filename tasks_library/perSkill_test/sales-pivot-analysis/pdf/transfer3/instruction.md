Read the multi-page logistics lane packet in `/root/logistics_margin_packet.pdf` and create `/root/transfer3_lane_priority.tsv`.

The output TSV must use this header exactly:
`lane_id	hub	priority_tier	risk_score	action`

Requirements:
- Parse every table page in the PDF. The packet spans multiple pages and repeats the same columns.
- Treat each row as one logistics lane with on-time percentage, late stops, fuel variance percentage, and gross margin.
- Compute `risk_score` as `(100 - on_time_pct) + late_stops + max(fuel_variance_pct, 0) * 2`.
- Set `priority_tier` to `RED` if `risk_score >= 25` or `gross_margin < 15000`.
- Otherwise set `priority_tier` to `AMBER` if `risk_score >= 15`, else `GREEN`.
- Set `action` to:
  - `expedite audit` for `RED`
  - `monitor next cycle` for `AMBER`
  - `maintain plan` for `GREEN`
- Sort rows by descending `risk_score`, then ascending `lane_id`.

Save the final TSV to `/root/transfer3_lane_priority.tsv`.
