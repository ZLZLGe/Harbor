SMT AOI 与返修工位会记录很多临时写下的缺陷备注，里面夹杂中英缩写、器件位号、重复表达和工序信息。你的任务是把这些备注规范化到统一的 SMT 缺陷代码表，并把结果写到 `/app/output/aoi_defect_map.json`。

输入文件位于 `/app/data/`:
- `aoi_cases.jsonl`: 每行一个待规范化的板级缺陷记录。
- `aoi_defect_codebook.csv`: 标准缺陷代码表，包含 `allowed_stages` 限制。

输出 JSON 必须使用下面的格式：

```json
{
  "boards": [
    {
      "board_id": "",
      "panel_id": "",
      "product_family": "",
      "process_stage": "",
      "line": "",
      "side": "",
      "operator_id": "",
      "remark_text": "",
      "defect_segments": [
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
- `segment_id` 必须是 `<board_id>-S<i>`，每条记录内从 1 开始。
- `span_text` 必须是 `remark_text` 中的原始连续子串，不能改写。
- 一条备注里可能有多个独立缺陷；请按独立缺陷分段，但不要把同一缺陷的中英重复描述拆成两段。
- `pred_code` 和 `pred_label` 必须来自代码表；若证据不足或工序限制导致不能使用候选代码，则输出 `pred_code = "UNKNOWN"` 且 `pred_label = ""`。
- 必须遵守 `allowed_stages`。例如只允许在回流后 AOI 使用的代码，不能直接用于返修工位记录。
- `confidence` 必须是 `[0.0, 1.0]` 之间的数值，保留 4 位小数；已知缺陷通常应高于 `UNKNOWN`。
- `rationale` 需要简短但具体，至少引用工序、器件位号、关键词命中或其他直接证据。

只写入要求的输出文件，不要生成额外说明文件。
