你需要根据 `/root/data/` 中的年尺度水库数据，识别藻华强度最主要的驱动类别。

可用输入文件：

- `annual_bloom.csv`：字段为 `WaterYear`、`BloomSeverityIndex`
- `reservoir_meteorology.csv`：字段为 `WaterYear`、`SurfaceTempAnomaly`、`SunlightHours`
- `reservoir_nutrients.csv`：字段为 `WaterYear`、`TPLoad`、`TNLoad`
- `reservoir_hydrodynamics.csv`：字段为 `WaterYear`、`ResidenceDays`、`MixingDepth`
- `shoreline_development.csv`：字段为 `WaterYear`、`ImperviousPct`、`DockDensity`

请完成以下工作：

1. 按 `WaterYear` 合并全部 5 张表。
2. 把 8 个驱动变量分为 4 类：
   - `Meteorology`：`SurfaceTempAnomaly`、`SunlightHours`
   - `Nutrient`：`TPLoad`、`TNLoad`
   - `Hydrodynamics`：`ResidenceDays`、`MixingDepth`
   - `Shoreline`：`ImperviousPct`、`DockDensity`
3. 对这 8 个驱动变量先做 z-score 标准化，再做一次全局 PCA，保留前 4 个主成分。
4. 用每个主成分在各类别原始变量上的绝对载荷总和，做四类与四个主成分的一一匹配。
5. 以 `BloomSeverityIndex` 为响应变量，用这 4 个主成分拟合线性模型并计算完整模型的 `R²`。
6. 每次去掉一个已匹配的类别主成分，重新计算 `R²`，得到该类别的 `R²` 降幅。
7. 只对 4 个类别里大于 0 的 `R²` 降幅做归一化，使它们之和为 100%，然后只保留贡献最大的类别。

把结果写到 `/root/output/dominant_bloom_driver.csv`，要求：

- 文件必须包含表头且只有 1 行结果
- 列名必须严格为 `driver_category` 和 `normalized_contribution_pct`
- `driver_category` 必须是 `Meteorology`、`Nutrient`、`Hydrodynamics`、`Shoreline` 之一
- `normalized_contribution_pct` 是百分比数值，保留 1 位小数
