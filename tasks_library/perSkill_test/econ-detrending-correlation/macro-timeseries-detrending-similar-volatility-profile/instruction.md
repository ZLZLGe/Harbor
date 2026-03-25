你在 `/root/` 会看到一份已经整理好的季度实值宏观面板数据 `us_macro_quarterly_real_panel.csv`。文件包含多个指标、额外年份和无关序列；你只需要基于其中的 3 个目标序列，构造一个商业周期波动率画像。

目标：

1. 从数据中提取以下 3 个序列，并且只保留 `1990Q1` 到 `2024Q4`（含）：
   - `RGDP` -> `GDP`
   - `RPCE` -> `Consumption`
   - `RPFI` -> `Fixed Investment`
2. 对每个目标序列的 `value`：
   - 先取自然对数；
   - 再对季度序列应用 HP 滤波，平滑参数使用 `lambda = 1600`；
   - 使用得到的周期成分计算样本标准差（`ddof=1`）。
3. 以 GDP 的周期标准差为分母，计算每个序列的相对波动率：
   - `relative_volatility_to_gdp = cycle_std / GDP 的 cycle_std`
4. 生成 `/root/cycle_volatility_profile.csv`，并满足以下要求：
   - 必须是 UTF-8 编码的 CSV；
   - 列名必须严格为：`series,series_code,cycle_std,relative_volatility_to_gdp`
   - 一共 3 行数据，分别对应 `GDP`、`Consumption`、`Fixed Investment`
   - 按 `relative_volatility_to_gdp` 从高到低排序
   - `cycle_std` 和 `relative_volatility_to_gdp` 都保留 6 位小数

说明：

- 输入文件里还有其他指标和区间，不要把它们纳入结果。
- `value` 已经是实值，不需要再做通胀调整。
- 最终只需要提交 `cycle_volatility_profile.csv`，不要额外输出别的答案文件。
