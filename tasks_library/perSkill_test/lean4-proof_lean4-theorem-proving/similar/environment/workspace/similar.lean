def balance : Nat -> Nat
  | 0 => 3
  | n + 1 => balance n + 2

theorem problemsolution (n : Nat) : balance n = 3 + 2 * n := by
