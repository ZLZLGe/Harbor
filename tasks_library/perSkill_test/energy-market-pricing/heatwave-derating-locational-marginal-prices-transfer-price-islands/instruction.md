You are supporting an RTO operations desk that is preparing an emergency pricing note during a severe heatwave.

The compact network snapshot is stored in `compact_heatwave_network.json`, in MATPOWER-style JSON format. Heat-stress line deratings and reporting settings are stored in `heatwave_event.json`.

Use the same DC-OPF with reserve co-optimization model as the source task:
1. DC nodal power balance at every bus
2. Generator output limits and line thermal limits
3. A single system spinning-reserve requirement with standard capacity coupling

Run two market-clearing scenarios:
1. `pre_event`, using the network exactly as given
2. `emergency_case`, applying every derated thermal limit from `heatwave_event.json`

For each scenario, report:
- total system cost
- system reserve clearing price
- nodal marginal price at every bus, sorted by ascending bus number
- all lines with loading at or above `binding_threshold_pct`, sorted by ascending `from` and then `to`

Then build a risk summary:
- `production_cost_increase_dollars_per_hour` = emergency-case cost minus pre-event cost
- `monitored_load_center_price_spikes` must cover every bus listed in `monitored_load_centers`, sorted by descending price increase and then ascending bus number
- assign `risk_tier` using the price increase at each monitored load center:
  - `severe` for increases greater than or equal to `severe_price_increase_threshold`
  - `elevated` for increases greater than or equal to `elevated_price_increase_threshold` but below the severe threshold
  - `watch` otherwise
- `newly_binding_derated_lines` must include only the derated lines that were not binding in `pre_event` but are binding in `emergency_case`, sorted by ascending `from` and then `to`
- `price_island_summary` must cover the buses in `island_buses` and compare them against `reference_bus`

Write `/root/price_island_risk.json` with this structure:

```json
{
  "pre_event": {
    "scenario_id": "pre_event",
    "total_cost_dollars_per_hour": 0.0,
    "reserve_mcp_dollars_per_MWh": 0.0,
    "lmp_by_bus": [
      {"bus": 2, "lmp_dollars_per_MWh": 0.0}
    ],
    "binding_lines": [
      {
        "from": 64,
        "to": 1501,
        "flow_MW": 0.0,
        "limit_MW": 0.0,
        "loading_pct": 0.0
      }
    ]
  },
  "emergency_case": {
    "scenario_id": "emergency_case",
    "total_cost_dollars_per_hour": 0.0,
    "reserve_mcp_dollars_per_MWh": 0.0,
    "lmp_by_bus": [
      {"bus": 2, "lmp_dollars_per_MWh": 0.0}
    ],
    "binding_lines": []
  },
  "risk_summary": {
    "production_cost_increase_dollars_per_hour": 0.0,
    "monitored_load_center_price_spikes": [
      {
        "bus": 1501,
        "pre_event_lmp": 0.0,
        "emergency_lmp": 0.0,
        "increase_dollars_per_MWh": 0.0,
        "risk_tier": "severe"
      }
    ],
    "newly_binding_derated_lines": [
      {
        "from": 64,
        "to": 1501,
        "base_limit_MW": 0.0,
        "emergency_limit_MW": 0.0,
        "emergency_flow_MW": 0.0
      }
    ],
    "price_island_summary": {
      "reference_bus": 629,
      "island_buses": [64, 1501],
      "island_load_MW": 0.0,
      "average_emergency_lmp_dollars_per_MWh": 0.0,
      "premium_vs_reference_bus_dollars_per_MWh": 0.0
    }
  }
}
```

Requirements:
- Include every bus exactly once in each `lmp_by_bus` list.
- Use numeric values, not strings, for all metrics.
- Round all reported prices, costs, flows, limits, loadings, and deltas to 2 decimals.
