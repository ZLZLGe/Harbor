You are covering the reserve watch desk after a dispatch-and-reserve plan has already been proposed.

The file `network_snapshot.json` contains a MATPOWER-format network snapshot.  
The file `proposed_schedule.json` contains the proposed generator schedule, keyed by 1-based generator row id.

Review the proposed plan and generate `/root/dispatch_audit.json` with this structure:

```json
{
  "checks": {
    "generation_matches_load": true,
    "reserve_requirement_met": false,
    "all_reserves_within_generator_limits": true,
    "all_generators_within_capacity_coupling": false
  },
  "totals": {
    "load_MW": 144839.06,
    "scheduled_generation_MW": 144839.06,
    "generation_minus_load_MW": 0.0,
    "scheduled_reserve_MW": 4483.85,
    "reserve_requirement_MW": 5923.5,
    "reserve_shortfall_MW": 1439.65
  },
  "reserve_capacity_violations": [
    {
      "id": 17,
      "bus": 120,
      "scheduled_reserve_MW": 55.0,
      "reserve_capacity_MW": 40.0,
      "excess_MW": 15.0
    }
  ],
  "capacity_coupling_violations": [
    {
      "id": 42,
      "bus": 301,
      "scheduled_output_MW": 900.0,
      "scheduled_reserve_MW": 150.0,
      "pmax_MW": 1000.0,
      "excess_MW": 50.0
    }
  ],
  "branch_loading_top3": [
    {
      "from": 1101,
      "to": 400,
      "flow_MW": -870.76,
      "rating_MW": 390.0,
      "loading_pct": 223.27
    }
  ]
}
```

Requirements:

- Use the MATPOWER bus numbers from the input data, not zero-based indices.
- Interpret the proposed schedule by generator row order: schedule entry `id = 1` refers to the first row of `gen`, `id = 2` to the second row, and so on.
- `generation_matches_load` should be `true` when the scheduled generation and total load match after rounding to 2 decimals.
- `reserve_requirement_met` should reflect whether total scheduled reserve meets `reserve_requirement`.
- `all_reserves_within_generator_limits` should reflect whether every scheduled reserve is less than or equal to the corresponding `reserve_capacity`.
- `all_generators_within_capacity_coupling` should reflect whether every generator satisfies `scheduled_output_MW + scheduled_reserve_MW <= Pmax`.
- Include every reserve-capacity violation in `reserve_capacity_violations`, sorted by `id` ascending.
- Include every capacity-coupling violation in `capacity_coupling_violations`, sorted by descending `excess_MW`, then ascending `id`.
- Compute branch flows under the proposed schedule with the standard DC power-flow approximation and report the three branches with the highest absolute loading percentage in `branch_loading_top3`, sorted by descending `loading_pct`.
- Round all reported MW values and percentages to 2 decimals.
