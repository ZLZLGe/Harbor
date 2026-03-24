读取 `/root/sales_transactions` 后接 `.xls` 再接 `x` 的销售工作簿，与 `/root/product_master` 后接 `.xls` 再接 `x` 的商品主数据工作簿，生成新的 Excel 报表 `/root/retail_margin_report` 后接 `.xls` 再接 `x`。

要求如下：

1. 先按 `SKU` 关联两份工作簿。
   - `SKU` 关联前需要去掉首尾空格，并统一为大写。
   - `Region` 与 `Channel` 需要去掉首尾空格，并统一为首字母大写形式。
   - `OrderDate` 保留原值，只去掉首尾空格，不做额外格式化。
   - 使用内连接；无法匹配到商品主数据的销售记录不要出现在结果中。

2. 生成一个名为 `SourceData` 的明细工作表，必须且只能包含以下列，并严格按这个顺序输出：
   - `OrderID`
   - `OrderDate`
   - `Region`
   - `Channel`
   - `SKU`
   - `Category`
   - `Units`
   - `UnitPrice`
   - `DiscountPct`
   - `UnitCost`
   - `GrossSales`
   - `NetSales`
   - `TotalCost`
   - `GrossProfit`
   - `DiscountBand`
   - `SourceData` 的行顺序必须与销售交易工作簿清洗后的原始记录顺序一致；完成关联后不要再额外排序。

3. 派生字段规则：
   - `GrossSales = Units * UnitPrice`
   - `NetSales = GrossSales * (1 - DiscountPct)`
   - `TotalCost = Units * UnitCost`
   - `GrossProfit = NetSales - TotalCost`
   - 金额字段保留两位小数
   - `DiscountBand` 分段规则：
     - `DiscountPct == 0` -> `No Discount`
     - `0 < DiscountPct < 0.10` -> `1-9%`
     - `0.10 <= DiscountPct < 0.20` -> `10-19%`
     - `DiscountPct >= 0.20` -> `20%+`

4. 结果工作簿中的工作表顺序必须严格为：`SourceData`、`Margin by Region`、`Margin by Category`、`Net Sales by Channel`、`Discount Band Profit`。

5. 在结果工作簿中额外创建以下透视表工作表：
   - `Margin by Region`
     - Rows: `Region`
     - Values: Sum of `GrossProfit`
   - `Margin by Category`
     - Rows: `Category`
     - Values: Sum of `GrossProfit`
   - `Net Sales by Channel`
     - Rows: `Channel`
     - Values: Sum of `NetSales`
   - `Discount Band Profit`
     - Rows: `DiscountBand`
     - Columns: `Channel`
     - Values: Sum of `GrossProfit`

6. 最终只需要保存结果到 `/root/retail_margin_report` 后接 `.xls` 再接 `x`。
