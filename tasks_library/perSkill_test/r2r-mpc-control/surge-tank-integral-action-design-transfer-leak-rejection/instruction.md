你接手的是一个缓冲罐液位改造任务。环境已经给出：

- `surge_tank_env.py`：离散液位过程仿真器、模型/工况读取逻辑，以及指标与整点采样汇总函数。
- `tank_controller_scaffold.py`：现成的名义阀门预测控制器，以及把液位误差积分补偿接到阀门命令上的评估入口。
- `tank_model.yaml`：名义离散模型、采样周期、阀门物理上限和验收带宽。
- `tank_cases.csv`：两个必须通过的泄漏工况。

你不需要重写求解器。本题只要求你在现有阀门控制回路外层加入“液位误差积分补偿 + 简单限幅”，并把结果写成工作目录根部的 `level_offset_report.yaml`。

必须覆盖的两个工况：

- `blend_recipe_step`：液位目标在 `2.5 min` 切换到更高设定，后半程计划出料偏差加重，同时罐体存在持续泄漏。
- `truck_fill_recovery`：装车缓冲工况中液位目标在 `3.2 min` 切换，后半程计划出料偏差变化，系统同样存在持续泄漏。

结果文件名固定为 `level_offset_report.yaml`，YAML 结构必须满足：

```yaml
controller_settings:
  integral_gain_pct_per_m: 50.0
  integral_leak: 0.995
  integral_limit_pct: 18.0
  valve_max_pct: 88.0
cases:
  blend_recipe_step:
    baseline_tail_mean_abs_level_error_m: 0.310470
    tail_mean_abs_level_error_m: 0.015556
    tail_max_abs_level_error_m: 0.021332
    recovery_time_min: 5.1
    peak_overshoot_m: 0.030339
    peak_valve_pct: 25.398398
    checkpoints:
      - minute: 1.0
        level_m: 1.371681
        target_level_m: 1.42
        valve_pct: 10.667104
        integral_state_pct: 2.491554
  truck_fill_recovery:
    baseline_tail_mean_abs_level_error_m: 0.318053
    tail_mean_abs_level_error_m: 0.014032
    tail_max_abs_level_error_m: 0.026511
    recovery_time_min: 5.5
    peak_overshoot_m: 0.031429
    peak_valve_pct: 24.832888
    checkpoints:
      - minute: 1.0
        level_m: 1.437145
        target_level_m: 1.48
        valve_pct: 10.818182
        integral_state_pct: 2.202240
```

具体要求：

- `controller_settings` 下 4 个字段都必须存在，且都必须是数值标量。
- `integral_gain_pct_per_m` 必须严格大于 `0`。
- `integral_leak` 必须满足 `0 < integral_leak <= 1`。
- `integral_limit_pct` 必须严格大于 `0`。
- `valve_max_pct` 必须满足 `0 < valve_max_pct <= tank_model.yaml` 中的物理阀门上限。
- `cases` 下必须且只能包含 `blend_recipe_step` 与 `truck_fill_recovery`。
- 每个工况都必须报告 6 个标量指标和 `checkpoints`。
- `checkpoints` 必须按时间升序给出完整的整点采样：从 `1.0 min` 开始，每隔 `1.0 min` 记录一次，直到 `10.0 min` 结束，共 10 条。
- 每条 checkpoint 都必须包含 `minute`、`level_m`、`target_level_m`、`valve_pct`、`integral_state_pct`。

指标定义如下：

- `tail_mean_abs_level_error_m`：最后 `15` 个采样点上，`|level_m - target_level_m|` 的平均值。
- `tail_max_abs_level_error_m`：最后 `15` 个采样点上，`|level_m - target_level_m|` 的最大值。
- `baseline_tail_mean_abs_level_error_m`：在同一工况上，不加外层积分补偿、只运行环境自带名义阀门控制器时得到的 `tail_mean_abs_level_error_m`。
- `recovery_time_min`：从设定点切换开始，到之后始终保持在 `tank_model.yaml` 中 `recovery_band_m` 带宽内所需的时间。
- `peak_overshoot_m`：设定点切换之后，`level_m - 最终目标液位` 的最大正值；若始终未高于最终目标，则记为 `0`。
- `peak_valve_pct`：该工况全过程中出现过的最大阀门开度命令。

验收目标：

- 两个工况的 `tail_mean_abs_level_error_m` 都必须严格小于 `0.020`。
- 两个工况的 `tail_max_abs_level_error_m` 都必须严格小于 `0.030`。
- 两个工况都必须满足 `baseline_tail_mean_abs_level_error_m - tail_mean_abs_level_error_m >= 0.240`。
- 两个工况的 `recovery_time_min` 都必须小于等于 `5.6`。
- 两个工况的 `peak_overshoot_m` 都必须严格小于 `0.040`。
- 两个工况的 `peak_valve_pct` 都必须不超过你自己在 `valve_max_pct` 中报告的值。

评测时会读取你报告的 `controller_settings`，带回环境中的仿真器重新运行两个工况，并复算指标与 10 个整点 checkpoint。

为了本地验证，环境里已经提供：

- `run_case(case_id, controller_settings)`：运行单个工况，返回逐采样轨迹、指标摘要和整点 checkpoint。
- `run_baseline_case(case_id)`：返回指定工况下不加积分补偿时的基线表现。
- `evaluate_report(report)`：一次性复算整个 `level_offset_report.yaml` 的报告内容。

你可以自由编写脚本，只要最终输出契约和可观察结果满足上述要求即可。
