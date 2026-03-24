You are consolidating crystal structure files that came from different export pipelines. The inputs include both CIF files and POSCAR-style files for some duplicate structures, and two different polymorphs share the same reduced chemical formula.

The input files are stored in `/root/structure_exports/`, and the required scan order is listed in `/root/structure_exports/export_manifest.txt`.

Write your code to `/root/workspace/solution.py`.

Implement this entry function:

```python
def cluster_structure_equivalence(input_dir: str) -> dict:
```

The function must read every file listed in the manifest and return a JSON-serializable dictionary with this shape:

```python
{
    "input_file_count": 8,
    "cluster_count": 4,
    "clusters": [
        {
            "representative_file": "cluster_a_cf4_reference.cif",
            "formula": "CF4",
            "spacegroup_symbol": "...",
            "spacegroup_number": 0,
            "members": [
                "POSCAR_cluster_a_cf4_export",
                "cluster_a_cf4_reference.cif"
            ]
        }
    ]
}
```

Requirements:

- Read every manifest entry exactly once.
- Parse both CIF inputs and POSCAR-style inputs from the same directory.
- Group files into the same cluster only when they represent the same crystal structure, even if file format, atom ordering, or equivalent lattice representation differ.
- Do not rely only on filename, reduced formula, or atom counts. In this dataset, two different clusters share the same reduced formula.
- Within each cluster, `members` must be sorted lexicographically.
- `representative_file` must be the lexicographically smallest `.cif` member in that cluster. If a cluster has no CIF member, use the lexicographically smallest member overall.
- `formula`, `spacegroup_symbol`, and `spacegroup_number` must be computed from the representative structure.
- Sort `clusters` by `representative_file`.
- Keep the final result fully JSON-serializable with plain dict/list/str/int values.
- Do not hardcode the expected cluster assignments.

When `/root/workspace/solution.py` is executed as a script, it must call `cluster_structure_equivalence("/root/structure_exports")` and write the returned object to `/root/workspace/structure_equivalence_clusters.json`.
