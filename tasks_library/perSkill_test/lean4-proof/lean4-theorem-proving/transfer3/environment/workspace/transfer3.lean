def checkpoints : Nat -> Nat
  | 0 => 7
  | n + 1 => checkpoints n + 1

theorem problemsolution (n : Nat) : checkpoints n = 7 + 1 * n := by
