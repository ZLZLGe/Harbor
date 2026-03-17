You are preparing a silicone pour plan from a contaminated ASCII STL scan of a mold insert at `/root/mold_insert_scan_ascii.stl`.
The scan contains one real insert plus many disconnected stray fragments.

Use `/root/silicone_process_sheet.md` to read the process constants.

Write `/root/silicone_pour_plan.json` with this exact schema:

```json
{
  "main_component_volume_cm3": 6242.8903,
  "net_fill_volume_ml": 6242.8903,
  "reserve_volume_ml": 684.4312,
  "total_silicone_required_ml": 6927.3215
}
```

Requirements:
1. Parse `/root/mold_insert_scan_ascii.stl` as an ASCII STL.
2. Split the mesh into connected components using shared vertices.
3. Treat the largest connected component by volume as the real mold insert.
4. The STL coordinates are already in centimeters, so the component volume is in `cm^3`.
5. Read the following values from `/root/silicone_process_sheet.md`:
   - `Transfer factor (mL per cm^3)`
   - `Reserve percent`
   - `Fixed loss (mL)`
6. Compute:
   - `net_fill_volume_ml = main_component_volume_cm3 * transfer_factor`
   - `reserve_volume_ml = net_fill_volume_ml * reserve_percent + fixed_loss_ml`
   - `total_silicone_required_ml = net_fill_volume_ml + reserve_volume_ml`
7. Write numeric JSON values, not strings.

Notes:
- For this task, `1 cm^3` transfers directly according to the process sheet.
- Small floating-point error is acceptable.
