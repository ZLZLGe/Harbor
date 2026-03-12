You need to prepare a feedstock plan for a scanned part.

The input mesh at `/root/scan_data.stl` is a binary STL. Its 2-byte `Attribute Byte Count` field is being used to store the part's `Material ID` on each triangle.

Your job is to:
1. Parse the binary STL and ignore scanning debris by isolating the largest connected component.
2. Extract that component's `Material ID`.
3. Look up the density in `/root/material_density_table.md`.
4. Look up the material-specific waste factor in `/root/feedstock_waste_factors.md`.
5. Compute:
   - `net_part_mass = volume * density`
   - `required_feedstock_mass = net_part_mass / (1 - waste_factor)`
   - `estimated_waste_mass = required_feedstock_mass - net_part_mass`
6. Write `/root/feedstock_plan.json` with this exact schema:

```json
{
  "material_id": 42,
  "net_part_mass": 12345.67,
  "waste_factor": 0.12,
  "required_feedstock_mass": 14029.17,
  "estimated_waste_mass": 1683.50
}
```

Notes:
- The STL coordinates are already in centimeters, so the computed volume is in `cm^3`.
- The density table uses `g/cm^3`, so no unit conversion is needed before multiplying.
- The answer is considered correct if the numeric values are within `0.1%`.
