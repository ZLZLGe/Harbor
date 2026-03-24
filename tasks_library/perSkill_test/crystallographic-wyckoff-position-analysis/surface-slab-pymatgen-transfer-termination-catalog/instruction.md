You are preparing a compact surface-termination catalog for a few bulk structures that are already available on disk.

The input files are stored in `/root/slab_catalog_inputs/`:

- `slab_requests.json` describing which bulk files to analyze, the Miller indices to use, and the slab/vacuum thickness settings
- the referenced CIF files for the bulk structures

Write your code to `/root/workspace/solution.py`.

Implement this entry function:

```python
def build_slab_termination_catalog(data_dir: str) -> dict:
```

The function must return a JSON-serializable dictionary with this shape:

```python
{
    "bulk_count": 2,
    "total_slab_count": 6,
    "bulks": [
        {
            "bulk_id": "pyrite_reference",
            "filename": "FeS2_mp-226.cif",
            "formula": "FeS2",
            "requested_miller_indices": [[1, 0, 0], [1, 1, 0]],
            "slab_count": 3,
            "slabs": [
                {
                    "miller_index": [1, 0, 0],
                    "surface_area": 34.123456,
                    "layer_count": 7,
                    "termination_composition": {
                        "top_layer": "S",
                        "bottom_layer": "S"
                    },
                    "polarity_summary": {
                        "top_bottom_same_composition": True,
                        "termination_type": "symmetric"
                    }
                }
            ]
        }
    ]
}
```

Requirements:

- Process `bulks` in the order given by `slab_requests.json`.
- For each bulk structure, first convert the loaded structure to its conventional standard structure before generating slabs.
- For each Miller index, generate slabs using the exact `min_slab_size` and `min_vacuum_size` values from the request file and `center_slab=True`.
- `requested_miller_indices` must echo the Miller indices from the request in the same order.
- `formula` must be the reduced formula of the conventional standard structure used for slab generation.
- `slabs` must contain every generated slab for every requested Miller index.
- For each slab:
  - `miller_index` must be a length-3 integer list.
  - `surface_area` must be rounded to 6 decimal places.
  - `layer_count` must be computed by sorting all slab sites by Cartesian `z` and merging consecutive sites into the same layer when their `z` difference is less than or equal to `layer_merge_tol_angstrom` from the request file.
  - `termination_composition.top_layer` and `termination_composition.bottom_layer` must come from the highest-`z` and lowest-`z` merged layers, respectively, serialized as reduced formulas.
  - `polarity_summary.top_bottom_same_composition` must state whether those two layer compositions are identical.
  - `polarity_summary.termination_type` must be `"symmetric"` when the top and bottom layer compositions match, otherwise `"asymmetric"`.
- Sort each bulk's `slabs` list by `miller_index`, then `termination_composition.top_layer`, then `termination_composition.bottom_layer`, then `layer_count`, then `surface_area`.
- `slab_count` must equal the number of slab records for that bulk.
- `total_slab_count` must equal the sum of all per-bulk `slab_count` values.
- Keep the final result fully JSON-serializable with plain dict/list/str/int/float/bool values.
- Do not hardcode the expected answers.

When `/root/workspace/solution.py` is executed as a script, it must call `build_slab_termination_catalog("/root/slab_catalog_inputs")` and write the returned object to `/root/workspace/slab_termination_catalog.json`.
