你接手的是一条 4 段卷对卷涂布线的张力控制改造任务。环境已经给出：

- `coating_line_env.py`：4 段涂布线仿真器与工况配置读取逻辑。
- `controller_scaffold.py`：名义预测控制脚手架，以及运行单个工况和汇总指标的辅助函数。
- `coating_line_cases.json`：两个必须验证的工况。

当前名义控制器在模型失配和持续摩擦偏置下会留下稳态误差。你的目标是在它外层补上“分段泄漏积分 + 限幅”，并输出 `tension_retrofit_results.json`，证明两个工况下的张力尾段误差都被压到很小。

两个必做工况：

- `roll_change_step`：换卷后，第 2、3 段目标张力在 `t = 1.2 s` 发生阶跃。
- `friction_bias_hold`：目标张力恒定，但 4 个执行器存在持续摩擦偏置。

结果文件必须写到工作目录根部，文件名固定为 `tension_retrofit_results.json`，JSON 结构必须满足：

```json
{
  "controller_settings": {
    "integral_gain_by_section": [2.4, 2.4, 1.8, 1.8],
    "leak_by_section": [0.995, 0.995, 0.987, 0.987],
    "integral_limit_by_section": [16.0, 16.0, 10.0, 10.0],
    "torque_limit_by_section": [140.0, 140.0, 140.0, 140.0]
  },
  "cases": {
    "roll_change_step": {
      "baseline_tail_mean_abs_error": 0.70,
      "tail_mean_abs_error": 0.31,
      "tail_max_abs_error": 0.58,
      "peak_tension": 36.4,
      "peak_abs_torque": 134.2,
      "trace": [
        {
          "time": 0.02,
          "tensions": [22.1, 30.0, 28.0, 26.0],
          "reference_tensions": [22.0, 30.0, 28.0, 26.0],
          "torques": [98.3, 104.7, 110.8, 99.4],
          "integral_state": [0.0, 0.0, 0.0, 0.0]
        }
      ]
    },
    "friction_bias_hold": {
      "baseline_tail_mean_abs_error": 0.64,
      "tail_mean_abs_error": 0.28,
      "tail_max_abs_error": 0.46,
      "peak_tension": 32.4,
      "peak_abs_torque": 129.1,
      "trace": [
        {
          "time": 0.02,
          "tensions": [24.0, 32.0, 30.0, 28.0],
          "reference_tensions": [24.0, 32.0, 30.0, 28.0],
          "torques": [99.7, 106.2, 112.6, 101.8],
          "integral_state": [0.0, 0.0, 0.0, 0.0]
        }
      ]
    }
  }
}
```

具体要求：

- `controller_settings` 下 4 个数组都必须长度为 4，且体现“两段式”调参：前两段相同、后两段相同。
- verifier 会把你报告的 `controller_settings` 直接回放到环境里的名义预测控制器外层，按下面固定公式重建控制器，因此这些数组必须真实描述你用于生成结果的控制律：
  `tension_error = state[:4] - state_ref[:4]`
  `integral_state = clip(leak_by_section * integral_state - integral_gain_by_section * dt * tension_error, -integral_limit_by_section, integral_limit_by_section)`
  `torques = clip(nominal_torque + integral_state, -torque_limit_by_section, torque_limit_by_section)`
- `trace` 必须覆盖工况配置中的完整仿真时长，并且每个仿真步都记录 1 条数据；每条数据都必须包含 `time`、`tensions`、`reference_tensions`、`torques`、`integral_state`。
- `tail_mean_abs_error` 的定义：`trace` 最后 50 个采样点上，4 段张力绝对误差的整体平均值。
- `tail_max_abs_error` 的定义：`trace` 最后 50 个采样点上，4 段张力绝对误差的最大值。
- `baseline_tail_mean_abs_error` 的定义：用环境中提供的名义预测控制器、在同一工况上直接运行得到的 `tail_mean_abs_error`。
- `peak_tension` 的定义：该工况整个 `trace` 中出现过的最大张力值。
- `peak_abs_torque` 的定义：该工况整个 `trace` 中出现过的最大绝对扭矩值。

验收阈值也就是你需要达成的目标：

- 两个工况的 `tail_mean_abs_error` 都必须严格小于 `0.40`。
- 两个工况的 `tail_max_abs_error` 都必须严格小于 `0.70`。
- 两个工况都必须满足 `baseline_tail_mean_abs_error - tail_mean_abs_error >= 0.12`。
- 两个工况的 `peak_tension` 都必须严格小于 `40.0`。
- 两个工况的 `peak_abs_torque` 都必须不超过你自己在 `torque_limit_by_section` 中报告的最大值。

你可以自由编写脚本，只要最终产出满足上述契约即可。
