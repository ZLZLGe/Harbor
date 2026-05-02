你需要为内部产品团队完成下一次两周 Sprint 的最终承诺规划，并向发布经理提交可执行的排期结果。

输入数据位于 `/root/data/`：

- `planning_manifest.json`：Sprint 编号、计划窗口和本地 planning service 入口。
- `backlog_export.csv`：较早导出的候选 backlog 清单，可能过期或不完整。
- `team_capacity.csv`：本次 Sprint 的容量信息。
- `delivery_policy.yaml`：本次 Sprint 的交付策略与选择约束。
- `planning_notes/`：从公开 backlog 归一化整理出的需求摘要、里程碑背景和补充上下文。

## 你的任务

1. 审查所有候选 backlog item，并生成一份完整的候选分诊结果。
2. 使用当前容器内 planning service 作为事实源，确定哪些 item 可以进入本次 Sprint 承诺范围。
3. 生成一份可执行的 Sprint 计划，说明已承诺项、未承诺项及原因、容量占用和主要风险。
4. 为发布经理写一份简短摘要，说明本次 Sprint 的承诺范围和关键阻塞。

## 业务约束

1. 所有候选 item 都必须出现在分诊结果里，不能遗漏。
2. `backlog_export.csv` 不是最终事实源。容器内 planning service 才是 backlog 状态和相关规划信息的权威来源。
3. 已完成、已取消或已归档的 item 不能进入 Sprint 承诺。
4. 只有满足当前交付策略和容量约束的 item 才能被承诺。
5. `must_ship = true` 的 item 在满足承诺条件时必须优先考虑。
6. 如果 item 未进入 Sprint，必须给出唯一的未承诺原因。

## 输出

如 `/root/output/` 不存在，请先创建该目录。

写入 `/root/output/backlog_triage.csv`，列名必须严格如下：

```csv
item_id,title,priority,story_points,owner_role,milestone_date,ready,blocked,must_ship,qa_required,selected,rejection_reason
```

要求：

- 必须包含所有候选 item，且每个 `item_id` 只能出现一次。
- `milestone_date` 使用 `YYYY-MM-DD` 格式。
- `ready`、`blocked`、`must_ship`、`qa_required`、`selected` 必须使用 `true` 或 `false`。
- `rejection_reason` 必须为空字符串或以下值之一：
  - `already_closed`
  - `not_ready`
  - `blocked_dependency`
  - `insufficient_story_points`
  - `insufficient_qa_capacity`
  - `insufficient_review_capacity`
  - `below_cutline`

写入 `/root/output/sprint_plan.json`，结构如下：

```json
{
  "sprint_id": "SPR-000",
  "committed_item_ids": ["ITEM-1"],
  "committed_items": [
    {
      "item_id": "ITEM-1",
      "title": "Example",
      "priority": "P1",
      "story_points": 3,
      "owner_role": "Backend Engineer",
      "depends_on": ["ITEM-0"],
      "why_selected": "Required for milestone and fits current sprint capacity."
    }
  ],
  "deferred_items": [
    {
      "item_id": "ITEM-9",
      "rejection_reason": "below_cutline",
      "explanation": "Lower priority than remaining committed work."
    }
  ],
  "capacity_summary": {
    "story_points_available": 0,
    "buffer_points_reserved": 0,
    "story_points_committed": 0,
    "qa_slots_available": 0,
    "qa_slots_used": 0,
    "review_slots_available": 0,
    "review_slots_used": 0
  },
  "risk_flags": [
    "Example risk"
  ],
  "notes": [
    "Example note"
  ]
}
```

要求：

- `committed_item_ids` 必须与 `committed_items` 中的 `item_id` 集合完全一致，且顺序一致。
- `deferred_items` 必须覆盖所有 `selected = false` 且不是 `already_closed` 的 item。
- `depends_on` 必须列出该 item 的 hard dependency item ID；如无则写空数组。
- `story_points_committed` 不能超过 policy 允许的 Sprint 承诺上限。
- `qa_slots_used` 和 `review_slots_used` 不能超过对应可用容量。
- `risk_flags` 至少包含最重要的交付风险和容量风险。

写入 `/root/output/manager_update.md`，内容必须包含：

- Sprint 编号；
- 承诺 item 总数；
- 承诺 item ID 列表；
- 总承诺 story points；
- 未进入 Sprint 的高优先级 item；
- 主要容量瓶颈；
- 最重要的交付风险；
- 对本次取舍逻辑的简短说明。

## 说明

- 不要修改 `/root/data/` 下的文件。
- 不要把 `backlog_export.csv` 当作唯一依据，也不要绕过当前容器内 planning service。
- 不要用硬编码结果、缓存答案或手工伪造输出来替代真实规划链路。
- 明确禁止替换真实链路、删除功能规避问题，或通过减少交付内容来规避约束。
- 不要修改 verifier 文件、task metadata 或 environment 文件。
- 你可以在工作目录中编写辅助脚本，但最终只需要提交 `/root/output/` 下要求的 3 个文件。
