You are reviewing a local DFT screening table for one chemical system. The data is already on disk, and some rows in the table belong to other systems and must be ignored.

The input files are stored in `/root/local_phase_data/`:

- `entries.csv` with columns `entry_id,formula,energy_per_atom`
- `analysis_request.json` with the requested chemical system and the target entry IDs to analyze

Write your code to `/root/workspace/solution.py`.

Implement this entry function:

```python
def build_local_phase_hull_report(data_dir: str) -> dict:
```

The function must return a JSON-serializable dictionary with this shape:

```python
{
    "chemical_system": "Li-Fe-O",
    "stable_entries": [
        {
            "entry_id": "fe_ref",
            "formula": "Fe",
            "energy_per_atom": -1.25
        }
    ],
    "targets": [
        {
            "entry_id": "lifeo2_high",
            "formula": "LiFeO2",
            "energy_per_atom": -3.76,
            "is_stable": False,
            "energy_above_hull": 0.123456,
            "decomposition": [
                {
                    "entry_id": "li2o_alpha",
                    "formula": "Li2O",
                    "amount": 0.5
                }
            ]
        }
    ]
}
```

Requirements:

- Use only rows whose elements are entirely contained in the requested `chemical_system`. The CSV intentionally includes off-system distractor rows.
- Build the phase diagram from the filtered rows.
- `chemical_system` must be the `chemical_system` array from the request joined by `-` in the same order.
- `stable_entries` must contain only the stable entries on the hull, sorted by `formula`, then by `entry_id`.
- Each stable-entry record must contain `entry_id`, reduced `formula`, and `energy_per_atom`.
- `targets` must follow the order in `target_entry_ids`.
- Each target record must contain `entry_id`, reduced `formula`, `energy_per_atom`, `is_stable`, `energy_above_hull`, and `decomposition`.
- Round every float in the output to 6 decimal places.
- If a target is stable, `energy_above_hull` must be `0.0` and `decomposition` must be an empty list.
- If a target is unstable, `decomposition` must list the decomposition products and their phase-diagram amounts, sorted by `formula`, then by `entry_id`.
- Keep the final result fully JSON-serializable with plain dict/list/str/bool/float values.
- Do not hardcode the expected answers.

When `/root/workspace/solution.py` is executed as a script, it must call `build_local_phase_hull_report("/root/local_phase_data")` and write the returned object to `/root/workspace/local_hull_analysis.json`.
