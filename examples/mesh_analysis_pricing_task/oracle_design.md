# Oracle 设计

## 目标

Oracle 必须稳定通过全部测试，并明确展示：

- 主难点由 skill 负责
- 业务逻辑由任务层负责

## Oracle 实现顺序

1. 定位 `environment/skills/mesh-analysis/scripts`。
2. 导入 `mesh_tool.py` 中的 `MeshAnalyzer`。
3. 对 `environment/scan_input.stl` 调用 `analyze_largest_component()`。
4. 读取 `environment/material_price_table.md` 中的 `material_id -> unit_price` 映射。
5. 计算 `main_part_estimated_cost = volume * unit_price`。
6. 输出到 `output/pricing_report.json`。

## 为什么 Oracle 应该 100% 通过

- skill 已覆盖本任务最难的步骤：二进制解析、连通体分析、体积与材料编号提取。
- 任务层额外逻辑只有查表与乘法，复杂度很低。
- 测试只检查输出文件、材料编号和数值精度，不依赖随机性。
- 输入数据固定，输出 deterministic。

## 本示例中的 Oracle 入口

- `examples/mesh_analysis_pricing_task/solution/solve.py`

运行方式：

```bash
python examples/mesh_analysis_pricing_task/solution/solve.py
```
