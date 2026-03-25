你要处理一条 4 段涂布线。环境里已经给出两个离散状态空间模型、参考切换调度和一个轻量仿真器；你需要在不修改输入资产的前提下，实现滚动控制并生成 `/root/coating_response_report.json`。

可用输入资产：

- `/root/coating_line_case.json`：任务配置，包含 `dt`、`duration`、`switch_time`、`speed_ramp_duration`、初始状态、两段运行模型与参考输入。
- `/root/coating_line_simulator.py`：轻量仿真器，提供参考轨迹、分段模型和闭环步进接口。

控制目标：

- `t < 1.5s` 时运行在 `pre_ramp` 工况。
- 从 `t = 1.5s` 开始，线速度参考在 `0.8s` 内从慢线平滑提升到快线水平。
- 从 `t = 1.5s` 开始，中间两段张力参考直接切换到新目标。
- 仿真总时长至少覆盖 `6.0s`。

输出文件必须是 `/root/coating_response_report.json`，格式如下：

```json
{
  "scenario": {
    "dt": 0.05,
    "duration": 6.0,
    "switch_time": 1.5
  },
  "phase_gain_summary": [
    {
      "phase": "pre_ramp",
      "horizon": 16,
      "sampled_stage_gains": [
        {"stage": 0, "fro_norm": 7.9},
        {"stage": 8, "fro_norm": 7.6},
        {"stage": 15, "fro_norm": 7.0}
      ]
    },
    {
      "phase": "post_ramp",
      "horizon": 16,
      "sampled_stage_gains": [
        {"stage": 0, "fro_norm": 7.8},
        {"stage": 8, "fro_norm": 7.6},
        {"stage": 15, "fro_norm": 6.9}
      ]
    }
  ],
  "trajectory": [
    {
      "time": 0.0,
      "phase": "pre_ramp",
      "tensions": [17.8, 20.5, 21.1, 18.4],
      "speeds": [1.08, 1.03, 1.07, 1.01],
      "reference_tensions": [18.0, 21.0, 20.0, 17.0],
      "reference_speeds": [1.2, 1.18, 1.15, 1.12],
      "control_inputs": [0.41, 0.36, 0.22, 0.18]
    }
  ],
  "metrics": {
    "steady_state_tension_error": 0.18,
    "steady_state_speed_error": 0.056,
    "middle_zone_tension_overshoot": 0.22,
    "line_speed_overshoot": 0.10,
    "control_energy": 5.63
  }
}
```

明确要求：

- `scenario` 中必须包含 `dt`、`duration`、`switch_time`，并与输入配置一致。
- `phase_gain_summary` 必须正好包含两个阶段：`pre_ramp` 与 `post_ramp`。
- 每个阶段都要给出整数 `horizon`，范围为 `[6, 24]`。
- 每个阶段的 `sampled_stage_gains` 至少包含 3 个采样点，且必须覆盖 `stage = 0` 和 `stage = horizon - 1`；`fro_norm` 为该阶段反馈增益矩阵的 Frobenius 范数。
- `trajectory` 中每个元素都必须包含 `time`、`phase`、`tensions`、`speeds`、`reference_tensions`、`reference_speeds`、`control_inputs`。
- `tensions`、`reference_tensions` 长度都为 4；`speeds`、`reference_speeds` 长度都为 4；`control_inputs` 长度为 4。
- `trajectory` 必须覆盖至少 `6.0s`，时间严格递增，并且 `phase` 只能是 `pre_ramp` 或 `post_ramp`。
- `trajectory` 里的 `control_inputs` 必须是实际施加到给定仿真器的闭环控制量；验证时会把这些输入逐步回放到 `/root/coating_line_simulator.py`，检查是否能重现你报告中的状态轨迹。
- `phase_gain_summary` 中 `stage = 0` 的 `fro_norm` 必须对应该阶段实际闭环所用首个反馈增益的 Frobenius 范数，不能只给任意正数摘要。

指标定义：

- `steady_state_tension_error`：最后 `1.0s` 内，4 个张力状态相对参考的平均绝对误差。
- `steady_state_speed_error`：最后 `1.0s` 内，4 个速度状态相对参考的平均绝对误差。
- `middle_zone_tension_overshoot`：`t >= 1.5s` 后，第 2、3 段张力相对各自参考的最大正超调。
- `line_speed_overshoot`：`t >= 1.5s` 后，4 个速度相对各自参考的最大正超调。
- `control_energy`：全程 `sum(dt * ||u_k||_2^2)`。

需要满足的公开性能门槛：

- `steady_state_tension_error < 0.22`
- `steady_state_speed_error < 0.07`
- `middle_zone_tension_overshoot < 0.35`
- `line_speed_overshoot < 0.15`
- `control_energy < 6.5`

可以自由组织求解脚本，但最终只会检查 `/root/coating_response_report.json` 是否满足以上约定。
