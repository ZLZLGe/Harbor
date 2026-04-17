# 任务说明（空间分析模板）

你需要对网格化观测区域做确定性统计，输出可验证的空间分析报表。

## 输入
- 输入文件：`/app/workspace/input/tiles.csv`
- 字段定义：
  - `tile_id`：网格编号（字符串）
  - `area_km2`：面积（平方公里）
  - `population`：人口数（整数）
  - `elevation_m`：海拔（米）

## 输出
- 输出文件：`/app/workspace/output/spatial_report.csv`
- 必须包含且仅包含以下字段（顺序固定）：
  - `tile_id`
  - `pop_density`
  - `population_band`
  - `relief_index`

## 处理规则
1. `pop_density = population / area_km2`，保留 3 位小数。
2. `population_band` 规则：
   - `pop_density >= 8000` -> `high`
   - `6000 <= pop_density < 8000` -> `medium`
   - `pop_density < 6000` -> `low`
3. `relief_index = elevation_m / 1000`，保留 3 位小数。
4. 输出按 `pop_density` 降序；若相同按 `tile_id` 升序。
5. 空值必须输出空字符串，不允许 `null`/`nan`。

## 禁止事项
- 不允许重命名输出字段。
- 不允许写额外主结果文件。
- 不允许依赖随机策略或联网接口。
