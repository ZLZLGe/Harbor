你需要审查一个市政资本项目组合，并为延期、超预算或受采购阻塞影响的项目制定一份 6 周 PMO 恢复计划。

输入数据位于 `/root/data/`：

- `capital_projects.csv`：项目组合记录，包括机构、项目名称、行政区、类别、当前阶段、基准日期、预测日期、批准预算、当前估算成本和完成百分比。
- `project_dependencies.csv`：规划、采购、施工、验收和收尾活动之间的依赖关系与阶段门规则。
- `team_capacity.csv`：按周、工作流和负责人角色列出的 PMO 可用产能。
- `action_catalog.csv`：允许使用的恢复动作、适用项目阶段、预计持续时间、所需工时和目标看板状态。
- `risk_flags.csv`：高优先级标记、已知阻塞项、公共影响标记和必需升级负责人。
- `cpi.csv`：用于标准化预算和成本暴露的月度 CPI 数据。

## 你的任务

1. 读取所有输入文件，并为每个项目创建项目组合分诊表。

2. 使用 CPI 数据，将每个项目的当前估算成本标准化为 2025 年 1 月美元口径。

3. 计算进度和成本风险：
   - `schedule_variance_days` = 预测完成日期 - 基准完成日期。
   - `cost_variance_pct` = 标准化后的当前估算成本 / 批准预算 - 1。
   - 如果 `schedule_variance_days > 30`，项目为 `late`。
   - 如果 `cost_variance_pct > 0.10`，项目为 `over_budget`。
   - 如果 `risk_flags.csv` 标记了未解决阻塞项，项目为 `blocked`。
   - 如果项目有高优先级标记或公共影响标记，项目为 `high_priority`。

4. 选择进入 6 周恢复计划的项目：
   - 包含所有 `blocked` 项目。
   - 包含所有 late 或 over_budget 的 `high_priority` 项目。
   - 包含所有同时满足 `schedule_variance_days > 60` 且 `cost_variance_pct > 0.15` 的其他项目。
   - 不要包含已完成或已取消项目。

5. 从 `team_capacity.csv` 中指定的最早周一开始，制定 6 周恢复计划。
   - 只能使用 `action_catalog.csv` 中列出的动作。
   - 只能使用适用于项目当前阶段的动作。
   - 必须遵守 `project_dependencies.csv` 中的阶段门和动作类型规则。
   - 不得超过任何工作流或负责人角色的周产能。
   - 如果项目存在未解决阻塞项，该项目的第一个动作必须是清除阻塞或升级处理动作。
   - 如果多个项目竞争同一产能，按以下顺序排序：
     1. 存在阻塞的项目
     2. 有公共影响的高优先级项目
     3. 进度偏差更大的项目
     4. 标准化成本暴露更大的项目
     5. 基准完成日期更早的项目
     6. 项目 ID，作为稳定的最终排序规则

6. 为选入恢复计划的项目准备项目看板更新数据。
   - 每个选入项目必须且只能有一条看板更新。
   - 看板状态必须与该项目最重要的计划动作匹配。
   - 评论应简要说明恢复动作和主要剩余风险。

## 输出格式

如 `/root/output/` 不存在，请先创建该目录。

写入 `/root/output/portfolio_triage.csv`，列名必须严格如下：

```csv
project_id,agency,project_name,borough,category,current_phase,baseline_finish,forecast_finish,approved_budget,current_estimate,normalized_current_estimate,schedule_variance_days,cost_variance_pct,late,over_budget,blocked,high_priority,triage_status
```

要求：

- 必须包含 `capital_projects.csv` 中的每一个项目。
- 日期使用 `YYYY-MM-DD` 格式。
- `normalized_current_estimate` 必须为数值，并保留 2 位小数。
- `cost_variance_pct` 必须为数值，并保留 4 位小数。
- 布尔列必须使用 `true` 或 `false`。
- `triage_status` 必须是 `monitor`、`recover`、`escalate`、`complete` 或 `exclude` 之一。

写入 `/root/output/recovery_plan.csv`，列名必须严格如下：

```csv
project_id,week_start,workstream,owner_role,action_id,action_name,planned_start,planned_finish,effort_hours,target_status,dependency_note,risk_note
```

要求：

- 只包含进入恢复计划的项目。
- 每个进入恢复计划的项目至少要有一个计划动作。
- 所有日期使用 `YYYY-MM-DD` 格式。
- `planned_start` 和 `planned_finish` 必须位于 6 周计划窗口内。
- 每周工时不得超过 `team_capacity.csv` 中的可用产能。
- `target_status` 必须是 `Blocked`、`Escalated`、`Recovery Planned`、`In Progress`、`Ready for Review` 或 `On Track` 之一。

写入 `/root/output/board_updates.json`，结构如下：

```json
{
  "updates": [
    {
      "project_id": "P-0001",
      "target_status": "Recovery Planned",
      "owner_role": "Procurement Lead",
      "week_start": "2025-07-07",
      "comment": "Expedite procurement package and resolve vendor blocker before construction restart."
    }
  ]
}
```

要求：

- `updates` 必须为 `recovery_plan.csv` 中每个项目各包含一条记录。
- `project_id`、`target_status`、`owner_role` 和 `week_start` 必须能与恢复计划对应。
- `comment` 必须是一个简洁句子，说明计划恢复动作和剩余风险。

写入 `/root/output/executive_summary.md`，内容必须包含：

- 审查的项目总数。
- 进入恢复计划的项目数量。
- 被标记为 blocked、late 和 over_budget 的项目数量。
- 风险最高的前五个恢复项目。
- 主要产能瓶颈工作流。
- 对优先级排序方法的简短说明。
- 一个紧凑的 PMO 项目计划附录。若 `project-planner` skill 可用，该附录必须遵循该 skill 的标准项目计划输出格式；若不可用，也应自行按专业项目计划格式补全目标、阶段、里程碑、依赖、风险缓解和资源分配信息。

## 说明

- 不要修改 `/root/data/` 下的文件。
- 不要从分诊输出中遗漏项目。
- 不要创建 `action_catalog.csv` 中不存在的动作。
- 不要忽略依赖规则或每周产能限制。
- 不要硬编码 verifier 的答案。
- 不要用纯文字报告替代要求的结构化输出。
- 不要在 `/root/output/` 之外创建额外输出文件。

## 数据文件参考来源

[1] [NYC Capital Projects Dashboard](https://www.nyc.gov/site/operations/other-resources/capital-projects-dashboard.page)
[2] [NYC Open Data](https://opendata.cityofnewyork.us/)
[3] [Consumer Price Index for All Urban Consumers: All Items in U.S. City Average, CPIAUCSL](https://fred.stlouisfed.org/series/CPIAUCSL)
