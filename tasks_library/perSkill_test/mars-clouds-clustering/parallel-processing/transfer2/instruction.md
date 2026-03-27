# Transfer - Habitat Zone Plan

You are given habitat zone data at `/root/data/zones.json`.

For each zone, evaluate all policies from:
- `vent_rate`: 1, 2, 3, 4
- `humidifier_level`: 0, 1, 2, 3
- `reheat_level`: 0, 1, 2

Using the deterministic comfort/energy equations implied by the dataset schema:
1. score every policy for each zone
2. pick the best policy per zone

Tie-break order for selecting the best policy in a zone:
1. higher utility
2. lower energy
3. lower `vent_rate`
4. lower `humidifier_level`
5. lower `reheat_level`

Write exactly one JSON file:
- `/outputs/transfer2_zone_plan.json`

Required top-level keys:
- `zones`
- `fleet_summary`

`zones` must be sorted by `zone_id` ascending.

`fleet_summary` must include:
- `mean_comfort`
- `mean_energy`
- `mean_utility`

Round all numeric metrics in the output to 4 decimal places.
