## 第一部分：任务设计参考

* **Skill 价值定位**：技能收益必须体现在项目管理方法论的稳定应用上，例如目标定义、工作分解、阶段计划、依赖映射、资源分配、风险缓解和里程碑组织；严禁把收益建立在隐藏答案、改测试、改数据、替换真实链路、硬编码 verifier 或让 skill 直接暴露标准答案上。
* **任务目标形态**：任务应要求 Agent 从真实风格的业务数据中产出可执行的 PMO / 项目计划交付物，例如项目组合分诊、恢复计划、看板更新、资源配置和 executive summary；不应设计成单纯修 app、调用 localhost API、猜 puzzle、复述模板文本或只写一份不可验证的叙述报告。
* **验证设计重点**：Verifier 应从输入数据动态重算关键指标，并验证结果行为是否满足业务约束，例如阶段门、依赖、容量、优先级、输出 schema、项目计划结构和防作弊 guardrails；不应绑定唯一实现路径，也不应依赖隐藏 golden answer 文件。

## 第二部分：示例任务

### 📌 任务元数据

- 任务：Municipal Capital Project Recovery Plan
- 类别：Project Management
- 绑定 Skill：`project-planner`
- Skill stars：约 `106.7k`
- 数据主题：市政资本项目组合分诊、CPI 成本标准化、6 周 PMO 恢复计划、产能约束、看板更新与项目计划附录

### 📊 验证与测试指标（Oracle & Verifier）

- e2b oracle 结果：✅ 通过（Reward: `1.0`）
- Oracle Job：`pm-recovery-oracle-e2b-20260423-007`
- 测试用例：`8/8` 通过

Verifier 策略：

- 主测：重算 CPI 标准化成本、进度偏差、成本偏差、风险标记、恢复项目选择、动作合法性、阶段门规则、6 周窗口、周产能限制、看板更新一致性、executive summary 关键指标，以及 `project-planner` 标准项目计划附录结构。
- 防作弊：校验输入 CSV hash；只允许四个指定输出文件；不使用隐藏标准答案文件；从输入数据动态推导 expected behavior；阻止修改输入、硬编码答案或跳过恢复项目。

数据来源：

- [NYC Capital Projects Dashboard](https://www.nyc.gov/site/operations/other-resources/capital-projects-dashboard.page)
- [NYC Open Data](https://opendata.cityofnewyork.us/)
- [Consumer Price Index for All Urban Consumers: CPIAUCSL](https://fred.stlouisfed.org/series/CPIAUCSL)

多模态：

- 不适用（纯数据处理 / 项目管理计划任务）。

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，Skill 的核心价值是把恢复计划组织成标准项目计划结构：目标、时间线、团队、约束、里程碑、阶段计划、依赖图、风险缓解和资源分配。Without Skill 的 agent 能完成多数数据计算和排程，但稳定遗漏 `project-planner` 标准附录格式，因此被 verifier 拦下。

基于最近 `3` 次有效 with/without 对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；没有计入启动失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `100%` | With Skill `3/3` 全通过；Without Skill `0/3`，均在项目计划附录格式上失败 |
| 平均总耗时 | `387.8s` | `429.8s` | With Skill 多完成了标准 planning appendix，耗时更高但质量达标 |
| 平均 Agent 执行耗时 | `332.4s` | `378.1s` | With Skill 的输出更完整，未靠省略计划结构缩短执行 |
| 平均 Input Tokens | `219.1k` | `353.7k` | With Skill 使用更多上下文读取和应用 skill 格式 |
| 主要失败点 | 缺少 `## Project:` 等 project-planner 标准附录标记 | 无 | Without Skill 的结构化 PMO 附录不稳定 |

对照实验：

- With Skill Job：`pm-recovery-with-skills-e2b-20260423-006`
- Without Skill Job：`pm-recovery-without-skills-e2b-20260423-003`
- 唯一区别：with runtime 保留 `environment/skills/36__project-planner/`；without runtime 删除 `environment/skills/`。`diff -qr` 仅显示 `Only in .../task_with_skills_e2b/environment: skills`。

### 📁 标准目录结构说明

```text
template_new/
├── instruction.md
├── task.toml
├── PLAN.json
├── environment/
│   ├── Dockerfile
│   ├── data/
│   └── skills/
├── tests/
└── solution/
```
