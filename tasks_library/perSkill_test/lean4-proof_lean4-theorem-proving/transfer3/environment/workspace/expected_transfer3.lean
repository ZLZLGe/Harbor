def checkpoints : Nat -> Nat
  | 0 => 7
  | n + 1 => checkpoints n + 1

theorem problemsolution (n : Nat) : checkpoints n = 7 + 1 * n := by
  induction n with
  | zero =>
      simp [checkpoints]
  | succ k ih =>
      simp [checkpoints, ih, Nat.mul_succ, Nat.add_assoc, Nat.add_left_comm, Nat.add_comm]
