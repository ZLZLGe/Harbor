You are supporting a transmission operations team that wants a fast N-1 screening note for a fixed network snapshot.

The environment contains:

- `transmission_snapshot.json`: a simplified transmission model with
  - `baseMVA`
  - `slack_bus`
  - `buses`: each bus has a non-contiguous `bus` ID and a fixed `net_injection_MW`
  - `branches`: each branch has `branch_id`, `from_bus`, `to_bus`, `x_pu`, and `limit_MW`
- `contingency.json`: the single-line outage to study and the sizes of the ranked comparison lists

Run a DC power flow for:
1. The intact network
2. The contingency case with the specified branch removed from service

Use the fixed bus injections from the snapshot, anchor the slack bus angle at 0, and compute branch flows as:

`flow_MW = (theta_from - theta_to) / x_pu * baseMVA`

Treat a branch as overloaded when `loading_pct >= overload_threshold_pct` from `contingency.json`.

Then write `/root/contingency_flow_report.json` with this structure:

```json
{
  "scenario": {
    "name": "North corridor single-line outage",
    "slack_bus": 101,
    "outaged_branch_id": "L5",
    "outaged_branch": {
      "branch_id": "L5",
      "from_bus": 205,
      "to_bus": 611
    }
  },
  "base_case": {
    "bus_angles_deg": [
      {"bus": 101, "angle_deg": 0.0}
    ],
    "branch_flows": [
      {
        "branch_id": "L1",
        "from_bus": 101,
        "to_bus": 205,
        "flow_MW": 120.0,
        "limit_MW": 120.0,
        "loading_pct": 100.0
      }
    ],
    "overloads": [
      {
        "branch_id": "L13",
        "from_bus": 205,
        "to_bus": 450,
        "flow_MW": 60.0472,
        "limit_MW": 50.0,
        "loading_pct": 120.0944
      }
    ]
  },
  "outage_case": {
    "bus_angles_deg": [
      {"bus": 101, "angle_deg": 0.0}
    ],
    "branch_flows": [
      {
        "branch_id": "L1",
        "from_bus": 101,
        "to_bus": 205,
        "flow_MW": 120.0,
        "limit_MW": 120.0,
        "loading_pct": 100.0
      }
    ],
    "overloads": []
  },
  "comparison": {
    "largest_angle_shifts": [
      {
        "bus": 611,
        "base_angle_deg": -20.8669,
        "outage_angle_deg": -25.3161,
        "absolute_shift_deg": 4.4492
      }
    ],
    "largest_flow_redistribution": [
      {
        "branch_id": "L2",
        "from_bus": 205,
        "to_bus": 309,
        "base_flow_MW": 74.8349,
        "outage_flow_MW": 97.5301,
        "absolute_delta_MW": 22.6952
      }
    ],
    "overload_count_change": 1,
    "newly_overloaded_branches": ["L2"]
  }
}
```

Requirements:

- Keep bus angle lists ordered by the bus order in `transmission_snapshot.json`.
- Keep branch flow lists ordered by the branch order in `transmission_snapshot.json`.
- Keep each `overloads` list in the same relative order as the corresponding `branch_flows` list.
- In `outage_case.branch_flows`, omit the outaged branch because it is out of service.
- In `comparison.largest_angle_shifts`, return the top `top_angle_shift_count` buses ranked by absolute angle change, breaking ties by smaller bus number first.
- In `comparison.largest_flow_redistribution`, return the top `top_flow_redistribution_count` in-service branches ranked by absolute flow change, excluding the outaged branch and breaking ties by `branch_id` ascending.
- Define `comparison.overload_count_change` as `len(outage_case.overloads) - len(base_case.overloads)`.
- `newly_overloaded_branches` should list branch IDs that are not overloaded in the base case but are overloaded in the outage case, sorted ascending.
- Round every reported floating-point value in the JSON report to 4 decimal places.
- Use the unrounded loading percentage only for deciding whether a branch is overloaded, then round the reported `loading_pct` value to 4 decimal places.
- Compute each `absolute_shift_deg` from the reported `base_angle_deg` and `outage_angle_deg` values for that bus, then round the result to 4 decimal places.
- Compute each `absolute_delta_MW` from the reported `base_flow_MW` and `outage_flow_MW` values for that branch, then round the result to 4 decimal places.

Only the JSON report is required.
