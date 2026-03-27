def packets : Nat -> Nat
  | 0 => 1
  | n + 1 => packets n + 4

theorem problemsolution (n : Nat) : packets n = 1 + 4 * n := by
