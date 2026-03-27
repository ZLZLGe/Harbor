Generate a markdown quality-control report for extracted formulas.

Input file:
- `/root/input/formula_qc_cases.json`

Output file:
- `/root/transfer3_formula_qc_report.md`

Report format requirements:
1. Start with title line: `# Formula QC Summary`.
2. Add bullet lines:
   - `- Total formulas: <N>`
   - `- Requires fixes: <M>`
3. Add a blank line.
4. Add table header exactly:
   - `| formula_id | status | note |`
   - `| --- | --- | --- |`
5. Add one table row per input item in original order:
   - status must be `fix-required` when `requires_fix=true`, otherwise `ok`
6. End with a trailing newline.
