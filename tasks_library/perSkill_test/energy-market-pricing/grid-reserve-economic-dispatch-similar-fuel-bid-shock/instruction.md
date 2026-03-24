You support a balancing-area market monitor that wants a precise before-and-after review of a fuel-bid shock on one reserve-capable gas peaker.

The input file is `fleet_data.json`. It contains a single-zone generator fleet, the system load, the spinning-reserve requirement, and a counterfactual scenario in which one generator's energy bid becomes more expensive.

Run the market clearing twice:
1. Base case: use the generator data exactly as listed.
2. Counterfactual: keep every quantity the same except replace the designated generator's energy bid with the counterfactual bid from the file.

For each scenario, solve a reserve-co-optimized dispatch that minimizes total production cost subject to:
1. Total scheduled energy must equal system load.
2. Each generator must stay within its `pmin_mw` and `pmax_mw`.
3. Total cleared spinning reserve must meet `reserve_requirement_mw`.
4. A generator's cleared energy plus cleared reserve cannot exceed `pmax_mw`.
5. A generator's cleared reserve cannot exceed `reserve_cap_mw`.

Use these definitions when you build the output:
- `total_production_cost_dollars_per_hour`: sum of `energy_bid_dollars_per_mwh * energy_mw` across all generators in that scenario.
- `system_energy_price_dollars_per_mwh`: the increase in minimum total production cost if system load is increased by exactly 1 MW while the reserve requirement stays unchanged.
- `reserve_mcp_dollars_per_mw`: the increase in minimum total production cost if the reserve requirement is increased by exactly 1 MW while system load stays unchanged.
- `generator_awards`: one entry per generator, in the same order as the input file.

Reserve awards must be deterministic. If multiple reserve allocations are compatible with the same minimum-cost energy dispatch, break ties by clearing reserve in descending `energy_bid_dollars_per_mwh`, using alphabetical `generator_id` order as the secondary key, until the reserve requirement is exactly met.

Create `dispatch_impact.json` with this structure:

```json
{
  "base_case": {
    "total_production_cost_dollars_per_hour": 10890.0,
    "system_energy_price_dollars_per_mwh": 44.0,
    "reserve_mcp_dollars_per_mw": 14.0,
    "generator_awards": [
      {
        "generator_id": "coal_alpha",
        "energy_mw": 180.0,
        "reserve_mw": 0.0
      }
    ]
  },
  "counterfactual": {
    "total_production_cost_dollars_per_hour": 11410.0,
    "system_energy_price_dollars_per_mwh": 52.0,
    "reserve_mcp_dollars_per_mw": 22.0,
    "generator_awards": [
      {
        "generator_id": "coal_alpha",
        "energy_mw": 180.0,
        "reserve_mw": 0.0
      }
    ]
  },
  "impact_analysis": {
    "cost_change_dollars_per_hour": 520.0,
    "largest_redispatch_units": [
      {
        "generator_id": "gas_peaker_red",
        "base_energy_mw": 65.0,
        "counterfactual_energy_mw": 0.0,
        "energy_delta_mw": -65.0,
        "base_reserve_mw": 25.0,
        "counterfactual_reserve_mw": 25.0,
        "reserve_delta_mw": 0.0
      }
    ]
  }
}
```

Additional output rules:
- `cost_change_dollars_per_hour` must be `counterfactual total cost - base case total cost`.
- `largest_redispatch_units` must contain the 2 generators with the largest absolute change in `energy_mw`, ordered by descending absolute energy change and then alphabetical `generator_id`.
- `energy_delta_mw` and `reserve_delta_mw` must be `counterfactual - base case`.
- Round every numeric value in the JSON to 2 decimal places.
