# `mesh-analysis` 重构任务示例：`noisy-part-volume-pricing`

## 任务目标

这个示例任务展示如何把 `mesh-analysis` skill 重构成一个适合训练的 task。

核心结构是：

`网格分析能力 + 薄业务逻辑（查单价表） + 固定 JSON 输出`

## 为什么这个任务适合 skill 内化

- 主难点是二进制 STL 解析、主连通体识别和体积计算
- 这些难点正好由 `mesh-analysis` 覆盖
- 业务层只有一步查表乘法，不会淹没 skill 价值
- 结果可以 deterministic 验证

## 任务分层

### 场景层

工程团队收到一份带扫描噪声的 3D 网格，希望快速估算主零件材料成本。

### 输入层

- `environment/scan_input.stl`
- `environment/material_price_table.md`

### 能力层

- 解析 Binary STL
- 读取每个三角面的属性字节
- 做连通分量分离
- 找出最大主体
- 计算主体体积

### 业务层

- 将主零件的 `material_id` 映射到价格表中的单位成本
- 计算 `estimated_cost = volume * unit_price`

### 输出层

- `output/pricing_report.json`

## 与 benchmark 原题的关系

这个任务和 `skillsbench` 中的 `3d-scan-calc` 共用相同核心能力，但业务壳不同：

- 原题：查密度表，计算质量
- 本示例：查价格表，计算成本

这样能减少对 benchmark 原题表面的过拟合，更适合做训练样本。
