---
name: mesh-analysis
description: "Analyzes 3D mesh files (STL) to calculate geometric properties, identify connected components, and extract per-triangle attribute data."
---

# Mesh Analysis

This skill provides a `MeshAnalyzer` helper for binary STL parsing, connected component analysis, volume calculation, and attribute extraction.

## When to Use

Use this skill when you need to:

1. Parse STL mesh files
2. Separate the main connected component from debris
3. Compute component volume
4. Read metadata stored in the 2-byte attribute field of binary STL triangles

## Typical Workflow

```python
from mesh_tool import MeshAnalyzer

analyzer = MeshAnalyzer("/path/to/file.stl")
report = analyzer.analyze_largest_component()

volume = report["main_part_volume"]
material_id = report["main_part_material_id"]
```

## Notes

- Binary STL is supported directly
- The 2-byte attribute field is preserved and exposed as `main_part_material_id`
- Volume is computed from mesh triangles and returned in source coordinate units cubed
