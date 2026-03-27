#!/bin/sh
set -eu

cat > /app/workspace/transfer2.lean <<'LEAN'
def packets : Nat -> Nat
  | 0 => 1
  | n + 1 => packets n + 4

theorem problemsolution (n : Nat) : packets n = 1 + 4 * n := by
  induction n with
  | zero =>
      simp [packets]
  | succ k ih =>
      simp [packets, ih, Nat.mul_succ, Nat.add_assoc, Nat.add_left_comm, Nat.add_comm]
LEAN
