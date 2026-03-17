You are given a JSON file at `/root/data/wyckoff_constraint_cases.json`. Each case contains:

- `parameter_symbols`: symbolic parameters used in affine fractional-coordinate expressions
- `representative_constraints`: three expressions for one representative coordinate
- `sample_point`: the same representative coordinate measured as noisy decimals
- `orbit_constraints`: all coordinate expressions generated for that orbit
- `max_denominator`: the largest denominator allowed when recovering exact rationals from the noisy decimals

Write `/root/workspace/wyckoff_constraint_solver.py`.

Your script must define:

```python
def solve_wyckoff_constraint_cases(filepath: str) -> dict[str, dict]:
```

For every case, recover the exact rational values of the parameters from `sample_point`, substitute them into the orbit expressions, and return a dictionary keyed by `case_id` with this shape:

```python
{
    "orbit_alpha": {
        "parameters": {"x": "1/3", "y": "-1/4"},
        "canonical_representative": ["1/3", "3/4", "1/6"],
        "orbit_multiplicity": 4
    }
}
```

Requirements:

1. Reconstruct exact rationals instead of leaving decimals in the final answer.
2. Normalize every substituted coordinate modulo 1 into the half-open interval `[0, 1)`.
3. `orbit_multiplicity` must count unique normalized orbit coordinates after substitution.
4. Do not hardcode the expected answers.
5. When the script is executed directly, it must read `/root/data/wyckoff_constraint_cases.json` and write the full result JSON to `/root/workspace/wyckoff_constraint_results.json`.

Only the file `/root/workspace/wyckoff_constraint_solver.py` will be graded.
