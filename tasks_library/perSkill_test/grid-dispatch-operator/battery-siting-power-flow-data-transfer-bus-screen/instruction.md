You are screening a shortlist of grid buses for a standalone battery interconnection study.

The file `interconnection_network.json` contains a MATPOWER-format network snapshot.  
The file `candidate_buses.json` contains the shortlisted buses and the voltage thresholds for the study.

Generate `/root/interconnection_screen.json` with this structure:

```json
{
  "project_name": "Harbor Point 250 MW Battery",
  "candidate_count": 8,
  "ranking_rule": {
    "primary": "voltage_class_rank_desc",
    "secondary": "connected_branch_transfer_MW_desc",
    "tertiary": "nearby_load_sink_MW_desc",
    "quaternary": "local_generation_headroom_MW_desc",
    "tie_breaker": "bus_asc"
  },
  "ranked_buses": [
    {
      "rank": 1,
      "bus": 2633,
      "voltage_kV": 380.0,
      "voltage_class": "EHV",
      "voltage_class_rank": 3,
      "connected_in_service_branches": 10,
      "connected_branch_transfer_MW": 283487.0,
      "nearby_load_sink_MW": 42.74,
      "local_generation_headroom_MW": 603.66
    }
  ]
}
```

Requirements:

- Work only from the MATPOWER data and the candidate shortlist.
- Use MATPOWER bus numbers exactly as given in the input data.
- Treat a branch as connected only when `BR_STATUS = 1`.
- `connected_in_service_branches` is the number of in-service branch rows incident to the candidate bus.
- `connected_branch_transfer_MW` is the sum of `RATE_A` across in-service incident branches whose `RATE_A > 0`.
- `nearby_load_sink_MW` is the sum of positive `PD` values on the candidate bus plus every directly connected in-service neighboring bus.
- `local_generation_headroom_MW` is the sum of `max(PMAX - PG, 0)` for in-service generators on the candidate bus plus every directly connected in-service neighboring bus.
- Derive `voltage_class` from the candidate bus `BASE_KV` using the thresholds in `candidate_buses.json`:
  - `BASE_KV >= ehv_min` => `EHV` with rank `3`
  - `hv_min <= BASE_KV < ehv_min` => `HV` with rank `2`
  - otherwise => `Subtransmission` with rank `1`
- Sort `ranked_buses` by descending `voltage_class_rank`, then descending `connected_branch_transfer_MW`, then descending `nearby_load_sink_MW`, then descending `local_generation_headroom_MW`, and finally ascending `bus`.
- Assign `rank` values `1..N` after sorting.
- Round every reported MW value and `voltage_kV` to 2 decimals.
