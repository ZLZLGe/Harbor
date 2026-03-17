你是一名基层医疗服务空间分析师。请读取 `/root/rural_settlements.geojson`、`/root/rural_clinics.geojson` 和 `/root/county_boundaries.geojson`，完成乡村聚落到诊所的最近服务区分配，并将结果写入 `/root/clinic_service_summary.csv`。

要求如下：

- 只把严格落在县级边界面内的聚落和诊所视为合法对象，县外点位全部忽略。
- 先将合法对象投影到 `EPSG:32648`，再按公里计算距离。
- 每个合法聚落只能分配给与它位于同一县域的最近诊所。
- 如果某个聚落所在县没有任何合法诊所，则该聚落不进入最终统计。
- 输出时要对每一家合法诊所汇总其服务情况；即使某家合法诊所没有分配到任何聚落，也必须保留该诊所一行。

输出 CSV 必须包含以下列，列顺序也必须一致：

- `clinic_id`
- `clinic_name`
- `county_id`
- `county_name`
- `assigned_settlement_count`
- `max_service_distance_km`

其中：

- `assigned_settlement_count` 为分配到该诊所的聚落数量。
- `max_service_distance_km` 为该诊所已分配聚落中最远一条服务距离，单位为公里，保留 2 位小数。
- 若某诊所没有分配到任何聚落，`max_service_distance_km` 写 `0.00`。
- 最终 CSV 需要按 `county_id` 升序、再按 `clinic_id` 升序排序。
- 输出文件不要包含额外索引列。
