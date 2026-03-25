你接手的是一次针对 Blue Heron Lake 冷水鱼类夏季栖息地的快速复核。环境里已经提供了这两个输入文件：

- `/root/data/blue_heron_output.nc`
- `/root/config/refuge_rules.toml`

请生成 `/root/reports/refuge_thickness_daily.csv`。

按下面规则处理：

1. 从 `refuge_rules.toml` 读取：
   - `simulation_start`
   - `lake_depth_m`
   - `refuge_min_temp_c`
   - `refuge_max_temp_c`
   - `summer_start_date`
   - `summer_end_date`
   - `collapse_threshold_m`
2. NetCDF 里的 `time` 表示自 `simulation_start` 起经过的小时数。
3. NetCDF 里的 `z` 是“距湖底的高度”，不是“水面以下深度”；必须先换算成 `depth_from_surface_m = lake_depth_m - z`。
4. 对每一个模型时间步，只保留 `z` 和 `temp` 都有效的层，并按 `depth_from_surface_m` 从浅到深排序。
5. 用层中心深度重建每层代表的厚度：
   - 最浅层上边界固定为 `0`
   - 最深层下边界固定为 `lake_depth_m`
   - 相邻两层之间的边界取这两层中心深度的中点
   - 单层厚度等于它的下边界减去上边界
6. 温度满足 `refuge_min_temp_c <= temp <= refuge_max_temp_c` 的层，计入该时间步的冷水栖息地厚度；该时间步厚度等于所有满足条件层厚度之和。
7. 将同一日内所有时间步的冷水栖息地厚度取算术平均，得到该日的 `refuge_thickness_m`。
8. 输出 CSV 必须按日期升序排列，并且对 NetCDF 中出现的每个日历日都输出一行。
9. CSV 必须且只需包含这 4 列：
   - `date`
   - `refuge_thickness_m`
   - `summer_minimum_flag`
   - `first_collapse_flag`
10. `date` 使用 `YYYY-MM-DD`。
11. `summer_minimum_flag` 规则：
   - 只在 `summer_start_date` 到 `summer_end_date`（含首尾）的日期里比较
   - 找到 `refuge_thickness_m` 最小的那一天
   - 如果最小值有并列，只标记最早的一天为 `1`
   - 其他所有行写 `0`
12. `first_collapse_flag` 规则：
   - 只在 `summer_start_date` 到 `summer_end_date`（含首尾）的日期里检查
   - 把 `refuge_thickness_m < collapse_threshold_m` 视为栖息地崩塌
   - 只标记第一天崩塌日为 `1`
   - 如果整个夏季窗口都没有崩塌，则这一列全部写 `0`

只要最终 CSV 满足上述契约即可，不要求额外输出别的文件。
