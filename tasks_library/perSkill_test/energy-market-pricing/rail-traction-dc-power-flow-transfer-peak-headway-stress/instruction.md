You are supporting a rail electrification planning team that needs a short stress note for a traction power network.

The environment contains:

- `rail_traction_network.json`: a simplified traction network model with
  - `baseMVA`
  - `slack_bus`
  - `traction_substation_bus_ids`
  - `buses`: each bus has a non-contiguous `bus` ID, a `name`, and a `kind`
  - `sections`: each feeder section has `section_id`, `from_bus`, `to_bus`, `x_pu`, `rating_MW`, `corridor`, and `section_type`
- `timetable_patterns.json`: the two timetable-driven injection patterns and the ranking settings

Run a DC power flow for:
1. The shoulder-service injection pattern from `shoulder_bus_injections_MW`
2. The peak-headway injection pattern from `peak_headway_bus_injections_MW`

Use the bus injections exactly as provided in `timetable_patterns.json`, anchor the slack bus angle at 0, and compute each section flow as:

`flow_MW = (theta_from - theta_to) / x_pu * baseMVA`

Treat a section as overloaded when:

`loading_pct >= loading_alert_pct`

For each corridor, define its peak loading percentage within a scenario as the maximum `loading_pct` among sections in that corridor. The corridor incremental stress is:

`peak_headway_peak_loading_pct - shoulder_peak_loading_pct`

Then write `/root/traction_peak_stress_report.json` with this structure:

```json
{
  "scenario": {
    "name": "Peak headway stress check for the Harbor Loop traction grid",
    "slack_bus": 8000,
    "shoulder_pattern": "Shoulder timetable",
    "peak_headway_pattern": "Peak headway timetable",
    "traction_substation_bus_ids": [8000, 8110, 8220, 8330]
  },
  "shoulder_service": {
    "substation_angle_profile_deg": [
      {"bus": 8000, "angle_deg": 0.0}
    ],
    "feeder_loadings": [
      {
        "section_id": "EL-1",
        "from_bus": 8110,
        "to_bus": 8411,
        "corridor": "East Line",
        "section_type": "line_section",
        "flow_MW": 35.2432,
        "rating_MW": 52.0,
        "loading_pct": 67.7754
      }
    ],
    "overloaded_sections": []
  },
  "peak_headway_service": {
    "substation_angle_profile_deg": [
      {"bus": 8000, "angle_deg": 0.0}
    ],
    "feeder_loadings": [
      {
        "section_id": "CX-2",
        "from_bus": 8220,
        "to_bus": 8522,
        "corridor": "Cross Link",
        "section_type": "tie_section",
        "flow_MW": 40.4978,
        "rating_MW": 40.0,
        "loading_pct": 101.2445
      }
    ],
    "overloaded_sections": [
      {
        "section_id": "CX-2",
        "from_bus": 8220,
        "to_bus": 8522,
        "corridor": "Cross Link",
        "section_type": "tie_section",
        "flow_MW": 40.4978,
        "rating_MW": 40.0,
        "loading_pct": 101.2445
      }
    ]
  },
  "comparison": {
    "largest_substation_angle_shifts_deg": [
      {
        "bus": 8330,
        "shoulder_angle_deg": -3.7399,
        "peak_headway_angle_deg": -4.9411,
        "absolute_shift_deg": 1.2012
      }
    ],
    "newly_overloaded_sections": ["CX-2", "EL-1", "SB-2"],
    "corridors_with_highest_incremental_stress": [
      {
        "corridor": "South Branch",
        "shoulder_peak_loading_pct": 68.2531,
        "peak_headway_peak_loading_pct": 100.5523,
        "incremental_stress_pct": 32.2992,
        "peak_limiting_section_id": "SB-2"
      }
    ]
  }
}
```

Requirements:

- Keep both `substation_angle_profile_deg` lists ordered by `traction_substation_bus_ids` in `rail_traction_network.json`.
- Keep both `feeder_loadings` lists ordered by the section order in `rail_traction_network.json`.
- Keep both `overloaded_sections` lists ordered by the same section order.
- `largest_substation_angle_shifts_deg` must consider the traction substations listed in `traction_substation_bus_ids`, rank them by `absolute_shift_deg` descending and then by smaller bus number first, and truncate to `top_substation_shift_count`.
- `newly_overloaded_sections` must list section IDs that are not overloaded in shoulder service but are overloaded in peak headway service, sorted ascending.
- `corridors_with_highest_incremental_stress` must keep only corridors with positive incremental stress, rank them by `incremental_stress_pct` descending and then by `corridor` ascending, and truncate to `top_corridor_count`.
- For each corridor entry, `peak_limiting_section_id` must be the section with the highest `loading_pct` in the peak-headway scenario for that corridor, breaking ties by `section_id` ascending.
- Round every reported numeric value to 4 decimal places.

Only the JSON report is required.
