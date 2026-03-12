# Production Coating Process Table

Use the coating recipe ID stored in the STL triangle attributes to select the correct finishing recipe.

| Recipe ID | Coating Name | Dry Film Thickness (mm) | Cured Density (g/cm^3) | Transfer Efficiency | Material Cost (USD/kg) |
| --- | --- | --- | --- | --- | --- |
| 7 | Clear Seal | 0.05 | 1.02 | 0.92 | 19.00 |
| 18 | Zinc Epoxy | 0.16 | 2.15 | 0.74 | 12.50 |
| 42 | Ceramic Shield | 0.18 | 1.24 | 0.77 | 28.00 |
| 88 | PTFE Glide | 0.09 | 1.10 | 0.88 | 33.00 |

## Formula

1. `dry_volume_cm3 = surface_area_cm2 * (dry_film_thickness_mm / 10)`
2. `coating_mass_g = dry_volume_cm3 * cured_density_g_per_cm3 / transfer_efficiency`
3. `coating_cost_usd = coating_mass_g / 1000 * material_cost_usd_per_kg`
