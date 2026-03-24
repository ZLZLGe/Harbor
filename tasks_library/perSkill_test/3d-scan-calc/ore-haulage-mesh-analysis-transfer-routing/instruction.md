You need to prepare a haulage routing manifest for an ore sorting conveyor.

The scan at `/root/conveyor_ore_scan.stl` is a binary STL captured over a belt transfer point. It contains several disconnected dust and pebble fragments, so the actual ore parcel is the **largest connected component**. The 2-byte `Attribute Byte Count` field at the end of each triangle record stores the **Ore Type ID** for that component.

Use `/root/ore_type_catalog.csv` to look up the bulk density, Fe grade, and silica percentage for the extracted Ore Type ID. Use `/root/routing_rules.toml` to choose the outbound line and gate.

The STL coordinates are in **centimeters**, so convert the main component volume from `cm^3` to `m^3` before estimating tonnage.

Write `/root/ore_manifest.json` in the following format:

```json
{
  "ore_type_id": 318,
  "main_ore_volume_m3": 0.048395,
  "estimated_mass_tonnes": 0.168414,
  "dispatch_line": "blend-pad",
  "diversion_gate": "G3",
  "requires_breaker": true
}
```

Calculation rules:
- `main_ore_volume_m3 = main_component_volume_cm3 / 1000000`
- `estimated_mass_tonnes = main_ore_volume_m3 * bulk_density_t_per_m3`
- Select the first route in `/root/routing_rules.toml` whose `min_fe_grade_pct <= fe_grade_pct`, `max_silica_pct >= silica_pct`, and `max_mass_tonnes >= estimated_mass_tonnes`
- `requires_breaker = estimated_mass_tonnes >= breaker.threshold_tonnes`

The result will be considered correct if numeric fields are within **0.1%** of the expected values.
