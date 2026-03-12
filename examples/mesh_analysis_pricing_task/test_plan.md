# 测试计划

## 测试目标

验证 Oracle 输出是否满足：

- 文件存在
- JSON 结构正确
- `material_id` 正确
- `main_part_estimated_cost` 在 `0.1%` 容差内正确

## Ground Truth 原则

测试不得直接导入或调用 skill。

测试需要独立实现以下逻辑：

- 二进制 STL 解析
- 连通分量分离
- 最大主体识别
- 体积计算
- 价格表解析

## 覆盖范围

### 测试 1：输出文件存在

检查 `output/pricing_report.json` 是否生成。

### 测试 2：输出结构正确

检查是否包含：

- `main_part_estimated_cost`
- `material_id`

### 测试 3：输出值正确

独立计算 ground truth，并与 Oracle 输出做比对。

## 对照实验建议

后续如果要做 no-skill 对照，保持以下内容不变：

- `instruction.md`
- 输入文件
- tests

只移除 skill 暴露方式即可。
