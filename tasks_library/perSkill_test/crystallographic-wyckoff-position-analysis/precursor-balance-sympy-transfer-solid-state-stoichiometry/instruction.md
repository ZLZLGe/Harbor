You are checking several proposed solid-state synthesis routes before sending them to a furnace run. A JSON file lists, for each route:

- precursor species on the left-hand side
- one target product on the right-hand side
- optional gaseous byproducts on the right-hand side
- exact element counts for every species

Write a Python script at:

`/root/workspace/solid_state_stoichiometry.py`

The script must expose the function:

```python
def balance_solid_state_reactions(filepath: str) -> dict:
```

The evaluation input file is:

`/root/reaction_specs/solid_state_reactions.json`

Requirements:

1. Read every reaction entry in `reactions`.
2. Build the element-conservation linear system from the provided element counts. Do not infer element counts from the species names.
3. Solve for the smallest positive integer coefficients that balance each reaction.
4. Preserve the species order from the input when reporting coefficients and formatting the equation string.
5. Return the result in this shape:

```python
{
    "reactions": {
        "<reaction_id>": {
            "coefficients": {
                "precursors": {"A": 1, "B": 2},
                "target": {"C": 1},
                "byproducts": {"D": 3}
            },
            "normalized_equation": "A + 2 B -> C + 3 D",
            "element_balance": {
                "X": {"left": 4, "right": 4, "balanced": True},
                "Y": {"left": 7, "right": 7, "balanced": True}
            }
        }
    }
}
```

6. If a coefficient is `1`, omit the `1` in `normalized_equation`, but still include the integer `1` inside `coefficients`.
7. Sort `element_balance` keys alphabetically for deterministic output.
8. Use exact arithmetic throughout. Do not rely on floating-point rounding.

Do not hardcode the expected answers. Parse the reaction specification file and compute the coefficients from the listed element counts.
