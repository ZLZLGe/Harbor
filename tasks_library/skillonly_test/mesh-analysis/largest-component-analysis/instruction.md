Analyze the noisy binary STL scan in `/root/scan_data.stl` and identify the largest connected component after filtering out debris.

Write `/root/outputs/largest_component_report.json` with this structure:

```json
{
  "main_part_volume": 123.45,
  "main_part_material_id": 42,
  "total_components": 4
}
```

Requirements:

1. Treat the file as a binary STL.
2. Count all connected components in the scan.
3. Select the largest connected component by volume.
4. Extract the 2-byte attribute value of the main part as `main_part_material_id`.
5. Report the main-part volume in the STL coordinate units cubed.

Do not rename files, do not add extra output files, and do not modify the provided skill files.
