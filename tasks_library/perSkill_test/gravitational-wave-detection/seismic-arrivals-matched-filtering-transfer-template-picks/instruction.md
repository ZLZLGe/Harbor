# 任务说明

一条连续地震台站波形里混入了两类重复事件：`microquake` 和 `blast`。你需要直接使用给定样本值做模板相关扫描，为每一类事件输出到时列表和对应匹配得分，并把结果写到 `/root/seismic_arrivals.json`。

输入文件：

- `/root/data/station_trace.csv`：连续波形，表头固定为 `sample_index,amplitude`。
- `/root/data/template_catalog.json`：模板目录，包含：
  - `station_id`
  - `sample_rate_hz`
  - `trace_start_time_s`
  - `templates`：数组。每个元素都包含 `event_type`、`detection_threshold`、`min_separation_samples`、`samples`

对目录中的每个模板，设连续波形为 `trace`，模板样本为 `template`，模板长度为 `M`。按下面定义计算响应序列：

```text
response[k] = sum(template[j] * trace[k + j] for j in 0..M-1)
score[k] = abs(response[k])
```

其中 `k` 从 `0` 扫到 `len(trace) - M`。

然后对每个模板单独做拾取：

1. 按 `score[k]` 从大到小遍历所有候选位置。
2. 只接受 `score[k] >= detection_threshold` 的候选。
3. 如果某个候选位置 `k` 与任何已接受位置的距离小于 `min_separation_samples`，则丢弃它。
4. 其余候选保留为该模板的有效到时。
5. 最后把该模板的有效到时按 `arrival_sample` 从小到大排序。

对每个保留到时，输出：

- `arrival_sample`：候选位置 `k`
- `arrival_time_s`：`trace_start_time_s + (k + M / 2) / sample_rate_hz`
- `match_score`：`score[k]`

把 `/root/seismic_arrivals.json` 写成一个 JSON 对象，格式如下：

```json
{
  "station_id": "QH01",
  "detections": {
    "microquake": [
      {
        "arrival_sample": 0,
        "arrival_time_s": 0.0,
        "match_score": 0.0
      }
    ],
    "blast": [
      {
        "arrival_sample": 0,
        "arrival_time_s": 0.0,
        "match_score": 0.0
      }
    ]
  }
}
```

要求：

- `station_id` 必须等于目录文件里的 `station_id`。
- `detections` 下的键必须和目录文件中出现的 `event_type` 完全一致。
- 每个事件类型的列表都必须按 `arrival_sample` 升序排列。
- `arrival_sample` 必须是整数；`arrival_time_s` 和 `match_score` 必须是有限数值。
- 不要重采样、滤波、归一化或裁剪输入波形；直接使用文件中的样本值。
- 不需要输出中间文件，也不需要生成额外报告。
