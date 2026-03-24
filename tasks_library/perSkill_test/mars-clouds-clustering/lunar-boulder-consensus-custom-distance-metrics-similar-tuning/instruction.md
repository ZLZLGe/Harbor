# Similar: 月表巨石共识聚类

## 任务目标

你需要在月表巨石志愿者点击数据上搜索一组 DBSCAN 参数，并把验证集上的最佳配置写入 `/root/boulder_best_config.json`。

## 数据

数据位于 `/root/data/`：

- `boulder_clicks_validation.csv`：志愿者点击，列为 `tile_id, click_id, x, y`
- `boulder_expert_validation.csv`：专家标注，列为 `tile_id, boulder_id, x, y`
- `tile_metadata.csv`：每个切片的成像主方向，至少使用 `tile_id, track_angle_deg`

只在同一个 `tile_id` 内聚类和评估。

## 参数搜索空间

遍历以下所有组合：

- `min_samples`: `3, 4, 5, 6`
- `epsilon`: `10, 12, 14, 16, 18, 20, 22`
- `direction_weight`: `1.0, 1.2, 1.4, 1.6, 1.8`

## 距离定义

对同一切片中的两个点击点 `a` 与 `b`，先计算：

- `dx = a_x - b_x`
- `dy = a_y - b_y`
- `theta = track_angle_deg` 对应的弧度值

再把位移旋转到沿轨方向与横轨方向：

- `d_track = cos(theta) * dx + sin(theta) * dy`
- `d_cross = -sin(theta) * dx + cos(theta) * dy`

DBSCAN 使用的距离为：

```text
distance(a, b) = sqrt(((2 - w) * d_track)^2 + (w * d_cross)^2)
```

其中 `w = direction_weight`。

## 评估方式

对每组参数：

1. 遍历 `boulder_expert_validation.csv` 中出现的全部 `tile_id`
2. 对该切片中的志愿者点击运行 DBSCAN
3. 对每个非噪声簇计算质心
4. 用标准欧氏距离把簇质心与专家点做贪心匹配：每次取当前最近的一对，匹配阈值为 `60` 像素
5. 对每个切片计算：
   - `precision = tp / (tp + fp)`
   - `recall = tp / (tp + fn)`
   - `F1 = 2 * precision * recall / (precision + recall)`
   - `centroid_error =` 当前切片所有成功匹配距离的平均值

特殊情况：

- 如果某个切片没有志愿者点击、没有形成任何簇、或没有成功匹配，则该切片 `F1 = 0.0`
- 这些切片的 `centroid_error` 记为 `NaN`
- 最终 `validation_f1` 需要对全部切片取平均
- 最终 `validation_mean_centroid_error` 只对非 `NaN` 的切片误差取平均

## 最优配置判定

按以下顺序选择唯一最佳配置：

1. `validation_f1` 更高
2. `validation_mean_centroid_error` 更低
3. `epsilon` 更小
4. `min_samples` 更小
5. `direction_weight` 更小

## 输出

写入 `/root/boulder_best_config.json`，格式为：

```json
{
  "min_samples": 3,
  "epsilon": 22,
  "direction_weight": 1.2,
  "validation_f1": 0.65752,
  "validation_mean_centroid_error": 23.67871
}
```

要求：

- 输出必须是合法 JSON 对象
- `min_samples` 和 `epsilon` 写成整数
- `direction_weight` 保留 1 位小数
- `validation_f1` 与 `validation_mean_centroid_error` 保留 5 位小数
