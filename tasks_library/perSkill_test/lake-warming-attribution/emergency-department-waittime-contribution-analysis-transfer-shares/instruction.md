你需要基于 `/root/data/` 中的急诊日运营数据，计算四类瓶颈对平均等待时间的贡献份额。

可用输入文件：

- `ed_wait_times_daily.csv`：字段为 `VisitDate`、`AverageWaitMinutes`
- `arrival_pressure_daily.csv`：字段为 `VisitDate`、`ArrivalsPerHour`、`HighAcuityPct`
- `staffing_gap_daily.csv`：字段为 `VisitDate`、`RNHoursGap`、`PhysicianGapPct`
- `diagnostics_turnaround_daily.csv`：字段为 `VisitDate`、`MedianLabMinutes`、`MedianImagingMinutes`
- `bed_flow_daily.csv`：字段为 `VisitDate`、`BoardingHoursPerPatient`、`BedAssignmentLagMinutes`

请完成以下工作：

1. 按 `VisitDate` 合并全部 5 张表，并按日期升序处理。
2. 把 8 个驱动变量分成 4 类：
   - `ArrivalPressure`：`ArrivalsPerHour`、`HighAcuityPct`
   - `StaffingGap`：`RNHoursGap`、`PhysicianGapPct`
   - `Diagnostics`：`MedianLabMinutes`、`MedianImagingMinutes`
   - `BedFlow`：`BoardingHoursPerPatient`、`BedAssignmentLagMinutes`
3. 对这 8 个驱动变量先做 z-score 标准化，再做一次全局 PCA 或等价的 SVD 降维，只保留前 4 个主成分。
4. 用每个主成分在各类别原始变量上的绝对载荷总和，给 4 个类别各匹配 1 个主成分；匹配时应选择总载荷和最大的那组一一对应关系。
5. 以 `AverageWaitMinutes` 为响应变量，用这 4 个已匹配主成分拟合线性模型，计算完整模型的 `R²`。
6. 每次去掉 1 个类别对应的主成分，重新计算 `R²`，把 `完整模型 R² - 去掉该类别后的 R²` 作为该类别的贡献降幅；若降幅为负，则按 0 处理。
7. 只对 4 个类别的正贡献降幅做归一化，使其转成百分比份额。

把结果写到 `/root/output/waittime_driver_shares.csv`，要求：

- 文件必须包含表头和 4 行结果
- 列名必须严格为 `driver_category` 和 `normalized_contribution_pct`
- `driver_category` 必须恰好覆盖 `ArrivalPressure`、`StaffingGap`、`Diagnostics`、`BedFlow` 四类，各出现一次
- `normalized_contribution_pct` 必须是百分比数值，保留 1 位小数
- 4 行结果必须按 `normalized_contribution_pct` 从高到低排序
- 4 行百分比之和允许因四舍五入落在 99.9 到 100.1 之间
