你在处理一个 PCB 组装车间的基线修复任务。SMT 贴片、回流焊和后段检测共 3 道工序，每个 lot 的每道工序都可以在不同产线上完成，但校准停机窗口、冻结约束和改线预算会让原始基线失效。请基于 `/app/data/` 下的输入资产，输出修复后的产线计划到 `/app/output/pcb_repair_plan.json`。

可用输入文件：

- `/app/data/board_routes.txt`：lot 与 stage 的可选产线及对应加工时长，格式与标准 FJSP 文本编码一致。
- `/app/data/calibration_windows.csv`：各产线不可用的校准停机窗口。
- `/app/data/repair_policy.json`：冻结窗口、改线预算、总开工偏移预算以及完工上限。
- `/app/data/baseline_plan.json`：当前基线计划，字段语义与目标输出一致。
- `/app/data/baseline_snapshot.json`：基线的冲突摘要，便于对照修复前后的改进幅度。

必须满足：

- 每个 `(lot, stage)` 都要且只要出现一次。
- `finish = start + duration`，并且 `duration` 必须匹配该 `lot/stage/line` 在 `board_routes.txt` 中定义的加工时长。
- 同一 `lot` 的 stage 必须按顺序执行。
- 同一 `line` 上的作业不能重叠。
- 任意作业都不能与 `calibration_windows.csv` 中对应产线的停机窗口重叠。
- 对基线只能右移，不能提前开工。
- 冻结窗口内被锁定的字段不能改动。
- 改线次数与总开工偏移必须不超过 policy 预算。

输出 JSON 必须使用下面的结构：

```json
{
  "status": "REPAIRED",
  "completion_time": 0,
  "change_budget_usage": {
    "line_changes": 0,
    "total_start_shift": 0
  },
  "line_plan": [
    {
      "lot": 0,
      "stage": 0,
      "line": 0,
      "start": 0,
      "finish": 0,
      "duration": 0
    }
  ]
}
```

其中 `completion_time` 是所有作业的最大 `finish`。`change_budget_usage` 需要与实际排程一致。
