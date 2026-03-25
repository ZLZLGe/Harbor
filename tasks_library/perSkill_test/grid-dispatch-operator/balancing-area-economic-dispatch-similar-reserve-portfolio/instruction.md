You are preparing a one-hour balancing-area dispatch for an evening peak interval.

Read `/root/balancing_area_portfolio.json` and determine the least-cost feasible energy and reserve awards for the listed units.

All units are already online for this interval. Your dispatch must satisfy all of the following:

1. Total scheduled energy equals `load_MW`.
2. Total scheduled reserve equals `reserve_requirement_MW`.
3. For every unit, `p_min_MW <= energy_MW <= p_max_MW`.
4. For every unit, `0 <= reserve_MW <= reserve_offer_cap_MW`.
5. For every unit, `energy_MW + reserve_MW <= p_max_MW`.

Minimize the total hourly procurement cost:

- Energy cost = `energy_MW * energy_offer_dollars_per_MWh`
- Reserve cost = `reserve_MW * reserve_offer_dollars_per_MW`

Write `/root/balancing_dispatch_report.json` with this structure:

```json
{
  "balancing_area": "Northshore Balancing Authority",
  "interval_start": "2026-08-17T19:00:00-05:00",
  "generator_dispatch": [
    {
      "unit_id": "RB_CT1",
      "fuel": "gas",
      "energy_MW": 75.0,
      "reserve_MW": 45.0,
      "unused_headroom_MW": 0.0
    }
  ],
  "totals": {
    "load_MW": 600.0,
    "energy_MW": 600.0,
    "reserve_requirement_MW": 150.0,
    "reserve_MW": 150.0,
    "total_cost_dollars_per_hour": 14697.5,
    "uncommitted_margin_MW": 10.0
  }
}
```

Additional output requirements:

- Keep `generator_dispatch` in the same order as the `units` array from the input file.
- Use the same `balancing_area` and `interval_start` strings from the input file.
- `unused_headroom_MW` must equal `p_max_MW - energy_MW - reserve_MW` for each unit.
- `uncommitted_margin_MW` must equal the sum of all `unused_headroom_MW` values.
- Use JSON numbers for all MW and cost values.
