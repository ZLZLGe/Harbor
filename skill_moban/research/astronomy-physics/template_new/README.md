# Astronomy Physics Template

这是面向 `astronomy-physics` 类 skill 的模板。它综合参考 SkillsMP 该类热门 skill 的共性能力：科学数据处理、坐标/空间参照转换、单位与时间系统、真实观测或环境数据链路、数值计算、外部/本地服务集成，以及可复核的分析报告生成。

## 第一部分：任务设计参考

* **Skill 价值定位**：这类 Skill 的价值应体现在把领域知识转化为稳定、可复用的科学分析流程。任务设计应让 Skill 帮助 Agent 正确处理坐标系、单位、时间、物理量、数据格式和领域诊断工具，而不是提供静态答案。好的 Skill 还应降低排查成本，使 Agent 能快速定位数据解释、阈值判断和结果一致性问题。
* **Task 目标形态**：任务应要求 Agent 面对真实风格的科学数据和上下游链路，产出可运行、可复核、可追溯的结果包。输入可以是 FITS、表格、模拟结果、时空数据、观测记录或本地服务响应，输出应包含正式分析结果和必要审计信息。任务不应退化为 puzzle、单纯格式转换、隐藏答案匹配或只修一个表层报错。
* **Verifier 设计重点**：Verifier 应重算关键行为结果，并检查物理/空间/时间一致性，而不是绑定某个唯一代码实现。它应覆盖输入全量性、单位和坐标正确性、阈值边界、数值误差、服务链路和报告一致性。防作弊测试应拦截静态占位输出、跳过真实链路、删行规避、硬编码摘要和只满足表面格式的解法。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`astronomy_physics__fits-transient-triage`
- 类别：`astronomy-physics`
- 难度：`hard`
- 绑定 Skill：`astropy`

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：官方解法重写正式 triage 入口，从公开 FITS、检测表、星表、校准表和本地 field context 服务生成全部交付物。Oracle 在 E2B 上通过 `7/7` 测试，Reward 为 `1.0`。

| Verifier 测试内容 | 对应 skill 要求掌握的部分 |
| :--- | :--- |
| 输出文件、列合同和输入 detection 全量覆盖 | `astropy.table.Table`、ECSV/TSV/JSON 结果组织 |
| FITS WCS 坐标、银道坐标、UTC 曝光中点和 MJD | FITS HDU、WCS、`SkyCoord`、`Time` |
| Gaia、宿主星系、移动天体交叉匹配与分类 | 球面角距离、角秒阈值、分类优先级 |
| AB 星等、误差传播、红移距离和绝对星等 | 单位、测光公式、`Planck18` 宇宙学 |
| `triage_diagnostics.tsv` 诊断 ledger | WCS round-trip、阈值 margin、task-bound signature kernel |
| `report.json` 与 `field_context.json` 一致性 | 本地下游服务调用、报告汇总和候选体集合对齐 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，Skill 的核心价值是把 FITS/WCS、`SkyCoord`、`Time`、测光、`Planck18` 和 task-bound diagnostics signature kernel 标准化，从而显著降低诊断与收敛成本；without Skill 仍能手写可见科学链路，但无法稳定复现 Skill 侧诊断内核约定。

基于最近 **5** 次有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` (`0/5`) | `100%` (`5/5`) | Without Skill 能重建部分科学结果，但无法复现 task-bound diagnostics kernel，无法稳定通过诊断 ledger |
| Agent 执行耗时 | `337.7s` | `303.3s` | With Skill 的诊断与收敛更快，平均 Agent 耗时降低约 `10%` |
| Tokens | `588,755` | `551,304` | Without Skill 的上下文与试错开销约为 With Skill 的 `1.07x` |

## 📁 标准目录结构说明

```text
template_new/
├── instruction.md
├── task.toml
├── PLAN.json
├── README.md
├── environment/
├── tests/
└── solution/
```
