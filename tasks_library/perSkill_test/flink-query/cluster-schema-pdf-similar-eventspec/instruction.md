你会在 `/app/workspace/input/cluster_schema.pdf` 中拿到一份集群追踪格式说明文档。请从这份 PDF 中提取与 `job_events` 和 `task_events` 直接相关的结构化规范，并把最终结果写入 `/app/artifacts/cluster_event_schema.json`。

只需要产出这一个 JSON 文件，不要额外输出说明文档。JSON 顶层必须使用下面这些键：

```json
{
  "source_document": "input/cluster_schema.pdf",
  "document_title": "...",
  "time_semantics": {
    "unit": "microseconds",
    "base_reference": "...",
    "usage_measurement_precision": "...",
    "usage_measurement_reporting": "...",
    "special_values": [
      {"value": "0", "meaning": "..."},
      {"value": "2^63-1", "meaning": "..."}
    ]
  },
  "event_type_codes": [
    {"code": 0, "name": "SUBMIT", "meaning": "..."}
  ],
  "job_events": {
    "field_count": 8,
    "fields": [
      {"position": 1, "name": "timestamp", "meaning": "..."}
    ]
  },
  "task_events": {
    "field_count": 13,
    "fields": [
      {"position": 1, "name": "timestamp", "meaning": "..."}
    ]
  }
}
```

规范要求：

1. 所有 `name` 字段都必须使用下面这组固定的 snake_case 名称，并保持字段顺序与 PDF 一致。
   - `job_events.fields`: `timestamp`, `missing_info`, `job_id`, `event_type`, `user_name`, `scheduling_class`, `job_name`, `logical_job_name`
   - `task_events.fields`: `timestamp`, `missing_info`, `job_id`, `task_index`, `machine_id`, `event_type`, `user_name`, `scheduling_class`, `priority`, `cpu_request`, `ram_request`, `local_disk_space_request`, `different_machine_constraint`
2. `event_type_codes` 必须覆盖 0 到 8 的全部事件编码，并按编码升序排列。
3. `time_semantics.unit` 必须明确写成 `microseconds`，同时保留“相对 trace 开始前 600 秒”的时间基准说明，以及 PDF 中给出的两个特殊时间值。
4. 所有说明性字符串都使用英文，内容应来自 PDF 的语义归纳，不要写与任务无关的背景介绍。
5. `field_count` 必须分别与字段数组长度一致。

不要依赖任何额外输入文件；这道题的唯一输入资产就是这份 PDF。
