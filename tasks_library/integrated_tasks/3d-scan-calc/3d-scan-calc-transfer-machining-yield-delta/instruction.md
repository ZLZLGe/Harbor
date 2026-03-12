You need to quantify machining yield from two noisy 3D scans of the same part.

The files `/root/pre_machining_scan.stl` and `/root/post_machining_scan.stl` are binary STL meshes. In each triangle record, the 2-byte `Attribute Byte Count` field stores the part's `Material ID`. Both scans include disconnected debris, so the actual part is the largest connected component in each file.

Your job is to:
1. Parse both binary STL files and isolate the largest connected component in each scan.
2. Recover the `Material ID` for that main component from each scan.
3. Use `/root/material_density_table.md` to look up the density.
4. Compute, in `cm^3` and `g`, for the main part in each scan:
   - `pre_machining_mass_g = pre_machining_volume_cm3 * density_g_cm3`
   - `post_machining_mass_g = post_machining_volume_cm3 * density_g_cm3`
5. Compute:
   - `removed_mass_g = pre_machining_mass_g - post_machining_mass_g`
   - `yield_percentage = (post_machining_mass_g / pre_machining_mass_g) * 100`
6. Write `/root/yield_loss_report.json` with this exact schema:

```json
{
  "material_id": 10,
  "pre_machining_volume_cm3": 120.0,
  "post_machining_volume_cm3": 84.0,
  "pre_machining_mass_g": 942.0,
  "post_machining_mass_g": 659.4,
  "removed_mass_g": 282.6,
  "yield_percentage": 70.0
}
```

Notes:
- The STL coordinates are already in centimeters, so computed volumes are in `cm^3`.
- The density table uses `g/cm^3`, so no unit conversion is needed before multiplying.
- The two main components represent the same base material. If the recovered material IDs disagree, treat that as an error.
- Numeric answers are considered correct within `0.1%`.
