# Project-Management Template

这是面向 `project-management` 类 skill 的模板。它综合参考 SkillsMP project-management 类热门 skill 的共性能力：项目拆解、里程碑规划、依赖管理、资源与产能分配、风险缓解、状态追踪、看板更新和管理层汇报。

## 第一部分：任务设计参考

* **Skill 价值定位**：project-management 类 skill 的核心价值，是把模糊业务目标转化为可执行的项目计划，并稳定组织任务、时间线、依赖、负责人、风险和交付状态。模板任务应让 skill 在计划结构、优先级排序、约束处理和沟通输出上降低遗漏率，而不是暴露隐藏答案或替代业务计算。
* **Task目标形态**：任务应要求 Agent 基于真实风格的项目组合、看板、资源或风险数据，产出可执行、可追踪、可验证的 PMO 交付物。目标形态适合设计成项目分诊、恢复计划、Sprint/Kanban 更新、资源排期、风险升级和 executive summary，不适合做纯叙述计划、静态模板填空或不可复算的主观建议。
* **Verifier设计重点**：Verifier 应从输入数据动态重算选择、排序、容量、依赖、状态和关键指标，并验证输出是否满足项目管理约束。重点应覆盖输入不可变、输出 schema、阶段门规则、工作流/角色产能、阻塞项首动作、每项目看板更新、管理层摘要指标和标准项目计划附录结构。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`municipal-capital-recovery-plan`
- 类别：`project-management`
- 难度：`medium`
- 绑定 Skill：`project-planner`

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：Oracle 使用同一批市政资本项目、CPI、依赖规则、风险标记、动作目录和团队产能数据，独立推导项目分诊、6 周恢复计划、看板更新和 summary 关键指标。它关注恢复计划是否满足业务约束，而不是实现路径是否一致。

- Verifier策略：

| Verifier 测试内容 | 对应 skill 要求掌握的部分 |
| :--- | :--- |
| 输出文件集合、CSV/JSON/Markdown schema 和输入 hash | 结构化 PMO 交付物与防作弊约束 |
| CPI 标准化成本、进度偏差、成本偏差、blocked/high_priority 标记 | 项目组合分诊与风险识别 |
| 恢复项目选择、优先级排序和 triage_status | 组合治理、优先级和升级规则 |
| action_catalog 成员、阶段门、阻塞项首动作和 6 周窗口 | 依赖管理、阶段计划和恢复动作设计 |
| 每周 workstream/owner_role 产能限制 | 资源分配与容量规划 |
| board_updates 与 recovery_plan 对齐 | 看板状态追踪和项目沟通 |
| executive_summary 指标与 project-planner 附录标记 | 管理层汇报、里程碑、依赖、风险缓解和资源计划 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，Skill 的核心价值是把恢复计划组织成标准项目计划结构：目标、时间线、团队、约束、里程碑、阶段计划、依赖图、风险缓解和资源分配。Without Skill 的 agent 能完成多数数据计算和排程，但稳定遗漏 `project-planner` 标准附录格式，因此被 verifier 拦下。

基于最近 **3** 次有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `100%` | 近 3 次有效对照里，without Skill 均缺少 `project-planner` 标准附录标记；with Skill 三次全通过。 |
| Agent 执行耗时 | `332.4s` | `378.1s` | With Skill 多完成了标准 planning appendix，耗时略高但输出质量达标。 |
| Tokens | `219.1k` | `353.7k` | With Skill 使用更多上下文读取和应用计划格式，换来更稳定的结构化 PMO 输出。 |

## 📁 标准目录结构说明

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
├── solution/
└── readme.md
```
