You are preparing a batch symmetry census for several CIF structures.

The input files are stored in `/root/census_inputs/`, and the required processing order is listed in `/root/census_inputs/batch_manifest.txt`.

Write your code to `/root/workspace/solution.py`.

Implement this entry function:

```python
def build_symmetry_site_census(cif_dir: str) -> dict:
```

The function must read every CIF file listed in the manifest and return a JSON-serializable dictionary with this shape:

```python
{
    "processed_count": 5,
    "structures": [
        {
            "filename": "FeS2_mp-226.cif",
            "formula": "FeS2",
            "spacegroup_symbol": "Pa-3",
            "spacegroup_number": 205,
            "crystal_system": "cubic",
            "element_site_summary": {
                "Fe": {
                    "equivalent_group_count": 1,
                    "groups": [
                        {
                            "wyckoff_letter": "a",
                            "representative_frac_coords": [0.0, 0.5, 0.5]
                        }
                    ]
                },
                "S": {
                    "equivalent_group_count": 1,
                    "groups": [
                        {
                            "wyckoff_letter": "c",
                            "representative_frac_coords": [0.38538, 0.11462, 0.88538]
                        }
                    ]
                }
            }
        }
    ]
}
```

Requirements:

- `processed_count` must equal the number of manifest entries.
- `structures` must follow the manifest order exactly.
- `spacegroup_symbol`, `spacegroup_number`, and `crystal_system` must come from symmetry analysis of each structure.
- `element_site_summary` must group symmetry-equivalent sites by chemical element.
- Each element entry must contain:
  - `equivalent_group_count`: the number of symmetry-equivalent site groups for that element.
  - `groups`: one record per symmetry-equivalent site group, using one representative site from that group.
- For each group:
  - `wyckoff_letter` must contain only the Wyckoff letter.
  - `representative_frac_coords` must be a length-3 list of floats.
  - Normalize fractional coordinates into `[0, 1)` and round each value to 6 decimal places.
- Within each element, sort `groups` by `wyckoff_letter`, then by `representative_frac_coords`.
- Keep the final result fully JSON-serializable with plain dict/list/str/int/float values.
- Do not hardcode the expected answers.

When `/root/workspace/solution.py` is executed as a script, it must call `build_symmetry_site_census("/root/census_inputs")` and write the returned object to `/root/workspace/symmetry_site_census.json`.
