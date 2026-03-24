You are organizing a small library of symmetry cards exported from a crystallography notebook. Each card contains:

- a list of symmetry operations written as affine expressions in `x`, `y`, and `z`
- several seed fractional coordinates that should be expanded into full orbits

Write a Python script at:

`/root/workspace/wyckoff_orbit_solver.py`

The script must expose the function:

```python
def analyze_wyckoff_orbits(filepath: str) -> dict:
```

The input file for evaluation is:

`/root/orbit_cards/wyckoff_orbit_cards.json`

Requirements:

1. Read the JSON file and process every card in `cards`.
2. For each symmetry operation, parse the three comma-separated coordinate expressions and apply them to each seed point.
3. Keep all arithmetic exact. Do not use floating-point rounding.
4. Normalize every generated coordinate modulo 1 into the half-open interval `[0, 1)`.
5. Deduplicate equivalent positions after normalization.
6. Sort each orbit's unique positions lexicographically by exact coordinate values.
7. For every orbit, report:
   - `multiplicity`: the number of unique normalized positions
   - `representative`: the first position in the sorted list
   - `positions`: the full sorted list of unique normalized positions
8. Return the result in this shape:

```python
{
    "cards": {
        "<card_id>": {
            "<orbit_label>": {
                "multiplicity": 4,
                "representative": ["1/8", "1/6", "1/5"],
                "positions": [
                    ["1/8", "1/6", "1/5"],
                    ["1/8", "1/3", "7/10"],
                    ["7/8", "2/3", "3/10"],
                    ["7/8", "5/6", "4/5"]
                ]
            }
        }
    }
}
```

Use canonical fraction strings such as `"0"`, `"1/2"`, and `"7/10"` in the returned structure.

Do not hardcode the expected answer. Parse the input card file and compute the orbit expansions from the listed symmetry operations.
