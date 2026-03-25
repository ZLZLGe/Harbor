你接手的是一次已经跑完的 Lake Mendota 温度剖面复核。环境里已经提供了这三个输入文件：

- `/root/data/mendota_stratified_output.nc`
- `/root/config/glm3.nml`
- `/root/data/alignment_observations.csv`

请生成 `/root/reports/temperature_alignment_report.json`，用于汇总模拟温度与观测温度的对齐误差。

按下面规则处理：

1. 从 `/root/config/glm3.nml` 读取模拟起始时间 `start` 和湖深 `lake_depth`。
2. `mendota_stratified_output.nc` 里的 `time` 表示自模拟起点起经过的小时数。
3. NetCDF 里的 `z` 是“距湖底的高度”，不是“水面以下深度”；必须先换算成 `depth_from_surface = lake_depth - z`。
4. 将模拟深度和观测深度都四舍五入到最接近的整数米，再按 `datetime` 和取整后的深度做精确匹配。
5. 输出 JSON 至少包含这些字段，且对应值必须是 JSON 数字（不是字符串）：
   - `lake_depth_m`
   - `surface_max_depth_m`
   - `deep_min_depth_m`
   - `valid_match_count`
   - `total_rmse_c`
   - `surface_rmse_c`
   - `deep_rmse_c`
   - `mean_bias_c`

指标定义：

- `valid_match_count`：成功匹配上的观测条数。
- `total_rmse_c`：所有匹配条目的 RMSE。
- `surface_rmse_c`：匹配条目中，取整后深度 `<= 5` 米的 RMSE。
- `deep_rmse_c`：匹配条目中，取整后深度 `>= 15` 米的 RMSE。
- `mean_bias_c`：所有匹配条目上 `temp_sim - temp_obs` 的平均值。

只要最终 JSON 满足上述契约即可，字段顺序不限。
