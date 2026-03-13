You are given a directory of CIF files at `/root/coordination_cases`.

Write your script at `/root/workspace/coordination_shell_signature.py`.

Your script must expose this entry function:

```python
def analyze_coordination_shell_signature(filepath: str) -> dict[str, Any]:
```

For the structure in `filepath`, standardize it to a conventional cell, identify the symmetry-independent sites in that standardized structure, and audit the first coordination shell of each representative site.

Return a dictionary with this exact top-level schema:

```python
{
    "spacegroup_number": 205,
    "spacegroup_symbol": "Pa-3",
    "site_signatures": [
        {
            "site_index": 0,
            "species": "Fe",
            "wyckoff_letter": "a",
            "coordination_number": 6,
            "neighbor_element_counts": {"S": 6},
            "shell_signature": [
                {
                    "element": "S",
                    "fractional_offset": ["3/8", "1/8", "-1/8"],
                    "distance_ratio": "1"
                }
            ]
        }
    ]
}
```

Requirements:

1. Standardize each structure to its conventional cell before computing symmetry labels or local environments.
2. Use the smallest site index inside each symmetry-equivalent group as that group's `site_index`.
3. Define the first coordination shell of a representative site as all periodic neighbors whose distance is within `1e-5` angstrom of the smallest nonzero neighbor distance for that representative site.
4. `coordination_number` must equal the number of neighbor entries in that first shell.
5. `neighbor_element_counts` must count shell neighbors by element symbol and be emitted in ascending element order.
6. For every shell neighbor, `fractional_offset` must be the fractional displacement from the representative site to the selected periodic image of that neighbor in the standardized conventional-cell basis, wrapped componentwise into `[-1/2, 1/2]`, then converted to rational strings with denominator at most 48.
7. `distance_ratio` must be the shell-neighbor distance divided by the minimum shell distance, simplified to a deterministic exact string. In practice this is often `"1"` for every neighbor in the first shell.
8. Sort `site_signatures` by ascending `site_index`.
9. Sort each `shell_signature` lexicographically by `(element, fractional_offset)`.
10. Keep the module importable. The tests will import `/root/workspace/coordination_shell_signature.py`.

Notes:

- The input CIF files may use nonstandard settings and arbitrary atom ordering.
- Do not hardcode answers by filename.
- You may use external libraries for CIF parsing, symmetry analysis, neighbor enumeration, and exact arithmetic.
