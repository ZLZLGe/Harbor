# Transfer: 微震频谱事件分组

## 任务目标

你需要先在校准台站的频谱峰值数据上搜索一组 DBSCAN 参数，再用最佳参数对待分析台站的峰值做聚类，并把事件簇摘要写入 `/root/seismic_event_clusters.csv`。

## 数据

数据位于 `/root/data/`：

- `calibration_peaks.csv`：校准台站上的离散峰值，列为 `station_id, peak_id, time_sec, frequency_hz, amplitude_db`
- `calibration_reference_events.csv`：校准台站的参考事件中心，列为 `station_id, reference_event_id, event_time_sec, event_frequency_hz`
- `survey_peaks.csv`：待分析台站上的离散峰值，列为 `station_id, peak_id, time_sec, frequency_hz, amplitude_db`

所有聚类都只能在同一个 `station_id` 内进行，不能跨台站混合。

## 参数搜索空间

遍历以下全部组合：

- `min_samples`: `3, 4`
- `epsilon`: `0.70, 0.85, 1.00, 1.15`
- `time_weight`: `0.8, 1.0, 1.2, 1.4, 1.6`

## 距离定义

先把时间轴和频率轴做固定归一化：

- `normalized_time = time_sec / 1.5`
- `normalized_frequency = frequency_hz / 20.0`

对同一台站内的两个峰值 `a` 与 `b`，DBSCAN 使用如下距离：

```text
distance(a, b) =
sqrt(
  (time_weight * (a_normalized_time - b_normalized_time))^2 +
  ((2 - time_weight) * (a_normalized_frequency - b_normalized_frequency))^2
)
```

## 校准集评估

对每一组参数：

1. 遍历 `calibration_reference_events.csv` 中出现的全部 `station_id`
2. 在该台站的 `calibration_peaks.csv` 上运行 DBSCAN
3. 对每个非噪声簇计算簇中心 `(center_time_sec, center_frequency_hz)`
4. 用归一化后的标准欧氏距离，把簇中心与参考事件做贪心匹配：每次取当前最近的一对，匹配阈值为 `0.90`
5. 对每个台站计算：
   - `precision = tp / (tp + fp)`
   - `recall = tp / (tp + fn)`
   - `F1 = 2 * precision * recall / (precision + recall)`
   - `centroid_error =` 当前台站所有成功匹配距离的平均值

特殊情况：

- 如果某个台站没有峰值、没有形成任何簇、或没有成功匹配，则该台站 `F1 = 0.0`
- 这些台站的 `centroid_error` 记为 `NaN`
- 最终 `validation_f1` 对全部校准台站取平均
- 最终 `validation_mean_centroid_error` 只对非 `NaN` 的台站误差取平均

## 最优参数判定

按以下顺序选择唯一最佳配置：

1. `validation_f1` 更高
2. `validation_mean_centroid_error` 更低
3. `epsilon` 更小
4. `min_samples` 更小
5. `time_weight` 更小

## 生成待分析事件结果

把最佳配置应用到 `survey_peaks.csv`：

1. 仍然按 `station_id` 分开聚类
2. 丢弃噪声点
3. 对每个非噪声簇输出一行摘要
4. 先按 `center_time_sec` 升序、再按 `center_frequency_hz` 升序为同一台站内的簇排序
5. 事件编号写成 `station_id_E01`、`station_id_E02` 这类形式

## 输出

写入 `/root/seismic_event_clusters.csv`，列必须按以下顺序：

```csv
station_id,event_id,peak_count,start_time_sec,end_time_sec,center_time_sec,min_frequency_hz,max_frequency_hz,center_frequency_hz,mean_amplitude_db,selected_time_weight,selected_epsilon,selected_min_samples
```

要求：

- `peak_count` 和 `selected_min_samples` 写成整数
- `start_time_sec`、`end_time_sec`、`center_time_sec`、`min_frequency_hz`、`max_frequency_hz`、`center_frequency_hz`、`mean_amplitude_db` 保留 3 位小数
- `selected_time_weight` 保留 1 位小数
- `selected_epsilon` 保留 2 位小数
- 行顺序按 `station_id` 升序，再按同一台站内的事件顺序输出
