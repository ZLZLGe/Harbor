You need to prepare a sterile packout estimate for a patient-specific implant.

The mesh at `/root/implant_segment.stl` is a binary STL exported from a pre-op segmentation workflow. It still contains several disconnected floating specks, so the actual implant is the **largest connected component**. The 2-byte `Attribute Byte Count` field at the end of each triangle record stores the **Material ID** for that component.

Use `/root/implant_material_profiles.tsv` to look up the fill multiplier and base sterile handling fee for the extracted Material ID. Use `/root/sterile_packout_policy.toml` for the global fill, pouch, pad, and pricing rules.

The STL coordinates are in **millimeters**, so convert the main component volume from `mm^3` to `cm^3`. Use `1 cm^3 = 1 mL`.

Write `/root/sterile_packout.json` in the following format:

```json
{
  "material_id": 602,
  "implant_volume_cm3": 64.0,
  "sterile_fill_volume_ml": 97.2,
  "pouch_size": "medium",
  "absorbent_pad_count": 3,
  "sterile_packout_charge_usd": 66.0
}
```

Calculation rules:
- `implant_volume_cm3 = main_component_volume_mm3 / 1000`
- `sterile_fill_volume_ml = implant_volume_cm3 * fill_multiplier + baseline_fill_ml`
- `pouch_size` is the smallest configured pouch whose capacity is greater than or equal to `sterile_fill_volume_ml`; if it exceeds all listed capacities, use `large`
- `absorbent_pad_count = ceil(sterile_fill_volume_ml / ml_per_pad)`
- `sterile_packout_charge_usd = base_handling_fee_usd + ceil(sterile_fill_volume_ml / charge_step_ml) * charge_per_step_usd`

The result will be considered correct if numeric fields are within **0.1%** of the expected values.
