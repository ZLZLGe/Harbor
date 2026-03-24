You are supporting an offshore transmission planning team that needs a short maintenance-risk note for a wind export grid.

The environment contains:

- `offshore_grid.json`: a simplified offshore network model with
  - `baseMVA`
  - `slack_node`
  - `landing_points`
  - `export_cable_ids`
  - `nodes`: each node has a non-contiguous `node` ID, a `kind`, and a fixed `net_injection_MW`
  - `cables`: each cable has `cable_id`, `from_node`, `to_node`, `x_pu`, `rating_MW`, and `cable_type`
- `maintenance_outage.json`: the maintenance scenario to study and the ranking settings

Run a DC power flow for:
1. The normal topology with all cables in service
2. The maintenance topology with the specified cable removed from service

Use the fixed node injections from `offshore_grid.json`, anchor the slack node angle at 0, and compute each in-service cable flow as:

`flow_MW = (theta_from - theta_to) / x_pu * baseMVA`

Treat a cable as overloaded when `loading_pct >= loading_alert_pct` from `maintenance_outage.json`.

Then write `/root/offshore_cable_stress_report.json` with this structure:

```json
{
  "scenario": {
    "name": "West export string maintenance outage",
    "slack_node": 7001,
    "maintenance_outage_cable_id": "E1",
    "maintenance_outage": {
      "cable_id": "E1",
      "from_node": 5201,
      "to_node": 6101,
      "cable_type": "export"
    }
  },
  "normal_topology": {
    "export_cable_loadings": [
      {
        "cable_id": "E1",
        "from_node": 5201,
        "to_node": 6101,
        "flow_MW": 225.1649,
        "rating_MW": 230.0,
        "loading_pct": 97.8978
      }
    ],
    "overloaded_elements": []
  },
  "maintenance_topology": {
    "export_cable_loadings": [
      {
        "cable_id": "E2",
        "from_node": 5250,
        "to_node": 6155,
        "flow_MW": 237.0118,
        "rating_MW": 190.0,
        "loading_pct": 124.743
      }
    ],
    "overloaded_elements": [
      {
        "cable_id": "T1",
        "from_node": 5201,
        "to_node": 5250,
        "flow_MW": 320.0,
        "rating_MW": 120.0,
        "loading_pct": 266.6667,
        "cable_type": "transfer"
      }
    ]
  },
  "comparison": {
    "landing_point_angle_shifts_deg": [
      {
        "node": 6101,
        "normal_angle_deg": 6.5142,
        "maintenance_angle_deg": 2.8715,
        "absolute_shift_deg": 3.6426
      }
    ],
    "largest_rerouted_cables": [
      {
        "cable_id": "T1",
        "cable_type": "transfer",
        "from_node": 5201,
        "to_node": 5250,
        "normal_flow_MW": 94.8351,
        "maintenance_flow_MW": 320.0,
        "absolute_delta_MW": 225.1649
      }
    ],
    "newly_overloaded_elements": ["E2", "E3", "T1"]
  }
}
```

Requirements:

- Keep `normal_topology.export_cable_loadings` ordered by `export_cable_ids` in `offshore_grid.json`.
- Keep `maintenance_topology.export_cable_loadings` ordered by the same export cable order, but omit the maintenance-outage cable because it is out of service.
- Keep each `overloaded_elements` list ordered by the cable order in `offshore_grid.json`.
- `landing_point_angle_shifts_deg` must include every node listed in `landing_points`, ranked by `absolute_shift_deg` descending and then by smaller node number first.
- `largest_rerouted_cables` must exclude the maintenance-outage cable and return the top `top_rerouted_count` in-service cables ranked by `absolute_delta_MW` descending, breaking ties by `cable_id` ascending.
- `newly_overloaded_elements` must list the cable IDs that are not overloaded in the normal topology but are overloaded in the maintenance topology, sorted ascending.
- Round every reported numeric value to 4 decimal places.

Only the JSON report is required.
