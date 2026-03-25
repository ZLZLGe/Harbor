你要根据一份多页供应商对账单文档，生成可导入系统的对账汇总表。

输入文件：
- `/root/data/vendor_statement_bundle`：3 页对账单文档。文档里会重复出现多个供应商区块，同一供应商可能跨页出现。

请生成 `/root/workspace/reconciliation.csv`，要求如下：

1. 只把明细表中首列以 `INV-` 或 `CRM-` 开头的行当作有效行项目。
2. 每个有效行项目都归属到它上方最近的 `Vendor: <vendor_id> | <vendor_name>` 区块。
3. 页眉、页脚、区块标题、`Ref | Posted | Charge | Paid | Memo` 表头以及 `Section subtotal` 行都不能计入汇总。
4. 输出 CSV 必须包含且仅包含这些列，列顺序也必须一致：
   - `vendor_id`
   - `vendor_name`
   - `amount_due`
   - `amount_paid`
   - `difference`
5. 每个供应商只保留一行；如果同一供应商在文档中出现多次，必须先合并全部有效行项目再汇总。
6. 金额计算规则：
   - `amount_due` = 该供应商全部有效行的 `Charge` 求和
   - `amount_paid` = 该供应商全部有效行的 `Paid` 求和
   - `difference` = `amount_due - amount_paid`
7. 所有金额都必须保留 2 位小数，不要加千分位分隔符。
8. 数据行按 `vendor_id` 升序排列，输出为标准 UTF-8 CSV。
