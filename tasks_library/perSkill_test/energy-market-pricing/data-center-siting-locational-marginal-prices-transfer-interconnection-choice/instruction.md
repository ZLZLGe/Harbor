You are supporting a transmission planning team that is screening where a new large data center block should interconnect.

The planning network snapshot is stored in `planning_snapshot.json`. Candidate interconnection buses and reporting thresholds are stored in `interconnection_candidates.json`.

Use the same DC-OPF with reserve co-optimization model as the source task:
1. DC nodal power balance at every bus
2. Generator output limits and line thermal limits
3. A single system spinning-reserve requirement with standard capacity coupling

Run one base scenario plus one siting scenario for each candidate bus:
1. `base_case`, using the snapshot exactly as given
2. For each candidate in `interconnection_candidates.json`, add the stated `added_load_MW` to that candidate's bus load and clear the market again

For `base_case`, report:
- total system cost
- system reserve clearing price
- nodal marginal price at every bus, sorted by ascending bus number
- all lines with loading at or above `binding_threshold_pct`, sorted by ascending `from` and then `to`

For each candidate siting scenario, report:
- `scenario_id`, `candidate_id`, `interconnection_bus`, and `added_load_MW`
- total system cost
- incremental system cost relative to `base_case`
- system reserve clearing price
- target-bus LMP at the candidate interconnection bus
- nodal marginal price at every bus, sorted by ascending bus number
- all newly binding lines: lines that are binding in the candidate scenario but were not binding in `base_case`, sorted by ascending `from` and then `to`
- a `price_diffusion_summary` with:
  - `affected_bus_count`: number of buses whose LMP changes by at least `price_diffusion_threshold_dollars_per_MWh` relative to `base_case`
  - `max_abs_lmp_change_dollars_per_MWh`
  - `average_abs_lmp_change_dollars_per_MWh`

Rank candidates using this rule:
1. Lower `incremental_cost_dollars_per_hour` is better
2. If tied, lower `target_bus_lmp_dollars_per_MWh` is better
3. If still tied, fewer affected buses is better
4. If still tied, fewer newly binding lines is better
5. If still tied, lower `interconnection_bus` is better

Write `/root/interconnection_choice.json` with this structure:

```json
{
  "base_case": {
    "scenario_id": "base_case",
    "total_cost_dollars_per_hour": 0.0,
    "reserve_mcp_dollars_per_MWh": 0.0,
    "lmp_by_bus": [
      {"bus": 101, "lmp_dollars_per_MWh": 0.0}
    ],
    "binding_lines": [
      {
        "from": 205,
        "to": 330,
        "flow_MW": 0.0,
        "limit_MW": 0.0,
        "loading_pct": 0.0
      }
    ]
  },
  "candidate_assessments": [
    {
      "scenario_id": "candidate_airport_hub",
      "candidate_id": "airport_hub",
      "interconnection_bus": 205,
      "added_load_MW": 80.0,
      "total_cost_dollars_per_hour": 0.0,
      "incremental_cost_dollars_per_hour": 0.0,
      "reserve_mcp_dollars_per_MWh": 0.0,
      "target_bus_lmp_dollars_per_MWh": 0.0,
      "lmp_by_bus": [
        {"bus": 101, "lmp_dollars_per_MWh": 0.0}
      ],
      "price_diffusion_summary": {
        "affected_bus_count": 0,
        "max_abs_lmp_change_dollars_per_MWh": 0.0,
        "average_abs_lmp_change_dollars_per_MWh": 0.0
      },
      "new_binding_lines": [
        {
          "from": 101,
          "to": 205,
          "flow_MW": 0.0,
          "limit_MW": 0.0,
          "loading_pct": 0.0
        }
      ]
    }
  ],
  "recommendation": {
    "selected_candidate_id": "airport_hub",
    "selected_interconnection_bus": 205,
    "ranking": [
      {
        "rank": 1,
        "candidate_id": "airport_hub",
        "interconnection_bus": 205,
        "incremental_cost_dollars_per_hour": 0.0,
        "target_bus_lmp_dollars_per_MWh": 0.0,
        "affected_bus_count": 0,
        "new_binding_lines_count": 1
      }
    ],
    "decision_basis": {
      "selection_rule": "lowest incremental cost, then lower target-bus LMP, then fewer affected buses, then fewer newly binding lines, then lower bus number",
      "runner_up_candidate_id": "metro_spur",
      "incremental_cost_advantage_dollars_per_hour": 0.0,
      "target_bus_lmp_advantage_dollars_per_MWh": 0.0
    }
  }
}
```

Requirements:
- Keep `candidate_assessments` in the same order as `candidate_buses` in `interconnection_candidates.json`.
- Include every bus exactly once in each `lmp_by_bus` list.
- Use numeric values, not strings, for all reported metrics.
- Round reported prices, costs, flows, limits, loadings, and comparison deltas to 2 decimals.
