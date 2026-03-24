IQC 来料检验会收到很多供应商批次异常备注，文本里常混有中英夹写、口语化缩写和不完整描述。你的任务是把这些备注规范化到统一的来料物料缺陷代码表，并把结果写到 `/app/output/iqc_supplier_reason_map.json`。

输入文件位于 `/app/data/`:
- `iqc_supplier_lots.csv`: 每行一条供应商批次抽检记录。
- `material_defect_codebook.json`: 标准物料缺陷代码表，包含 `allowed_categories` 与 `allowed_stages`。

输出 JSON 必须使用下面的格式：

```json
{
  "lots": [
    {
      "inspection_id": "",
      "supplier_id": "",
      "supplier_lot": "",
      "material_code": "",
      "item_category": "",
      "inspection_stage": "",
      "inspector_id": "",
      "sample_size": 0,
      "defect_remark": "",
      "normalized_reasons": [
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
- `segment_id` 必须是 `<inspection_id>-S<i>`，每条记录内从 1 开始。
- `span_text` 必须是 `defect_remark` 中的原始连续子串，不能改写。
- 一条备注里可能有多个独立异常；请按独立异常分段，但不要把同一异常的中英重复描述拆成两段。
- `pred_code` 和 `pred_label` 必须来自代码表；若证据不足或类别/检验阶段限制导致候选代码不可用，则输出 `pred_code = "UNKNOWN"` 且 `pred_label = ""`。
- 必须同时遵守 `allowed_categories` 和 `allowed_stages`。
- 相同 `supplier_lot` 的上下文可作为辅助证据，但不能覆盖掉明显冲突的类别或阶段限制。
- `confidence` 必须是 `[0.0, 1.0]` 之间的数值，保留 4 位小数；已知缺陷通常应高于 `UNKNOWN`。
- `rationale` 需要简短但具体，至少引用 `item_category`、`inspection_stage`，并在有帮助时引用 `supplier_lot` 或命中的关键词。

只写入要求的输出文件，不要生成额外说明文件。
