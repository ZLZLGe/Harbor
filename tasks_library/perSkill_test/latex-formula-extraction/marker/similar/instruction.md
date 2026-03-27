You are preparing a final standalone-formula handoff file for a research-paper extraction run.

Input files:
- `/root/input/latex_paper.pdf`
- `/root/input/formula_candidates.json`

Output file:
- `/root/similar_standalone_formulas.md`

Requirements:
1. Use only entries where `is_standalone` is `true`.
2. Normalize each formula body:
   - remove `\\tag{...}` fragments
   - remove trailing commas or periods
   - trim extra whitespace
3. Write one formula per line in the output using this wrapper format: `$$...$$`
4. Keep formulas in the original candidate order.
5. If a formula contains `\\left[` paired with `\\right)`, append one extra corrected formula at the end by changing that pair to `\\left(` and `\\right)`.
6. Do not add blank lines.
