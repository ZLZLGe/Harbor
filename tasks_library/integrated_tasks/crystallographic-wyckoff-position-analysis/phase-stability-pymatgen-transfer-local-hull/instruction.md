你需要根据本地给定的组成与总能量条目，构建一个化学体系的相图凸包，并分析若干查询条目的热力学稳定性。

输入文件：

- 条目数据：`/root/phase_entries.json`
- 查询数据：`/root/phase_queries.json`

请在 `/root/workspace/solution.py` 中实现下面的入口函数：

```python
def build_phase_hull_report(
    entries_path: str,
    queries_path: str,
    output_path: str = "/root/workspace/phase_hull_report.json",
) -> dict:
```

要求：

1. `entries_path` 的 JSON 顶层结构固定为：

```json
{
  "entries": [
    {
      "entry_id": "sample_entry",
      "formula": "Li2O",
      "energy": -8.4
    }
  ]
}
```

2. `queries_path` 的 JSON 顶层结构固定为：

```json
{
  "queries": [
    {
      "query_id": "query_1",
      "formula": "Li2O",
      "energy": -7.95
    }
  ]
}
```

3. 所有 `energy` 都表示该条目按输入化学式写法对应的总能量，单位为 eV，不是每原子能量。
4. 先使用 `entries_path` 中的全部条目构建相图凸包；`queries_path` 中的查询条目只用于分析，不要把查询条目再加入用于构建凸包的条目集合。
5. `chemical_system` 需要由所有输入条目中出现的元素符号按字母序连接得到，例如 `Fe-Li-O`。
6. `stable_entries` 只包含凸包上的稳定条目；如果同一组成存在多个条目，应该只保留真正位于凸包上的那些条目。
7. `stable_entries` 必须按 `(reduced_formula, entry_id)` 升序排序；`stable_entry_ids` 与它保持相同顺序。
8. `query_results` 必须保持 `queries_path` 中的原始顺序。
9. 每个查询结果都必须包含：
   - `query_id`
   - `formula`
   - `reduced_formula`
   - `energy`
   - `energy_per_atom`
   - `energy_above_hull`
   - `hull_energy_per_atom`
   - `is_stable`
   - `decomposition`
10. `energy_per_atom`、`energy_above_hull`、`hull_energy_per_atom` 都保留 6 位小数。
11. `is_stable` 只在 `energy_above_hull <= 1e-6` 时输出 `true`，否则输出 `false`。
12. `decomposition` 是一个数组，表示该查询条目在凸包上的分解相；数组元素必须按 `(reduced_formula, entry_id)` 升序排序，每个元素格式为：

```json
{
  "entry_id": "stable_entry",
  "formula": "Li2O",
  "reduced_formula": "Li2O",
  "amount": 1.0
}
```

13. `amount` 保留 6 位小数。
14. 返回值必须是一个 Python 字典，并把完全相同的内容写入 `output_path` 指定的 JSON 文件。
15. 输出 JSON 顶层结构必须为：

```json
{
  "entries_path": "/root/phase_entries.json",
  "queries_path": "/root/phase_queries.json",
  "chemical_system": "Fe-Li-O",
  "entry_count": 0,
  "stable_entry_count": 0,
  "stable_entry_ids": ["sample_entry"],
  "stable_entries": [
    {
      "entry_id": "sample_entry",
      "formula": "Li2O",
      "reduced_formula": "Li2O",
      "energy": -8.4,
      "energy_per_atom": -2.8
    }
  ],
  "query_count": 0,
  "query_results": [
    {
      "query_id": "query_1",
      "formula": "Li2O",
      "reduced_formula": "Li2O",
      "energy": -7.95,
      "energy_per_atom": -2.65,
      "energy_above_hull": 0.15,
      "hull_energy_per_atom": -2.8,
      "is_stable": false,
      "decomposition": [
        {
          "entry_id": "sample_entry",
          "formula": "Li2O",
          "reduced_formula": "Li2O",
          "amount": 1.0
        }
      ]
    }
  ]
}
```

16. 输出 JSON 使用 UTF-8 编码、`indent=2`、`sort_keys=True`。
17. 不要硬编码答案。

可以使用常见的材料分析库与标准 Python 库。
