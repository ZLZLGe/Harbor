请读取 `/root/regional_sales_report_input` 中所有页面上的销售明细表，并生成 `/root/regional_sales_rollup.csv`。

要求：

1. 合并所有页面里的表格数据，不要漏掉跨页内容。
2. 每条明细至少包含 `Region`、`Month`、`Gross Sales`、`Refunds`、`Net Sales`。
3. 根据月份生成季度：
   - `Jan`、`Feb`、`Mar` 归为 `Q1`
   - `Apr`、`May`、`Jun` 归为 `Q2`
4. 按 `Region` 和 `Quarter` 汇总，分别求和：
   - `Gross Sales` -> `gross_sales`
   - `Refunds` -> `refunds`
   - `Net Sales` -> `net_sales`
5. 输出 CSV 必须只包含这 5 列，列名顺序固定为：
   - `region,quarter,gross_sales,refunds,net_sales`
6. 输出结果按 `region` 升序、再按 `quarter` 升序排序。
7. 金额输出为整数，不要带货币符号或千位分隔符。

最终文件保存到 `/root/regional_sales_rollup.csv`。
