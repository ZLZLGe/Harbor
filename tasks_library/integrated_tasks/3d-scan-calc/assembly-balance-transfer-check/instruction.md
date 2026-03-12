You need to evaluate whether a scanned assembly is balanced on its mounting footprint.

Inputs:
- `/root/assembly_scan.stl`: a noisy binary STL assembly scan.
- `/root/material_density_table.md`: material densities keyed by Material ID.
- `/root/assembly_requirements.md`: rules for filtering debris and the mounting footprint bounds.

Important details:
- The STL is binary.
- The 2-byte `Attribute Byte Count` at the end of each triangle record stores the **Material ID** for that connected component.
- The STL coordinates are already in centimeters, so component volumes are in `cm^3`.
- Every meaningful assembly component is homogeneous. Small disconnected pieces are scan debris and must be ignored.

Your job is to:
1. Parse the binary STL and split it into connected components.
2. Read `/root/assembly_requirements.md` and keep only the connected components whose volume is at least the minimum assembly-component volume listed there. Treat every smaller component as debris.
3. For each remaining component:
   - determine its material ID from the triangle attributes,
   - look up the density in `/root/material_density_table.md`,
   - compute its volume, mass, and centroid.
4. Compute the total assembly mass and the assembly center of mass.
5. Project the assembly center of mass onto the mounting plane and decide whether it lies inside or on the rectangular mounting footprint from `/root/assembly_requirements.md`.
6. Save the result to `/root/assembly_balance.json` in exactly this shape:

```json
{
  "meaningful_component_count": 4,
  "components": [
    {
      "material_id": 10,
      "volume_cm3": 48.0,
      "mass_g": 376.8,
      "centroid_cm": {
        "x": -2.5,
        "y": 0.0,
        "z": 2.0
      }
    }
  ],
  "total_mass_g": 700.98,
  "assembly_center_of_mass_cm": {
    "x": -0.81,
    "y": -0.44,
    "z": 1.85
  },
  "balance_result": "fail"
}
```

Additional requirements:
- Sort `components` by descending `volume_cm3`. If two components have the same volume, sort by ascending `material_id`.
- `balance_result` must be either `"pass"` or `"fail"`.
- Numeric results are accepted within `0.1%` relative error.
