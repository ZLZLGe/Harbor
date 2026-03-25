# Conflict Notes For Handoff Merge

1. `mira-pp-recursive-bound-closed-form` and `noah-pp-closed-form-tail-control` clearly describe the same reusable proof family.
   - Keep a single canonical proof-pattern record.
   - Prefer Noah's wording for the canonical spine because it has broader evidence across multiple sessions.
   - Retain Mira's simpler "constant minus a nonnegative tail" framing and her fallback use of `ring` if you can merge them cleanly.

2. `mira-pc-relative-evidence` and `noah-pc-evidence-path-and-line` should not survive as two separate project conventions.
   - Keep one stricter rule for handoff review.
   - The canonical rule must require both a repository-relative path and a local line hint or theorem name.

3. `mira-td-positivity` and `noah-td-pow-pos` conflict on what should be remembered as the canonical dependency for positive-tail bounds.
   - Prefer the explicit theorem dependency in the final handoff pack.
   - If the automation tactic is still useful, keep it inside a broader proof-pattern description instead of as the canonical dependency record.

4. The two failed approaches are about different dead ends and should both remain visible after the merge.

5. Every surviving evidence file reference must exist in `project_file_inventory.json`.
