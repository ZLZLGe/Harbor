You are supporting a capacity engineering team for a multi-building data center campus. They want a concise rebalance note comparing the current hall placement against a planned weekend redistribution of rack load.

The environment contains:

- `campus_network.json`: a simplified campus distribution model with
  - `baseMVA`
  - `slack_bus`
  - `hall_bus_ids`
  - `tie_feeder_ids`
  - `buses`: each bus has a non-contiguous `bus` ID, a `name`, and a `kind`
  - `feeders`: each feeder has `feeder_id`, `from_bus`, `to_bus`, `x_pu`, `rating_MW`, and `feeder_class`
- `rebalance_plan.json`: the two hall-placement scenarios and the ranking settings

Run a DC power flow for:
1. The baseline hall placement from `baseline_bus_injections_MW`
2. The rebalanced hall placement from `rebalanced_bus_injections_MW`

Use the bus injections exactly as provided in `rebalance_plan.json`, anchor the slack bus angle at 0, and compute each feeder flow as:

`flow_MW = (theta_from - theta_to) / x_pu * baseMVA`

Treat a tie feeder as overloaded when:

`loading_pct >= loading_alert_pct`

Then write `/root/campus_rebalance_summary.json` with this structure:

```json
{
  "scenario": {
    "name": "GPU hall load migration between north and south campuses",
    "slack_bus": 5000,
    "baseline_layout": "Legacy hall placement",
    "rebalanced_layout": "Campus feeder rebalance plan",
    "tie_feeder_ids": ["T-N-S", "T-H"]
  },
  "baseline_layout": {
    "feeder_flows": [
      {
        "feeder_id": "UF-N",
        "from_bus": 5000,
        "to_bus": 5100,
        "feeder_class": "utility",
        "flow_MW": 245.5479,
        "rating_MW": 260.0,
        "loading_pct": 94.4415
      }
    ],
    "overloaded_ties": [
      {
        "feeder_id": "T-H",
        "from_bus": 6120,
        "to_bus": 6220,
        "feeder_class": "tie",
        "flow_MW": -19.1438,
        "rating_MW": 15.0,
        "loading_pct": 127.6256
      }
    ]
  },
  "rebalanced_layout": {
    "feeder_flows": [
      {
        "feeder_id": "UF-S",
        "from_bus": 5000,
        "to_bus": 5200,
        "feeder_class": "utility",
        "flow_MW": 214.589,
        "rating_MW": 240.0,
        "loading_pct": 89.4121
      }
    ],
    "overloaded_ties": []
  },
  "comparison": {
    "hall_bus_angle_changes_deg": [
      {
        "bus": 6110,
        "baseline_angle_deg": -15.5523,
        "rebalanced_angle_deg": -13.4833,
        "absolute_change_deg": 2.069
      }
    ],
    "feeders_with_most_relief": [
      {
        "feeder_id": "N-H1",
        "from_bus": 5100,
        "to_bus": 6110,
        "baseline_abs_flow_MW": 150.0,
        "rebalanced_abs_flow_MW": 110.0,
        "relief_MW": 40.0
      }
    ],
    "tie_overload_reduction_count": 2,
    "ties_relieved": ["T-H", "T-N-S"]
  }
}
```

Requirements:

- Keep both `feeder_flows` lists ordered by the feeder order in `campus_network.json`.
- Keep both `overloaded_ties` lists ordered by `tie_feeder_ids` in `campus_network.json`.
- `hall_bus_angle_changes_deg` must include the hall buses listed in `hall_bus_ids`, ranked by `absolute_change_deg` descending and then by smaller bus number first, and truncated to `top_angle_change_count`.
- `feeders_with_most_relief` must consider every feeder in service, compute `relief_MW = max(0, abs(baseline_flow_MW) - abs(rebalanced_flow_MW))`, keep only feeders with positive relief, rank them by `relief_MW` descending and then by `feeder_id` ascending, and truncate to `top_relief_count`.
- `tie_overload_reduction_count` is the number of overloaded ties in the baseline layout minus the number of overloaded ties in the rebalanced layout.
- `ties_relieved` must list tie feeder IDs that are overloaded in the baseline layout but not overloaded in the rebalanced layout, sorted ascending.
- Round every reported numeric value to 4 decimal places.

Only the JSON summary is required.
