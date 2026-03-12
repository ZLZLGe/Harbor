You need to audit a 3D scan before the part is released to production.

The input file `/root/audit_scan.stl` is a binary STL. The 2-byte `Attribute Byte Count` at the end of each triangle record is being used to store the **Material ID** of the part.

Your job is to:
1. Parse the binary STL and split it into connected components.
2. Treat the **largest connected component by volume** as the main part and treat every other component as discarded debris.
3. Read the main part's Material ID and look up its density in `/root/material_density_table.md`.
4. Compute:
   - `main_part_mass = main_part_volume * density`
   - `discarded_debris_volume = sum(volume of every non-main component)`
   - `scrap_percentage = discarded_debris_volume / (main_part_volume + discarded_debris_volume) * 100`
5. Save the result to `/root/part_audit.json` in exactly this shape:

```json
{
  "main_part_mass": 12345.67,
  "material_id": 42,
  "discarded_debris_volume": 123.45,
  "scrap_percentage": 6.78
}
```

Notes:
- The STL coordinates and the density table already use compatible units, so no unit conversion is needed.
- `scrap_percentage` must be reported as a percentage in the range `0` to `100`, not as a fraction.
- Numeric results are accepted within `0.1%` relative error.
