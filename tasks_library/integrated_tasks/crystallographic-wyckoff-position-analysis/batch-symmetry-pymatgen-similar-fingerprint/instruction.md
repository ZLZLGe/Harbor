你需要处理一批位于 `/root/structures/` 的 CIF 晶体结构文件，并生成一个批量对称性指纹报告。

请在 `/root/workspace/solution.py` 中实现下面的入口函数：

```python
def build_symmetry_fingerprint_report(
    input_dir: str,
    output_path: str = "/root/workspace/symmetry_fingerprint_report.json",
) -> dict:
```

要求：

1. 扫描 `input_dir` 下全部 `.cif` 文件，并按文件名排序后逐个处理。
2. 对每个结构先做标准化，再提取对称性信息。
3. 生成的报告必须写入 `output_path`，同时函数返回相同内容的 Python 字典。
4. 报告 JSON 的顶层结构必须为：

```json
{
  "input_directory": "/root/structures",
  "sample_count": 0,
  "samples": {
    "example.cif": {
      "space_group_number": 0,
      "crystal_system": "cubic",
      "equivalent_site_group_count": 0,
      "wyckoff_representatives": {
        "a": {
          "species": "Si",
          "frac_coords": [0.0, 0.0, 0.0]
        }
      }
    }
  }
}
```

5. `equivalent_site_group_count` 表示标准化后等价位点分组的数量。
6. `wyckoff_representatives` 以 Wyckoff 字母为键；如果同一字母在同一结构中对应多个等价位点分组，只保留标准化结构中首次出现的那一组代表位点。
7. `species` 只保留元素符号，不要带氧化态；如果站点包含多个元素，按字母序用 `-` 连接。
8. `frac_coords` 使用代表位点的分数坐标，归一化到 `[0, 1)`，并保留 6 位小数。
9. 输出 JSON 使用 UTF-8 编码，`indent=2`，并设置 `sort_keys=True`。
10. 不要硬编码结果。

可以使用常见的晶体结构分析库与标准 Python 库。
