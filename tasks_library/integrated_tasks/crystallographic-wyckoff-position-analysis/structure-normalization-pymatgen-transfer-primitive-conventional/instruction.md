你需要处理一批位于 `/root/inputs/` 的晶体结构文件。这批文件混合使用了 `CIF` 与 `POSCAR` 风格文本格式。

请在 `/root/workspace/solution.py` 中实现下面的入口函数：

```python
def build_normalization_manifest(
    input_dir: str,
    output_path: str = "/root/workspace/normalization_manifest.json",
) -> dict:
```

要求：

1. 扫描 `input_dir` 下全部结构文件，按文件名排序后逐个处理。
2. 对每个样品读取原始结构，并生成对应的 `primitive cell` 与 `conventional cell`。
3. 返回值必须是一个 Python 字典，并将相同内容写入 `output_path` 指定的 JSON 文件。
4. 输出 JSON 顶层结构必须为：

```json
{
  "input_directory": "/root/inputs",
  "sample_count": 0,
  "sample_order": ["example.cif"],
  "samples": {
    "example.cif": {
      "input_format": "cif",
      "original": {
        "formula": "Si2 O4",
        "site_count": 6,
        "volume": 123.456789,
        "volume_per_atom": 20.576132
      },
      "primitive": {
        "formula": "Si1 O2",
        "site_count": 3,
        "volume": 61.728395,
        "volume_per_atom": 20.576132
      },
      "conventional": {
        "formula": "Si2 O4",
        "site_count": 6,
        "volume": 123.456789,
        "volume_per_atom": 20.576132
      },
      "comparisons_to_original": [
        {
          "target": "primitive",
          "formula": "Si1 O2",
          "site_count": 3,
          "volume_ratio_to_original": 0.5,
          "volume_per_atom_delta": 0.0
        },
        {
          "target": "conventional",
          "formula": "Si2 O4",
          "site_count": 6,
          "volume_ratio_to_original": 1.0,
          "volume_per_atom_delta": 0.0
        }
      ]
    }
  }
}
```

5. `input_format` 只允许输出 `cif` 或 `poscar`。
6. `formula` 使用结构当前晶胞对应的化学式字符串，不要手工约分。
7. `site_count` 为该晶胞中的总站点数。
8. `volume` 与 `volume_per_atom` 都保留 6 位小数。
9. `volume_ratio_to_original` 表示目标晶胞体积除以原始晶胞体积，保留 6 位小数。
10. `volume_per_atom_delta` 表示目标晶胞与原始晶胞的 `volume_per_atom` 差值，保留 6 位小数。
11. 输出 JSON 使用 UTF-8 编码，`indent=2`，并设置 `sort_keys=True`。
12. 不要硬编码结果。

可以使用常见的晶体结构分析库与标准 Python 库。
