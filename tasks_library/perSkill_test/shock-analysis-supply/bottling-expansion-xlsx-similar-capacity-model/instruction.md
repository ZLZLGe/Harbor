你需要基于当前工作目录提供的装瓶厂模板工作簿，完成一个扩产冲击模型，并将结果保存为任务要求的输出工作簿文件。

可用输入文件：
- 当前工作目录中的模板工作簿：包含原始历史数据、扩产计划、假设参数和待补齐的模型页。

工作簿中已经给出 6 个工作表：
- `Historical_Data`：2018-2024 年历史产量、设备净资本和人工工时。
- `Expansion_Plan`：2025-2029 年扩产资本开支与新增名义产能。
- `Assumptions`：单箱价格、单位变动成本、扩产资产维护率、折旧年限、基线增长上限、扩产利用率。
- `Efficiency_Trend`：需要补齐历史链接、效率指标、平滑趋势和趋势增长。
- `Capacity_Model`：需要补齐基线产量、扩产后产量、扩产净资本、折旧、EBITDA uplift、营业利润 uplift。
- `Summary`：需要汇总年度和累计结果。

请在模板基础上完成以下内容，且需要保留公式，不要把应由公式计算的结果改成手填常数：

1. 在 `Efficiency_Trend` 中：
- 将 2018-2024 年的历史产量、净资本、人工工时链接到 B:D 列。
- 在 E:G 列分别计算 `Cases per Labor Hour`、`Cases per Capital` 和 `Raw Efficiency Index`，其中原始效率指数使用两者的几何平均。
- 在 H 列构造平滑效率指数：
  - 2018 和 2019 直接等于当年的原始效率指数。
  - 2020-2024 使用三年加权平滑：`20% * 前两年 + 30% * 前一年 + 50% * 当年`。
  - 2025-2029 使用工作表公式把 2018-2024 的平滑效率趋势线性延展。
- 在 I 列计算平滑效率指数的同比增速。

2. 在 `Capacity_Model` 中：
- 2024 行作为锚点。
- 将 `Smoothed Efficiency Index` 链接到 B 列，并在 C 列计算效率同比。
- D 列的 `Baseline Growth` 取效率同比和 `Assumptions` 中基线增长上限的较小值。
- E 列的 `Baseline Cases` 从 2024 年历史产量起步，向后逐年递推。
- F:G 列链接扩产计划中的年度资本开支和新增名义产能。
- H 列计算累计新增名义产能。
- I 列的 `With-Expansion Cases` 公式为：
  - 基线产量
  - 加上 `累计新增名义产能 × (当年平滑效率指数 / 2024 年平滑效率指数) × 扩产利用率`
- J 列跟踪 `Expansion Net Capital`，按“上年净资本减去上年折旧，再加上当年扩产资本开支”递推。
- K 列计算 `Expansion Depreciation`，使用直线折旧，年折旧率为 `1 / Depreciation Life`。
- L 列计算 `EBITDA Uplift`：
  - `(With-Expansion Cases - Baseline Cases) × (Price per Case - Variable Cost per Case)`
  - 再减去 `Expansion Net Capital × Maintenance Rate on Expansion Net Capital`
- M 列计算 `Operating Profit Uplift = EBITDA Uplift - Expansion Depreciation`。

3. 在 `Summary` 中：
- B2：汇总 2025-2029 年 `EBITDA Uplift` 总额。
- B3：汇总 2025-2029 年 `Expansion Depreciation` 总额。
- B4：引用 2029 年 `With-Expansion Cases`。
- E7:E11：逐年列出 2025-2029 年 `EBITDA Uplift`。
- H7:H11：逐年列出 2025-2029 年 `Expansion Depreciation`。

输出要求：
- 最终文件名必须使用任务要求的输出文件名。
- 结果必须保留为可见公式，跨表链接不能断。
- 请直接在当前工作目录生成输出文件，不要额外输出其他答案文件。
