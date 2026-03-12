You need to triage a batch of scanned parts.

The directory `/root/scan_batch/` contains noisy binary STL scans. In each file, the 2-byte `Attribute Byte Count` at the end of every triangle record is being used to store the **Material ID** of that component.

For every `.stl` file in `/root/scan_batch/`:
1. Parse the binary STL and split it into connected components.
2. Treat the **largest connected component by volume** as the main part and treat every other component as scanning debris.
3. Read the main part's Material ID and look up its density in `/root/material_density_table.md`.
4. Compute `main_part_mass = main_part_volume * density`.
5. Mark the scan as acceptable only if it satisfies `/root/batch_acceptance_rules.md`.

Then save `/root/batch_triage.json` in exactly this shape:

```json
{
  "heaviest_acceptable": {
    "file": "scan_beta.stl",
    "main_part_mass": 12345.67,
    "material_id": 25
  },
  "ranked_parts": [
    {
      "file": "scan_gamma.stl",
      "main_part_mass": 23456.78,
      "material_id": 10,
      "acceptable": false
    }
  ]
}
```

Requirements:
- `ranked_parts` must include every STL file in the batch.
- Sort `ranked_parts` from highest `main_part_mass` to lowest. If two masses are equal, break ties by filename in ascending order.
- `heaviest_acceptable` must be the single acceptable entry with the greatest `main_part_mass`. If there is a tie, use the same filename tie-breaker.
- Use the STL coordinate units and density units directly. No unit conversion is needed.
- Numeric results are accepted within `0.1%` relative error.
