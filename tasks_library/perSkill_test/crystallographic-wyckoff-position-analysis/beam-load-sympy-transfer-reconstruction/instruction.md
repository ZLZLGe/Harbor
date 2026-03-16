You are given `/root/data/beam_cases.json`. Each case defines a beam with piecewise polynomial distributed loads over closed intervals, two boundary conditions, and a set of query points.

Write `/root/workspace/beam_load_analyzer.py`.

Your script must define:

```python
def reconstruct_beam_response(filepath: str) -> dict[str, dict]:
```

Use the beam sign convention

```text
dV/dx = -w(x)
dM/dx = V(x)
```

For each segment, integrate symbolically to obtain an exact shear function `V(x)` and bending-moment function `M(x)`, introduce integration constants for every segment, and solve for those constants using:

1. continuity of `V` and `M` at every internal segment boundary;
2. the two boundary conditions listed in the case.

Return a dictionary keyed by `case_id`. Each value must have exactly this shape:

```python
{
    "constants": {
        "C1": "...",
        "D1": "...",
        "...": "..."
    },
    "shear_segments": [
        {"start": "0", "end": "2", "expr": "..."}
    ],
    "moment_segments": [
        {"start": "0", "end": "2", "expr": "..."}
    ],
    "evaluations": {
        "0": {"V": "...", "M": "..."}
    }
}
```

Requirements:

1. Do not hardcode the expected answers.
2. Treat all numeric values in the input as exact symbolic quantities, not floating-point approximations.
3. Keep the original segment order from the input.
4. `constants` must list every segment constant as `C1..Cn` and `D1..Dn`.
5. `shear_segments[i]["start"]` and `["end"]` must be copied from the corresponding input segment.
6. Every expression and evaluated result must be written as a string representing an exact closed form in the global variable `x`.
7. When the script is executed directly, it must read `/root/data/beam_cases.json` and write the full result JSON to `/root/workspace/beam_load_results.json`.

Only `/root/workspace/beam_load_analyzer.py` will be graded.
