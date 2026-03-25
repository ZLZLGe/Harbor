# Migration Guide

## Direct replacements

- Replace `Library.Tactic.Induction` imports with `Math2001/Tactic/StrongInduction.lean`.
- Replace `simple_induction` with `induction'`.
- Replace `pow_pos` with `pow_pos_of_pos`.

## Preferred rewrites after the refactor

- For the geometric-sequence upper-bound proof, prefer citing `geometric_tail_closed_form` instead of re-deriving the closed form from scratch in every file.
- Keep the warning about top-level recurrence unfolding; that anti-pattern still appears in the new build logs.

## Deprecated parity recipe

- Do not preserve memories that recommend `mod_cases n % 2` as the primary parity move.
- Reframe those memories around integer coercions plus `Int.ModEq.pow`, `Int.ModEq.add`, or `Int.ModEq.mul`.

## Citation policy

- The evidence format did not change during this refactor: repository-relative path plus line hint or theorem name is still mandatory.
