Create a short formula QA brief from `/root/latex_paper.pdf`.

Write `/root/transfer3_formula_errata.md` with this exact structure:

1. A title line: `# Formula Errata Brief`
2. A section `## Extracted Display Formulas` containing exactly four numbered formula lines in `$$...$$` form.
3. A section `## Syntax Fix` with three bullets:
   - `Original:` followed by the problematic formula line.
   - `Corrected:` followed by the fixed formula line.
   - `Reason:` a short sentence explaining the bracket mismatch fix.

Rules:
- Keep formula text normalized and free of trailing punctuation.
- Keep the extracted formulas in paper order.
- The corrected formula in `## Syntax Fix` must preserve meaning and only fix syntax.
- Output only `/root/transfer3_formula_errata.md`.
