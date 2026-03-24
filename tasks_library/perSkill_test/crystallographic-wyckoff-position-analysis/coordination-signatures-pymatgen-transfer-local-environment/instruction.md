你需要分析一批晶体样品中若干目标位点的局域配位环境。

结构文件位于 `/root/coordination_inputs/`，目标位点描述位于 `/root/coordination_targets.json`。请在 `/root/workspace/solution.py` 中实现下面的入口函数：

```python
def build_coordination_signatures(
    structure_dir: str,
    target_spec_path: str,
    output_path: str = "/root/workspace/coordination_signatures.json",
) -> dict:
```

要求：

1. 读取 `target_spec_path` 中的 JSON。其顶层结构固定为：

```json
{
  "samples": {
    "example.cif": [
      {
        "label": "site_a",
        "fractional_coords": [0.1, 0.2, 0.3]
      }
    ]
  }
}
```

2. 按样品文件名排序处理 `samples` 中列出的全部结构文件，并保持每个样品内目标位点的原始顺序。
3. 每个目标位点都要按周期性分数坐标匹配到结构中的唯一真实位点。匹配时请使用分数坐标逐分量容差 `1e-4`，并考虑 `0` 与 `1` 的周期等价。
4. 对每个匹配到的位点，使用固定的近邻判定规则 `CrystalNN(distance_cutoffs=None, x_diff_weight=0.0, porous_adjustment=False)` 获取局域近邻。
5. `coordination_number` 为该规则返回的近邻个数。
6. `neighbor_composition` 为邻居元素统计字典，键使用元素符号，值为出现次数，按元素符号排序。
7. `nearest_bond_length_range` 为该位点到全部近邻的距离最小值与最大值，保留 6 位小数，格式为长度为 2 的数组 `[min_distance, max_distance]`。距离计算必须考虑近邻给出的周期镜像。
8. `fractional_coords` 输出匹配后真实位点的分数坐标，每个分量保留 6 位小数。
9. `coordination_signature` 使用下面的字符串格式：

```text
{center_element}:CN{coordination_number}:{neighbor_formula}:{min_distance:.6f}-{max_distance:.6f}
```

其中 `neighbor_formula` 由 `neighbor_composition` 按元素符号排序后拼接得到，例如 `{"O": 4}` 生成 `O4`，`{"Fe": 2, "S": 4}` 生成 `Fe2-S4`。
10. 返回值必须是一个 Python 字典，并将同样的内容写入 `output_path` 指定的 JSON 文件。
11. 输出 JSON 顶层结构必须为：

```json
{
  "structure_directory": "/root/coordination_inputs",
  "target_spec_path": "/root/coordination_targets.json",
  "sample_count": 0,
  "sample_order": ["example.cif"],
  "samples": {
    "example.cif": {
      "formula": "Si3 O6",
      "target_count": 1,
      "targets": [
        {
          "label": "site_a",
          "site_index": 0,
          "center_element": "Si",
          "fractional_coords": [0.1, 0.2, 0.3],
          "coordination_number": 4,
          "neighbor_composition": {
            "O": 4
          },
          "nearest_bond_length_range": [1.61, 1.62],
          "coordination_signature": "Si:CN4:O4:1.610000-1.620000"
        }
      ]
    }
  }
}
```

12. `formula` 使用结构对象当前晶胞的化学式字符串，不要手工约分。
13. `site_index` 为匹配到的结构位点索引。
14. 输出 JSON 使用 UTF-8 编码、`indent=2`、`sort_keys=True`。
15. 不要硬编码答案。

可以使用常见的晶体结构分析库和标准 Python 库。
