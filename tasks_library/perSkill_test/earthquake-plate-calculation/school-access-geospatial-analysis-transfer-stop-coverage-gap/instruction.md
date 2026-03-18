你是一名城市可达性分析师。请读取 `/root/school_locations.csv` 和 `/root/bus_stops.csv`，审计每所学校在 400 米步行范围内可达的公交站点覆盖情况，并将结果写入 `/root/school_stop_coverage.json`。

两份输入文件中的 `easting_m` 和 `northing_m` 都已经是 `EPSG:32618` 下的米制坐标，不要把它们当成经纬度。请用这些坐标创建点，并在同一坐标系下完成缓冲区和空间计数。

规则如下：

- 对每所学校构造半径 400 米的缓冲区。
- 统计每个缓冲区内公交站点的数量，字段名为 `reachable_stop_count`。
- 设最低服务目标为 3 个站点，`coverage_gap = max(0, 3 - reachable_stop_count)`。
- 覆盖最差学校定义为 `coverage_gap` 最大的学校；若并列，则选择 `reachable_stop_count` 更少的学校；若仍并列，则选择 `school_id` 字典序更小的学校。

输出 JSON 必须包含以下字段：

- `metric_crs`: 固定写为 `EPSG:32618`
- `buffer_radius_m`: 固定写为 `400`
- `minimum_stop_target`: 固定写为 `3`
- `worst_school`: 对象，包含：
  - `school_id`
  - `school_name`
  - `reachable_stop_count`
  - `coverage_gap`
- `school_audit`: 数组，包含所有学校的上述四个字段，并按以下顺序排序：
  - `coverage_gap` 降序
  - `reachable_stop_count` 升序
  - `school_id` 升序

不要输出额外说明文字，只写目标 JSON 文件。
