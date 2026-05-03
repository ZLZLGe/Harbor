# Data Engineering Template

这是面向 Data Engineering 类 skill 的模板。它综合参考 SkillsMP Data Engineering 类热门 skill 的共性能力：面向真实数据链路的装载、去重、时间语义、聚合建模、质量校验和可复现实验，而不是单点修 bug 或静态问答。

## 第一部分：任务设计参考

* **Skill 价值定位**：Data Engineering skill 的核心价值是把数据库、批流处理、数据质量和管道工程中的隐性经验显式化。它应该帮助 agent 更快识别事件时间、幂等去重、时区、窗口聚合、数据契约和运行入口之间的约束关系。
* **Task 目标形态**：任务应呈现为一个可运行的数据产品或分析管道交付，而不是谜题式答案。输入数据应有真实业务结构、上下游装载链路和多源事实表，输出应包含明细、汇总和质量摘要。
* **Verifier 设计重点**：Verifier 需要同时验证主业务结果、边界数据、格式合同和防作弊约束。重点覆盖去重稳定性、时区/事件时间、窗口 sessionization、最终状态过滤、区间裁剪、输出 schema、输入不可篡改和核心引擎使用痕迹。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：clickhouse-delivery-wave-query
- 类别：Data Engineering
- 难度：`hard`
- 绑定 Skill：clickhouse-io

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：官方解法使用 ClickHouse 完成原始数据装载、scan/order/inventory 去重、事件时间 wave sessionization、SLA 与 stockout 区间聚合，并导出四个指定结果文件。
- Verifier 策略：

| Verifier 测试内容 | 对应 skill 要求掌握的部分 |
| :--- | :--- |
| 主数据集逐字段比对 `wave_metrics`、`longest_wave_per_route`、`order_package_audit` 和质量摘要 | ClickHouse 表设计、窗口函数、聚合、CSV/JSONL 装载 |
| 多组临时数据目录复跑，覆盖订单 tie-break、DST/本地业务日、重复 scan、stockout 区间 | 事件时间建模、时区处理、幂等去重、数据质量边界 |
| SQL/runner 源码 guardrail，禁止静态答案、Python/pandas/duckdb 绕过、字符串式时区转换 | 保持真实 ClickHouse 链路和 typed 时间函数 |
| 检查绑定 scaffold/provenance 与环境 skill 路径 | Skill 诊断脚手架使用、with/without 对照隔离 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务中，Skill 的核心价值是把 ClickHouse 表结构、窗口函数、事件时间去重、typed `toTimeZone` 分派和可审计 scaffold 路径标准化；without Skill 即使能写出部分 SQL，也更容易在边界数据、输出合同或 provenance guardrail 上失败。

基于最近 **3** 次有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `66.7%` | 近 3 次有效对照里，without Skill 没有完全通过；with Skill 主要借助 scaffold 和 ClickHouse 经验更快收敛，失败样本集中在 stockout 开区间摘要口径。 |
| Agent 执行耗时 | `547.2s` | `264.3s` | With Skill 的诊断与收敛更快，平均 Agent 耗时降低约 `51.7%` |
| Tokens | `0.91M` | `0.47M` | Without Skill 的上下文与试错开销约为 With Skill 的 `1.94x` |

## 📁 标准目录结构说明

```text
模板任务：
├── instruction.md
├── task.toml
├── PLAN.json
├── environment/
│   ├── Dockerfile
│   ├── workspace/
│   └── skills/
├── tests/
│   ├── test.sh
│   └── test_outputs.py
└── solution/
    └── solve.sh
```
