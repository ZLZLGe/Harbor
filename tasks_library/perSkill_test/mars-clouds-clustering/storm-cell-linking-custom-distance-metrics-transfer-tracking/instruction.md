# Transfer: 风暴单体跨帧链接

## 任务目标

你需要先在 archive 风暴个例上选出最合适的方向代价配置，再把该配置应用到 live 连续两帧的风暴单体候选，输出最终跨帧链接结果到 `/root/storm_cell_links.csv`。

## 数据

数据位于 `/root/data/`：

- `link_profiles.csv`：候选链接配置，列为 `profile_id,east_west_weight,north_south_weight,max_link_distance_km`
- `archive_prev_cells.csv`：archive 个例前一帧候选，列为 `case_id,frame_time,cell_id,centroid_x_km,centroid_y_km,area_km2,peak_dbz`
- `archive_next_cells.csv`：archive 个例后一帧候选，列为 `case_id,frame_time,cell_id,centroid_x_km,centroid_y_km,area_km2,peak_dbz`
- `archive_manual_links.csv`：archive 个例人工确认的真值链接，列为 `case_id,from_cell_id,to_cell_id`
- `live_prev_cells.csv`：live 待跟踪前一帧候选，列与 archive 前一帧相同
- `live_next_cells.csv`：live 待跟踪后一帧候选，列与 archive 后一帧相同

所有链接都只能在同一个 `case_id` 内完成，不能跨个例混合。

## 距离定义

对同一个 `case_id` 内的前一帧单体 `p` 与后一帧单体 `q`，记：

- `dx = q.centroid_x_km - p.centroid_x_km`
- `dy = q.centroid_y_km - p.centroid_y_km`

若当前候选配置的方向代价参数为：

- `wx = east_west_weight`
- `wy = north_south_weight`

则加权距离定义为：

```text
distance(p, q) = sqrt((wx * dx)^2 + (wy * dy)^2)
```

只有 `distance(p, q) <= max_link_distance_km` 的配对才允许进入链接。

## 单个个例内的贪心链接

对任一 `case_id`，在对应前后两帧候选之间：

1. 构造所有允许配对的候选边
2. 按 `weighted_distance_km` 升序处理
3. 若距离相同，则按 `from_cell_id` 升序，再按 `to_cell_id` 升序打破平局
4. 每次取当前最优的一条边，并移除与该边共享前一帧或后一帧单体的其他候选边
5. 直到没有剩余合法候选边

## archive 配置选择

对 `link_profiles.csv` 中的每个配置：

1. 对 `archive_manual_links.csv` 中出现的每个 `case_id`，分别执行上面的贪心链接
2. 把预测链接集合与该个例的人工真值链接集合比较
3. 对每个个例计算：
   - `tp`：预测且命中的链接数
   - `fp`：预测但不在真值中的链接数
   - `fn`：真值中存在但未被预测到的链接数
   - `F1 = 2 * tp / (2 * tp + fp + fn)`；若 `tp = 0`，则该个例 `F1 = 0.0`
   - `mean_correct_cost`：该个例中所有命中真值链接的 `weighted_distance_km` 平均值；若没有命中链接，则记为 `NaN`
4. 计算：
   - `validation_f1`：全部 archive 个例 `F1` 的平均值
   - `validation_mean_correct_cost`：全部非 `NaN` 的 `mean_correct_cost` 平均值

最佳配置按以下顺序唯一确定：

1. `validation_f1` 更高
2. `validation_mean_correct_cost` 更低
3. `profile_id` 字典序更小

## 生成 live 链接结果

将最佳配置应用到 `live_prev_cells.csv` 与 `live_next_cells.csv`：

1. 仍然只在相同 `case_id` 内构造距离矩阵并执行贪心链接
2. 只输出成功链接的配对，不输出未匹配单体
3. 结果按 `case_id` 升序，再按 `from_cell_id` 升序排列

## 输出

写入 `/root/storm_cell_links.csv`，列顺序必须严格为：

```csv
case_id,from_frame_time,to_frame_time,from_cell_id,to_cell_id,dx_km,dy_km,weighted_distance_km,selected_profile,max_link_distance_km
```

要求：

- `dx_km`、`dy_km` 保留 1 位小数
- `weighted_distance_km` 保留 5 位小数
- `max_link_distance_km` 保留 1 位小数
- `selected_profile` 必须在所有输出行中保持一致，并等于 archive 评估得到的最佳配置
