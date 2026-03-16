You are analyzing a debris-contaminated binary STL scan of a recovered marine artifact at `/root/recovered_artifact_scan.stl`.
The scan includes one real artifact plus many disconnected debris fragments.
Each triangle's 2-byte attribute field stores the artifact material code.

Use `/root/salvage_density_reference.md` to look up:
- the artifact material density from the material code
- the density of seawater

Write `/root/buoyancy_report.json` with this exact schema:

```json
{
  "material_id": 42,
  "main_component_volume_cm3": 6242.8903,
  "artifact_density_g_cm3": 0.92,
  "seawater_density_g_cm3": 1.025,
  "artifact_mass_g": 5743.4591,
  "displaced_seawater_mass_g": 6398.9626,
  "buoyancy_margin_g": 655.5035,
  "seawater_result": "floats"
}
```

Requirements:
1. Parse `/root/recovered_artifact_scan.stl` as a binary STL.
2. Split the mesh into connected components using shared vertices.
3. Treat the largest connected component by volume as the real artifact.
4. Read that component's material code from the triangle attribute bytes.
5. The STL coordinates are already in centimeters, so the computed volume is in `cm^3`.
6. Compute:
   - `artifact_mass_g = main_component_volume_cm3 * artifact_density_g_cm3`
   - `displaced_seawater_mass_g = main_component_volume_cm3 * seawater_density_g_cm3`
   - `buoyancy_margin_g = displaced_seawater_mass_g - artifact_mass_g`
7. Set `seawater_result` to `"floats"` when `buoyancy_margin_g > 0`, otherwise set it to `"sinks"`.

Notes:
- The material code is expected to be consistent across the main component.
- Write numeric JSON values, not strings.
- Small floating-point error is acceptable.
