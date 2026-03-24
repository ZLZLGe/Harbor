You are given `/root/data/reaction_cases.json`. Each case contains a `case_id` and an unbalanced chemical reaction string written with `+` separators and `->` between reactants and products. Molecular formulas may include element symbols, integer subscripts, and round parentheses such as `Ca3(PO4)2`.

Write `/root/workspace/reaction_balancer.py`.

Your script must define:

```python
def balance_reaction_cases(filepath: str) -> dict[str, dict]:
```

For every case, parse the formulas, build the exact element-conservation matrix, find a one-dimensional nullspace basis, and return a dictionary keyed by `case_id` with this shape:

```python
{
    "combustion_ethane": {
        "reactants": ["C2H6", "O2"],
        "products": ["CO2", "H2O"],
        "elements": ["C", "H", "O"],
        "stoichiometry_matrix": [
            [2, 0, -1, 0],
            [6, 0, 0, -2],
            [0, 2, -2, -1]
        ],
        "nullspace_basis": ["1", "7/2", "2", "3"],
        "integer_coefficients": [2, 7, 4, 6],
        "balanced_equation": "2 C2H6 + 7 O2 -> 4 CO2 + 6 H2O"
    }
}
```

Requirements:

1. Do not hardcode the expected answers.
2. `elements` must be sorted alphabetically.
3. The matrix column order must be all reactants first, then all products, preserving their appearance in the reaction string.
4. Product columns must use negative counts so that the matrix directly represents conservation equations.
5. `nullspace_basis` must come from exact arithmetic and be scaled so that its first nonzero entry is exactly `"1"`.
6. `integer_coefficients` must be the minimal positive integers obtained by clearing denominators and dividing by the global gcd.
7. `balanced_equation` must preserve the original species order from the input, with all reactants first and all products second. Render each term as just the formula when its integer coefficient is `1`, otherwise as `"<coefficient> <formula>"`. Join terms on each side with `" + "` and join the two sides with `" -> "`. Do not add any extra spaces anywhere else.
8. When the script is executed directly, it must read `/root/data/reaction_cases.json` and write the full result JSON to `/root/workspace/reaction_balancer_results.json`.

Only `/root/workspace/reaction_balancer.py` will be graded.
