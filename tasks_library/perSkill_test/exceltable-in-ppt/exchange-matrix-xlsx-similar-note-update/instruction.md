You are working with `/root/input_exchange_matrix.xlsx`, a treasury workbook that already contains an exchange-rate matrix on the `汇率矩阵` sheet and a single update request on the `更新说明` sheet.

You need to:
1. Read the currency pair and the new rate from `更新说明`
2. Update the matrix so that only the editable numeric input cell for that pair changes
3. Keep the reverse-rate formula cell as a formula, and leave the rest of the workbook unchanged
4. Save the updated workbook as `/root/results_exchange_matrix.xlsx`
