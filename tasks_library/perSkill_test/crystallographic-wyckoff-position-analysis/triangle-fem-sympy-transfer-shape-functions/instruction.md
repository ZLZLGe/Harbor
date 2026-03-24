You are preparing a verification script for a 2-D finite-element preprocessor. A TOML file lists several 3-node triangular elements with exact node coordinates and a few probe points inside each element.

Write a Python script at:

`/root/workspace/triangle_shape_functions.py`

The script must expose the function:

```python
def derive_triangle_shape_data(filepath: str) -> dict:
```

The evaluation input file is:

`/root/triangle_cases/triangle_cases.toml`

Requirements:

1. Read every case in the TOML file.
2. For each case, use the three listed node coordinates to derive the linear triangular shape functions `N1(x, y)`, `N2(x, y)`, and `N3(x, y)` exactly.
3. Keep arithmetic exact throughout. Do not convert the coordinates to floating-point approximations.
4. Report the positive triangle area as a canonical fraction string.
5. Report the constant gradient matrix in node order, where each row is `[dNi/dx, dNi/dy]`.
6. Evaluate all three shape functions at every listed query point and return those values as canonical fraction strings.
7. Return the result in this shape:

```python
{
    "cases": {
        "<case_id>": {
            "area": "15/8",
            "shape_functions": [
                "1 - 2*x/5 - 8*y/15",
                "2*x/5 - 2*y/15",
                "2*y/3"
            ],
            "gradient_matrix": [
                ["-2/5", "-8/15"],
                ["2/5", "-2/15"],
                ["0", "2/3"]
            ],
            "query_values": {
                "<point_id>": ["8/15", "2/15", "1/3"]
            }
        }
    }
}
```

8. The `shape_functions` entries must be algebraically simplified expressions in the symbols `x` and `y`.
9. Preserve the case order and the query-point order from the input file.

Do not hardcode the expected answers. Parse the TOML input and derive the quantities from the listed node coordinates.
