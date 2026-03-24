Analyze `/root/cold_chain_routes.xlsx` and write `/root/route_alerts.json`.

The workbook contains these relevant sheets:

- `Dispatch Log`
- `Contract Terms`
- `Lane Thresholds`
- `Client Priority`

Only the rows in `Dispatch Log` that sit between the marker cells `ACTIVE ROUTES START` and `ACTIVE ROUTES END` are part of the current dispatch window. Ignore the archive section.

For each active route:

1. Compute `on_time_ratio = on_time_stops / planned_stops`.
2. Look up the matching contract row by `Contract ID`.
3. Look up the matching lane row by `Lane`.
4. Look up the matching client row by `Client Code`.
5. Compute penalties:
   - `late_penalty = late_stops * late_penalty_per_stop`
   - `temp_penalty = temp_excursions * temp_penalty_per_excursion`
   - If `max_temp_overrun_c >= critical_overrun_c`, multiply `temp_penalty` by `severe_temp_multiplier`.
   - `spoilage_penalty = spoilage_crates * spoilage_penalty_per_crate`
   - `rebate_penalty = revenue * rebate_pct` only when `on_time_ratio < min_on_time_ratio`
6. Compute `adjusted_profit = revenue - linehaul_cost - cooling_cost - late_penalty - temp_penalty - spoilage_penalty - rebate_penalty`.
   Round `adjusted_profit` to 2 decimal places.
7. Compute `risk_score` as:
   - `late_stops * late_points`
   - `+ temp_excursions * temp_points`
   - `+ spoilage_crates * spoilage_points`
   - `+ critical_bonus` if `max_temp_overrun_c >= critical_overrun_c`
   - otherwise `+ warning_bonus` if `max_temp_overrun_c >= warning_overrun_c`
   - otherwise `+ 0`
   - `+ priority_points`
8. Convert `risk_score` to an initial level:
   - `Critical` if `risk_score >= critical_score`
   - `High` if `risk_score >= high_score`
   - `Moderate` if `risk_score >= 4`
   - otherwise `Low`
9. If `priority_tier` is `Critical`, `temp_excursions > 0`, and the initial level is `Moderate`, upgrade the final level to `High`.

Include a route in the output if either of these is true:

- the final `risk_level` is `High` or `Critical`
- `adjusted_profit` is below the client's `profit_floor`

Write JSON with exactly this top-level shape:

```json
{
  "routes_to_escalate": [
    {
      "route_id": "RT-000",
      "lane": "Metro",
      "client_code": "CL-XXX",
      "priority_tier": "Priority",
      "adjusted_profit": 0.0,
      "risk_score": 0,
      "risk_level": "Low",
      "reasons": [
        "profit_below_floor"
      ]
    }
  ]
}
```

Rules for the `reasons` array:

- Add `profit_below_floor` if `adjusted_profit < profit_floor`
- Add `temp_control_breach` if `temp_excursions > 0`
- Add `service_failures` if `late_stops > 0`
- Add `spoilage_claim` if `spoilage_crates > 0`
- Add `priority_upgrade` only if step 9 upgraded the route
- Keep the reasons in exactly the order listed above

Sort `routes_to_escalate` by:

1. `risk_level` severity in this order: `Critical`, `High`, `Moderate`, `Low`
2. `adjusted_profit` ascending
3. `route_id` ascending

Do not write any extra keys or files.
