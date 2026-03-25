import Mathlib.Data.Rat.Basic
import Mathlib.Tactic

/-
Session note:
- Goal family: upper bounds for recursively defined rational sequences.
- Intended reusable idea: prove a closed form by induction, then discharge the bound
  by showing the subtracted tail is strictly positive.
-/

def G : Nat -> Rat
  | 0 => 4 / 3
  | n + 1 => G n + 2 / 3 ^ (n + 2)

theorem geom_bound (n : Nat) : G n < 2 := by
  have h_closed : G n = 2 - 2 / 3 ^ (n + 1) := by
    induction n with
    | zero =>
        norm_num [G]
    | succ k ih =>
        calc
          G (k + 1) = G k + 2 / 3 ^ (k + 2) := by rw [G]
          _ = (2 - 2 / 3 ^ (k + 1)) + 2 / 3 ^ (k + 2) := by rw [ih]
          _ = 2 - 4 / 3 ^ (k + 2) + 2 / 3 ^ (k + 2) := by ring_nf
          _ = 2 - 2 / 3 ^ (k + 2) := by ring
  have h_tail_pos : 0 < 2 / (3 : Rat) ^ (n + 1) := by
    have h_pow_pos : 0 < (3 : Rat) ^ (n + 1) := by positivity
    positivity
  calc
    G n = 2 - 2 / 3 ^ (n + 1) := h_closed
    _ < 2 := by linarith
