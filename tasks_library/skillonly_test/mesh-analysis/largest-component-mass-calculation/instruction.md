The binary STL scan in `/root/scan_data.stl` contains one main printed part plus debris fragments. The 2-byte attribute field on each triangle stores the material id.

Use `/root/material_density_table.md` to look up the density for the material id of the largest connected component, then write `/root/outputs/main_part_mass.json` in this format:

```json
{
  "main_part_volume": 123.45,
  "main_part_material_id": 42,
  "density": 5.55,
  "main_part_mass": 685.15
}
```

Requirements:

1. Parse the STL as binary data.
2. Filter out debris by selecting the largest connected component by volume.
3. Extract the material id from the main component.
4. Use the density table as provided. The density units are already compatible with the STL volume units.
5. Compute `main_part_mass = main_part_volume * density`.

Do not modify the supplied files, do not add extra output files, and do not change the output path.
