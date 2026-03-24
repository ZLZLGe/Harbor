You need to prepare a lift plan for a subsea salvage recovery.

The scan at `/root/subsea_recovery_scan.stl` is a binary STL captured after cleanup dives. It still contains several disconnected shell clusters and loose fragments, so the actual recovery target is the **largest connected component**. The 2-byte `Attribute Byte Count` field at the end of each triangle record stores the **Alloy ID** for that component.

Use `/root/alloy_registry.json` to look up the alloy density and `/root/recovery_factors.toml` to look up the seawater density, gravity, and dynamic amplification factor used by the lift team.

The STL coordinates are in **centimeters**, so convert the main component volume from `cm^3` to `m^3` before calculating loads.

Write `/root/lift_plan.json` in the following format:

```json
{
  "alloy_id": 314,
  "main_body_volume_m3": 0.168558,
  "dry_weight_kN": 14.551278,
  "underwater_lift_load_kN": 13.88311
}
```

Calculation rules:
- `main_body_volume_m3 = main_body_volume_cm3 / 1000000`
- `dry_weight_kN = main_body_volume_m3 * density_kg_m3 * gravity_m_s2 / 1000`
- `underwater_lift_load_kN = main_body_volume_m3 * (density_kg_m3 - seawater_density_kg_m3) * gravity_m_s2 / 1000 * dynamic_amplification_factor`

The result will be considered correct if the numeric fields are within **0.1% accuracy**.
