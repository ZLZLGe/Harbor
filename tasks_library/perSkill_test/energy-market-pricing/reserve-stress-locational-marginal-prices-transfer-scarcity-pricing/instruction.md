You are supporting an RTO market monitoring team that is reviewing whether reserve scarcity spilled into energy prices during an evening operating hour.

The compact system snapshot is stored in `reserve_pocket_network.json`, in MATPOWER-style JSON format. Scenario settings, regional groupings, and reporting thresholds are stored in `reserve_stress_event.json`.

Use the same DC-OPF with reserve co-optimization model as the source task:
1. DC nodal power balance at every bus
2. Generator output limits and line thermal limits
3. A single system spinning-reserve requirement with standard capacity coupling

Run two market-clearing scenarios:
1. `base_case`, using the network exactly as given
2. `reserve_stress_case`, after applying every change listed in `reserve_stress_event.json`
   - replace the system reserve requirement with `stress_reserve_requirement_MW`
   - replace the reserve capacity of each listed generator with its `stress_reserve_capacity_MW`

For each scenario, report:
- `scenario_id`
- `reserve_requirement_MW`
- total system cost
- system reserve clearing price
- nodal marginal price at every bus, sorted by ascending bus number
- all lines with loading at or above `binding_threshold_pct`, sorted by ascending `from` and then `to`

Then build a scarcity-transfer assessment:
- `system_cost_increase_dollars_per_hour` = reserve-stress-case cost minus base-case cost
- `reserve_mcp_increase_dollars_per_MWh` = reserve-stress-case reserve MCP minus base-case reserve MCP
- `largest_lmp_increases` must contain the top `report_top_n_buses` buses ranked by descending LMP increase and then ascending bus number
- `regional_price_impacts` must cover every region in `regions`, in the same order as listed in `reserve_stress_event.json`
- for each region, compute:
  - `average_base_lmp_dollars_per_MWh`
  - `average_stress_lmp_dollars_per_MWh`
  - `average_lmp_change_dollars_per_MWh`
  - `max_lmp_change_dollars_per_MWh`
  - `affected_bus_count`, where a bus is affected if its LMP increase is strictly greater than 0
- `most_affected_region_id` is the region with the largest `average_lmp_change_dollars_per_MWh`; break ties by lexicographically smaller `region_id`
- `scarcity_pricing_transmitted_to_energy` is `true` if both of the following hold:
  - `reserve_mcp_increase_dollars_per_MWh` is at least `reserve_mcp_increase_threshold_dollars_per_MWh`
  - the `average_lmp_change_dollars_per_MWh` of `most_affected_region_id` is at least `regional_average_lmp_increase_threshold_dollars_per_MWh`

Write `/root/scarcity_pricing_report.json` with this structure:

```json
{
  "base_case": {
    "scenario_id": "base_case",
    "reserve_requirement_MW": 120.0,
    "total_cost_dollars_per_hour": 0.0,
    "reserve_mcp_dollars_per_MWh": 0.0,
    "lmp_by_bus": [
      {"bus": 1, "lmp_dollars_per_MWh": 0.0}
    ],
    "binding_lines": [
      {
        "from": 1,
        "to": 2,
        "flow_MW": 0.0,
        "limit_MW": 0.0,
        "loading_pct": 0.0
      }
    ]
  },
  "reserve_stress_case": {
    "scenario_id": "reserve_stress_case",
    "reserve_requirement_MW": 200.0,
    "total_cost_dollars_per_hour": 0.0,
    "reserve_mcp_dollars_per_MWh": 0.0,
    "lmp_by_bus": [
      {"bus": 1, "lmp_dollars_per_MWh": 0.0}
    ],
    "binding_lines": []
  },
  "scarcity_transfer_assessment": {
    "system_cost_increase_dollars_per_hour": 0.0,
    "reserve_mcp_increase_dollars_per_MWh": 0.0,
    "largest_lmp_increases": [
      {
        "bus": 3,
        "region_id": "south_load_pocket",
        "base_lmp_dollars_per_MWh": 0.0,
        "stress_lmp_dollars_per_MWh": 0.0,
        "delta_dollars_per_MWh": 0.0
      }
    ],
    "regional_price_impacts": [
      {
        "region_id": "upstream_hub",
        "region_name": "Upstream Hub",
        "buses": [1, 2],
        "average_base_lmp_dollars_per_MWh": 0.0,
        "average_stress_lmp_dollars_per_MWh": 0.0,
        "average_lmp_change_dollars_per_MWh": 0.0,
        "max_lmp_change_dollars_per_MWh": 0.0,
        "affected_bus_count": 0
      }
    ],
    "most_affected_region_id": "south_load_pocket",
    "scarcity_pricing_transmitted_to_energy": true,
    "assessment_basis": {
      "reserve_mcp_increase_threshold_dollars_per_MWh": 1.0,
      "regional_average_lmp_increase_threshold_dollars_per_MWh": 20.0
    }
  }
}
```

Requirements:
- Include every bus exactly once in each `lmp_by_bus` list.
- Use numeric values, not strings, for all reported metrics.
- Round reported prices, costs, flows, limits, loadings, and deltas to 2 decimals.
