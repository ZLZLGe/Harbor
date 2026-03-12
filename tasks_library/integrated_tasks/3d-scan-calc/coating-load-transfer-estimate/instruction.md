You need to estimate the coating load for a scanned production part.

The input file `/root/scan_data.stl` is a noisy binary STL. The 2-byte `Attribute Byte Count` at the end of each triangle record is being used to store the **coating recipe ID** for that connected component.

Your job is to:
1. Parse the binary STL and split it into connected components.
2. Treat the **largest connected component by volume** as the production part and ignore every other component as scan debris.
3. Read the production part's recipe ID from the triangle attributes and look up that recipe in `/root/coating_process_table.md`.
4. Compute the production part's exterior surface area by summing the areas of its triangles.
5. Use the process table to compute:
   - `coating_mass_g = surface_area_cm2 * (dry_film_thickness_mm / 10) * cured_density_g_per_cm3 / transfer_efficiency`
   - `coating_cost_usd = coating_mass_g / 1000 * material_cost_usd_per_kg`
6. Save the result to `/root/coating_estimate.json` in exactly this shape:

```json
{
  "recipe_id": 42,
  "surface_area_cm2": 1234.56,
  "coating_mass_g": 78.9,
  "coating_cost_usd": 1.23
}
```

Notes:
- The STL coordinates are already in centimeters, so the computed surface area is in `cm^2`.
- The dry film thickness values in the process table are in millimeters, so convert them to centimeters before using the formula.
- Numeric results are accepted within `0.1%` relative error.
