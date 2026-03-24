You are reviewing a transmission planning data handoff before downstream tools consume the snapshot.

The file `qc_network.json` contains a MATPOWER-format network snapshot.

Generate `/root/topology_audit.json` with this structure:

```json
{
  "snapshot_name": "topology_qa_fixture",
  "summary": {
    "bus_count": 8,
    "generator_count": 4,
    "branch_count": 8,
    "in_service_branch_count": 6,
    "orphan_bus_count": 2,
    "duplicate_corridor_count": 1,
    "zero_reactance_count": 1,
    "zero_rating_count": 1,
    "invalid_generator_reference_count": 1
  },
  "normalized_bus_index_map": [
    {"bus": 101, "normalized_index": 0}
  ],
  "orphan_buses": [
    {"bus": 511, "bus_type": 1, "pd_MW": 18.0}
  ],
  "duplicate_corridors": [
    {"from": 101, "to": 205, "branch_row_ids": [1, 3], "in_service_branch_count": 2}
  ],
  "branch_anomalies": {
    "zero_reactance": [
      {"branch_row_id": 4, "from": 309, "to": 402, "reactance_pu": 0.0, "rate_a_MVA": 80.0}
    ],
    "zero_rating": [
      {"branch_row_id": 5, "from": 402, "to": 450, "reactance_pu": 0.02, "rate_a_MVA": 0.0}
    ]
  },
  "invalid_generator_bus_references": [
    {"generator_row_id": 4, "bus": 999, "gen_status": 1}
  ]
}
```

Requirements:

- Build `normalized_bus_index_map` by sorting the MATPOWER bus numbers ascending and assigning zero-based `normalized_index` values in that order.
- Treat a branch as topologically active only when `BR_STATUS = 1`.
- An `orphan_buses` entry is any bus with zero incident active branches, even if a generator is attached to that bus.
- Report each orphan bus as `{bus, bus_type, pd_MW}` and sort `orphan_buses` by ascending `bus`.
- Normalize every corridor and branch endpoint so that `from < to`.
- A `duplicate_corridors` entry is any normalized active corridor that appears in at least two branch rows. Report the 1-based `branch_row_ids` for that corridor in ascending order, then sort the corridor entries by `from`, then `to`.
- `branch_anomalies.zero_reactance` must include every active branch whose `BR_X = 0`.
- `branch_anomalies.zero_rating` must include every active branch whose `RATE_A <= 0`.
- For each branch anomaly entry, report `{branch_row_id, from, to, reactance_pu, rate_a_MVA}` and sort by ascending `branch_row_id`.
- `invalid_generator_bus_references` must include every generator row whose `GEN_BUS` does not appear in the bus table, regardless of generator status. Report `{generator_row_id, bus, gen_status}` sorted by ascending `generator_row_id`.
- All counts in `summary` must match the detailed sections.
- Round every reported MW, MVA, and per-unit numeric value to 2 decimals. Integer identifiers must remain integers.
