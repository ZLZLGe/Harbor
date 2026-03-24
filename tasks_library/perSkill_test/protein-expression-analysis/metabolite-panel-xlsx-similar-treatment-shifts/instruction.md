Open the workbook in the working directory. It contains two sheets:

- `Task`: complete all requested formulas here
- `Data`: raw metabolite signal matrix

Your goal is to build a treatment-shift scorecard for the 8 metabolites already listed on the `Task` sheet.

1. Fill `C11:L18` with formulas that pull the raw signal for each metabolite/sample pair from `Data`.
Use a two-way lookup so each cell matches both the metabolite ID in column `A` and the sample ID in row `10`.

2. Fill `B24:I27` with grouped summary statistics for the 8 metabolites.
- Row `24`: responder mean
- Row `25`: responder standard deviation
- Row `26`: nonresponder mean
- Row `27`: nonresponder standard deviation

Use the sample group labels in row `9` to decide which columns belong to each group.

3. Fill `C32:E39` for the same 8 metabolites.
- `Log2 Shift` = responder mean - nonresponder mean
- `Fold Change` = 2 ^ (log2 shift)
- `Abs Log2 Shift` = absolute value of the log2 shift

4. Fill `I32:L35` with the top 4 metabolites ranked by `Abs Log2 Shift`, from largest to smallest.
Use the exact direction text:
- `Higher in Responder`
- `Higher in Nonresponder`

Requirements:

- Use formulas, not hard-coded final numbers
- Keep the workbook structure, formatting, colors, and fonts unchanged
- Do not use macros or VBA
- Leave the finished workbook saved in place with the same filename
