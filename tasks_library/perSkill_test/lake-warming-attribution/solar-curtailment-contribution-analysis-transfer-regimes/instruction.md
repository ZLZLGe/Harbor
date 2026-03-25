你需要基于 `/root/data/` 中的调度区块级数据，分别在两个运行工况内识别造成光伏弃电的主导驱动类别。

可用输入文件：

- `dispatch_blocks.csv`：字段为 `BlockHour`、`operating_regime`、`CurtailmentMWh`
- `weather_block.csv`：字段为 `BlockHour`、`IrradianceWm2`、`CloudCoverPct`
- `load_absorption_block.csv`：字段为 `BlockHour`、`LocalLoadMW`、`StorageAbsorptionMW`
- `maintenance_availability_block.csv`：字段为 `BlockHour`、`ThermalAvailabilityPct`、`OutageSharePct`
- `export_congestion_block.csv`：字段为 `BlockHour`、`InterfaceLoadingPct`、`ExportPriceSpreadUsdMWh`

请完成以下工作：

1. 按 `BlockHour` 合并全部 5 张表，并保留 `dispatch_blocks.csv` 中的 `operating_regime` 与 `CurtailmentMWh`。
2. 只处理 `export_constrained` 与 `balanced` 这两个运行工况，并且分别独立建模，不能把两个工况混在一起做一次总分析。
3. 在每个工况内，把 8 个驱动变量分成 4 类：
   - `Weather`：`IrradianceWm2`、`CloudCoverPct`
   - `DemandAbsorption`：`LocalLoadMW`、`StorageAbsorptionMW`
   - `MaintenanceAvailability`：`ThermalAvailabilityPct`、`OutageSharePct`
   - `ExportCongestion`：`InterfaceLoadingPct`、`ExportPriceSpreadUsdMWh`
4. 对每个工况内的 8 个驱动变量先做 z-score 标准化，再做一次全局 PCA 或等价的 SVD 降维，只保留前 4 个主成分。
5. 用每个主成分在各类别原始变量上的绝对载荷总和，为 4 个类别各匹配 1 个主成分；匹配时应选择总载荷和最大的那组一一对应关系。
6. 以 `CurtailmentMWh` 为响应变量，用这 4 个已匹配主成分拟合线性模型，计算完整模型的 `R²`。
7. 每次去掉 1 个类别对应的主成分，重新计算 `R²`，把 `完整模型 R² - 去掉该类别后的 R²` 作为该类别的贡献降幅；若降幅为负，则按 0 处理。
8. 只对 4 个类别的正贡献降幅做归一化，使其转成百分比份额，并在每个工况内只保留贡献最大的那个类别。

把结果写到 `/root/output/curtailment_regime_attribution.json`，要求：

- 顶层必须是 JSON object，且只能包含 `export_constrained` 与 `balanced` 两个键
- 每个工况键对应的值也必须是 JSON object，且列名式键必须严格为 `dominant_driver` 和 `normalized_contribution_pct`
- `dominant_driver` 必须是该工况内贡献最高的类别，且只能取 `Weather`、`DemandAbsorption`、`MaintenanceAvailability`、`ExportCongestion` 之一
- `normalized_contribution_pct` 必须是百分比数值，保留 1 位小数
- 两个工况都必须有结果，不能缺项，也不能额外输出其他工况
