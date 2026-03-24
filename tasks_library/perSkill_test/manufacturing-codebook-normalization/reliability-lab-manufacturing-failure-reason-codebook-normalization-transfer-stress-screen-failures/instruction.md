可靠性实验室会在热循环、振动和高温老化应力筛选中留下大量临时失败备注，里面常混有中英夹写、缩写、台架口语和不完整判断。你的任务是把这些备注规范化到统一的可靠性失效原因代码表，并把结果写到 `/app/output/reliability_failure_reason_map.json`。

输入文件位于 `/app/data/`:
- `stress_screen_runs.tsv`: 每行一条应力筛选失败记录，字段使用制表符分隔。
- `reliability_failure_codebook.yaml`: 标准失效原因代码表，包含 `allowed_screen_types`、`allowed_phases` 和 `allowed_benches` 约束。

输出 JSON 必须使用下面的格式：

```json
{
  "experiments": [
    {
      "run_id": "",
      "program_id": "",
      "screen_type": "",
      "phase": "",
      "bench_id": "",
      "technician_id": "",
      "lot_id": "",
      "unit_sn": "",
      "failure_note": "",
      "chamber_profile": "",
      "normalized_failures": [
        {
          "segment_id": "",
          "span_text": "",
          "pred_code": "",
          "pred_label": "",
          "confidence": 0.0,
          "rationale": ""
        }
      ]
    }
  ]
}
```

要求：
- `segment_id` 必须是 `<run_id>-S<i>`，每条记录内从 1 开始。
- `span_text` 必须是 `failure_note` 中的原始连续子串，不能改写。
- 一条备注里可能有多个独立失效；请按独立失效分段，但不要把同一失效的中英重复描述拆成两段。
- `pred_code` 和 `pred_label` 必须来自代码表；若证据不足，或 `screen_type`、`phase`、`bench_id` 任一约束不满足，则输出 `pred_code = "UNKNOWN"` 且 `pred_label = ""`。
- 必须同时遵守 `allowed_screen_types`、`allowed_phases` 和 `allowed_benches`。
- 相同 `lot_id` 或相同 `bench_id` 的上下文可作为辅助证据，但不能覆盖掉明显冲突的筛选类型、阶段或台架限制。
- `confidence` 必须是 `[0.0, 1.0]` 之间的数值，保留 4 位小数；已知失效通常应高于 `UNKNOWN`。
- `rationale` 需要简短但具体，至少引用 `screen_type`、`phase`、`bench_id`，并在有帮助时引用 `lot_id` 或命中的关键词。

只写入要求的输出文件，不要生成额外说明文件。
