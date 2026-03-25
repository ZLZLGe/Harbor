# Refactor Snapshot

## Namespace migration

- The old `Library.*` namespace was retired in favor of `Math2001.*`.
- `Library.Tactic.Induction` moved into `Math2001/Tactic/StrongInduction.lean`.
- Sequence-specific helper lemmas now live under `Math2001/Rewrites/GeometricTail.lean`.

## Proof workflow changes

- Bound proofs over recursive sequences should reach a closed-form lemma first and only then close the inequality.
- The project now prefers `induction'` from the new induction helper instead of the removed `simple_induction`.
- The standard tail rewrite for the geometric sequence is exposed as `geometric_tail_closed_form`.

## Parity and modular reasoning

- Parity automation was consolidated around `Int.ModEq` lemmas after the refactor.
- The old natural-number shortcut `mod_cases n % 2` is no longer part of the maintained parity workflow.

## Review hygiene that stayed the same

- Memory and review notes still require repository-relative evidence plus a line hint or theorem name.
