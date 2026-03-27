def budget : Nat -> Nat
  | 0 => 5
  | n + 1 => budget n + 3

theorem problemsolution (n : Nat) : budget n = 5 + 3 * n := by
