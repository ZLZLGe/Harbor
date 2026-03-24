You need to prepare a material quote for a powder-bed additive manufacturing job.

The input mesh at `/root/powder_bed_scan.stl` is a binary STL. It contains several small disconnected powder clumps, while the actual part is the **largest connected component**. The 2-byte `Attribute Byte Count` field at the end of each triangle record stores the **Material ID** for that component.

Use `/root/material_pricing.csv` to look up both the material density and the powder price for the extracted Material ID. The STL coordinates are already in **centimeters**, so the volume of the main component is already in **cm^3**.

Write `/root/production_quote.json` in the following format:

```json
{
  "material_id": 25,
  "part_volume_cm3": 780.36,
  "part_mass_g": 2106.98,
  "powder_unit_price_usd_per_kg": 72.5,
  "material_cost_usd": 152.76
}
```

Calculation rules:
- `part_mass_g = part_volume_cm3 * density_g_cm3`
- `material_cost_usd = (part_mass_g / 1000) * powder_unit_price_usd_per_kg`

The result will be considered correct if the numeric fields are within **0.1%** of the expected values.
