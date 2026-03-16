You are given a noisy scanned casting at `/root/foundry_scan.stl` in binary STL format.
The file contains one real casting plus several disconnected debris components.
Each triangle's 2-byte attribute field stores the casting's alloy code.

Generate `/root/feedstock_quote.json` with this exact schema:

```json
{
  "alloy_code": 314,
  "main_component_volume_cm3": 1080.0,
  "feedstock_mass_kg": 2.9916,
  "feedstock_quote_usd": 22.784
}
```

Requirements:
1. Parse `/root/foundry_scan.stl` as a binary STL.
2. Split the mesh into connected components using shared vertices.
3. Treat the largest component by volume as the real casting.
4. Read that component's alloy code from the triangle attribute bytes.
5. Load density data from `/root/alloy_density_table.md`.
6. Load feedstock pricing data from `/root/feedstock_cost_table.md`.
7. Compute:
   - `feedstock_mass_kg = main_component_volume_cm3 * density_g_per_cm3 / 1000`
   - `feedstock_quote_usd = feedstock_mass_kg * usd_per_kg * melt_loss_multiplier`

Notes:
- The STL coordinates are already in centimeters, so the computed mesh volume is in cm^3.
- Alloy code is expected to be consistent within the main component.
- Write numeric JSON values, not strings.
- Small floating-point error is acceptable.
