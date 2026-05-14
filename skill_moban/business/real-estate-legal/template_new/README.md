# Real-Estate-Legal Template

这是面向 `real-estate-legal` 类模板任务的示例。它综合参考 SkillsMP 中与融资材料、市场梳理、文档一致性和结构化交付相关的高星 skill 共性能力：先收拢当前业务口径，再把 memo、one-pager、财务模型和资金分配表对齐到同一组公开来源与当前公司输入。

## 第一部分：任务设计参考

* **Skill 价值定位**：这类 skill 的核心价值，是在多份对外材料同时存在时，帮助 Agent 先整理当前口径，再把数字、条款、市场范围和里程碑写到多份交付中，并持续对数。模板任务应让 skill 在口径统一、旧稿排查、模型滚动和多文件一致性上形成稳定优势。
* **Verifier 设计重点**：Verifier 应重算结构化事实、季度模型和资金分配，同时检查文档是否带入旧稿里的过期值。重点应放在当前口径是否被正确采用、公开市场快照是否被正确使用、以及多份交付是否前后一致，而不是把压力堆到版式细节。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`real-estate-legal__noticeflow-seed-materials`
- 类别：`real-estate-legal`
- 绑定 Skill：`investor-materials`
- 输入数据参考来源：
  - `environment/data/market_snapshots/metro_housing_snapshot.csv`：任务内 Atlanta、Dallas、Phoenix 住房市场快照；数据取自 Census Reporter ACS API，对应表 `B25003`、`B25071`、`B25064`、`B19013`  
    https://api.censusreporter.org/1.0/data/show/latest?table_ids=B25003,B25071,B25064,B19013&geo_ids=31000US12060,31000US19100,31000US38060

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：按正式流程独立运行并完成交付，结果可直接 100% 通过验证。
- Verifier 策略：

主测试

| 测试点 | 验证内容 | 对应 skill 内化点 |
| :--- | :--- | :--- |
| 输出契约 | 检查 6 个交付文件是否齐全、可解析、字段完整 | 多材料交付完整性 |
| 当前口径重算 | 重算融资条款、定价、经营指标、市场快照和里程碑 | 当前事实集整理 |
| 财务模型重算 | 重算 8 个季度的客户滚动、收入、净消耗和现金滚动 | 财务模型与算数闭环 |
| 资金分配校验 | 校验金额总和、比例总和和分类顺序 | 融资金额分配一致性 |
| 冲突与张力校验 | 校验旧稿冲突覆盖完整，并校验当前里程碑与 base-case 模型张力是否被记录 | 旧稿排查与输入张力识别 |
| 文档一致性 | 校验 memo 和 one-pager 中的关键数字与结构化事实一致 | 多份材料对数 |

防作弊测试

| 测试点 | 验证内容 |
| :--- | :--- |
| 输入不可变 | 校验 `/root/data` 原始输入 hash 不变 |
| 旧稿污染 | 检查输出中未带入旧稿里的过期融资金额、工具类型、定价和市场范围 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，skill 的核心价值在于帮助 Agent 先整理当前融资口径，再把旧稿冲突和当前输入张力显式记录出来，随后生成 memo、one-pager、模型和资金分配表，并把数字逐项对齐；without skill 更容易漏掉冲突清单或漏掉当前计划里的关键张力。

基于最近 **3** 次有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败类 trial；统计按当前 verifier 语义复核，`reconciliation_log.csv` 仅放宽等价值写法与行顺序）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0/3 (0%)` | `3/3 (100%)` | 近 3 次有效对照里，without Skill 更容易把旧稿冲突清单写残或把里程碑张力里的当前值与冲突值写反，因此始终保留至少 1 项 verifier 失败。 |
| Agent 执行耗时 | `344.0s` | `300.0s` | With Skill 的口径收拢与对数更快，平均 Agent 耗时降低约 `12.8%`。 |
| Tokens | `376.3k` | `312.5k` | Without Skill 的上下文与试错开销约为 With Skill 的 `1.20x`。 |

## 📁 标准目录结构说明

```text
template_new/
├── instruction.md
├── task.toml
├── PLAN.json
├── README.md
├── environment/
│   ├── Dockerfile
│   ├── data/
│   └── skills/
├── tests/
└── solution/
```
