# Failed attempts from the same session

## Attempt A: `linarith` too early in the induction step

- Context: while proving `h_closed` for the successor case.
- Attempted step:
  ```lean
  have : G (k + 1) = 2 - 2 / 3 ^ (k + 2) := by
    linarith [ih]
  ```
- Failure signal:
  `linarith failed to find a contradiction or derive the target`
- Why it stalled:
  `linarith` never saw the recursive definition of `G` unfolded, so the nonlinear term
  `2 / 3 ^ (k + 2)` stayed opaque.
- Better direction:
  Rewrite with `rw [G]`, substitute `ih`, and then use `ring_nf`/`ring` to normalize.

## Attempt B: using `simp [G]` at the top-level goal

- Context: trying to prove `geom_bound` directly.
- Attempted step:
  ```lean
  simp [G]
  ```
- Failure signal:
  The goal expanded into a larger recursive expression and still had no path to `< 2`.
- Why it stalled:
  The proof needed a closed form first; blind simplification only unfolded the recurrence
  without creating a usable induction hypothesis.
- Better direction:
  Split the proof into two phases: first derive `h_closed` by induction, then prove the
  tail term is positive and finish with `linarith`.
