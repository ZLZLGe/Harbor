You are supporting storm restoration triage after several transmission lines have failed.

The file `storm_network.json` contains a MATPOWER-format network snapshot.  
The file `storm_outages.json` lists the transmission lines that are out of service because of the storm.

Generate `/root/islanding_triage.json` with this structure:

```json
{
  "island_count": 3,
  "totals": {
    "stranded_load_MW": 225.0,
    "surviving_generation_MW": 225.0
  },
  "islands": [
    {
      "island_id": 1,
      "isolated_buses": [101, 205, 309, 402],
      "stranded_load_MW": 105.5,
      "surviving_generation_MW": 165.0,
      "generation_minus_load_MW": 59.5,
      "responsible_outage_lines": [
        {"from": 309, "to": 511},
        {"from": 402, "to": 511}
      ]
    }
  ]
}
```

Requirements:

- Build the post-contingency topology from `branch` rows whose `BR_STATUS = 1`, then remove every line listed in `storm_outages.json`.
- Match an outage line to a branch by the unordered bus pair, not by row position.
- Treat each connected component of the post-contingency network as one island.
- `isolated_buses` must list every bus in that island, sorted by ascending MATPOWER bus number.
- `stranded_load_MW` is the sum of `PD` across the island's buses.
- `surviving_generation_MW` is the sum of `PMAX` for generators in the island whose `GEN_STATUS = 1`.
- `generation_minus_load_MW` is `surviving_generation_MW - stranded_load_MW`.
- `responsible_outage_lines` must include every listed storm outage whose endpoints end up on opposite sides of that island boundary.
- Normalize every outage line in the output so that `from < to`, and sort each island's `responsible_outage_lines` by `from`, then `to`.
- Sort islands by the smallest bus number in each island, then assign `island_id` values `1..N` in that order.
- Round every reported MW value to 2 decimals.
