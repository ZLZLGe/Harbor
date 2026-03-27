Generate a formula metrics table from `/root/latex_paper.pdf`.

Write `/root/transfer2_formula_metrics.csv` with the exact header below:

`formula_id,page,char_count,operator_count,contains_greek,status`

Rules:
1. Include one row for each extracted standalone display formula, in order.
2. Add one final row for a corrected formula that fixes the bracket typo in the Hamiltonian expression.
3. `contains_greek` must be either `yes` or `no`.
4. `status` must be `original` for extracted rows and `corrected` for the added fix row.
5. Do not write markdown; output must be valid CSV only.
