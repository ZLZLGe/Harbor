你需要为一份带有扫描碎片的 3D 网格文件生成主零件的材料成本估算报告。

输入文件：

- `environment/scan_input.stl`
- `environment/material_price_table.md`

请完成以下工作：

1. 解析这个二进制 STL 文件，并从中识别出体积最大的连通主体，忽略掉扫描碎片。
2. 读取主零件在三角面记录末尾 2 字节中存放的材料编号。
3. 根据 `environment/material_price_table.md` 中的单价表，计算主零件的估算成本。
4. 将结果写入 `output/pricing_report.json`，格式如下：

```json
{
  "main_part_estimated_cost": 123.45,
  "material_id": 25
}
```

要求：

- 结果中的 `material_id` 必须精确正确。
- `main_part_estimated_cost` 允许的相对误差不超过 `0.1%`。
- 不要把扫描碎片计入主零件结果。
