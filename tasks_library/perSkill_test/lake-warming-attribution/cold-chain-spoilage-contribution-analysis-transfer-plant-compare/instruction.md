你需要基于 `/root/data/` 中的月度冷链仓库数据，分别识别两座仓库的主导损耗驱动，并比较它相对次高驱动的领先百分点。

可用输入文件：

- `spoilage_observed_monthly.csv`：字段为 `PlantCode`、`Month`、`SpoilageLossPct`
- `temperature_discipline_monthly.csv`：字段为 `PlantCode`、`Month`、`DoorOpenMinutesPerPallet`、`SetpointDeviationC`
- `operations_pressure_monthly.csv`：字段为 `PlantCode`、`Month`、`RushOrdersPct`、`OvertimeHours`
- `inventory_aging_monthly.csv`：字段为 `PlantCode`、`Month`、`AverageDaysInStorage`、`NearExpirySharePct`
- `equipment_reliability_monthly.csv`：字段为 `PlantCode`、`Month`、`UnplannedDowntimeHours`、`SensorAlarmRatePct`

请完成以下工作：

1. 按 `PlantCode` 和 `Month` 合并全部 5 张表，并按 `PlantCode`、`Month` 升序处理。
2. 只处理 `NorthDock` 和 `SouthHub` 两座仓库，并且必须分别独立建模；不要把两座仓库混在一起做一次总分析。
3. 在每座仓库内，把 8 个驱动变量分成 4 类：
   - `TemperatureDiscipline`：`DoorOpenMinutesPerPallet`、`SetpointDeviationC`
   - `OperationsPressure`：`RushOrdersPct`、`OvertimeHours`
   - `InventoryAging`：`AverageDaysInStorage`、`NearExpirySharePct`
   - `EquipmentReliability`：`UnplannedDowntimeHours`、`SensorAlarmRatePct`
4. 在每座仓库内，对这 8 个驱动变量先做 z-score 标准化，再做一次全局 PCA，只保留前 4 个主成分，并对这 4 个主成分做一次正交 varimax 旋转；如果你使用等价方法，得到的旋转后分量空间必须与上述流程一致。
5. 用每个旋转后分量在各类别原始变量上的绝对载荷总和，给 4 个类别各匹配 1 个旋转后分量；匹配时应选择总载荷和最大的那组一一对应关系。
6. 以 `SpoilageLossPct` 为响应变量，用这 4 个已匹配的旋转后分量得分拟合线性模型，计算完整模型的 `R²`。
7. 每次去掉 1 个类别对应的旋转后分量，重新计算 `R²`，把 `完整模型 R² - 去掉该类别后的 R²` 作为该类别的贡献降幅；若降幅为负，则按 0 处理。
8. 只对 4 个类别的正贡献降幅做归一化，使其转成百分比份额。
9. 对每座仓库，找出贡献最高的类别，并计算它相对次高类别的领先百分点：`lead_over_runner_up_pct = dominant_contribution_pct - second_highest_contribution_pct`。

把结果写到 `/root/output/plant_spoilage_driver_comparison.csv`，要求：

- 文件必须包含表头和 2 行结果
- 列名必须严格为 `plant_code`、`dominant_driver_category`、`dominant_contribution_pct`、`lead_over_runner_up_pct`
- `plant_code` 必须恰好覆盖 `NorthDock` 和 `SouthHub`，各出现一次
- `dominant_driver_category` 只能取 `TemperatureDiscipline`、`OperationsPressure`、`InventoryAging`、`EquipmentReliability` 之一
- `dominant_contribution_pct` 与 `lead_over_runner_up_pct` 都必须是百分比数值，保留 1 位小数
- 两行结果必须按 `plant_code` 升序排列
