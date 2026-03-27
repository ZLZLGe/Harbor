#!/bin/sh
set -eu

cat > /app/workspace/transfer1.lean <<'LEAN'
def budget : Nat -> Nat
  | 0 => 5
  | n + 1 => budget n + 3

theorem problemsolution (n : Nat) : budget n = 5 + 3 * n := by
  induction n with
  | zero =>
      simp [budget]
  | succ k ih =>
      simp [budget, ih, Nat.mul_succ, Nat.add_assoc, Nat.add_left_comm, Nat.add_comm]
LEAN
