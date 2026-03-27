#!/bin/sh
set -eu

cat > /app/workspace/similar.lean <<'LEAN'
def balance : Nat -> Nat
  | 0 => 3
  | n + 1 => balance n + 2

theorem problemsolution (n : Nat) : balance n = 3 + 2 * n := by
  induction n with
  | zero =>
      simp [balance]
  | succ k ih =>
      simp [balance, ih, Nat.mul_succ, Nat.add_assoc, Nat.add_left_comm, Nat.add_comm]
LEAN
