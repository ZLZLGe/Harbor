你在处理一台双区工业烘箱的温控改造。环境已经给出：

- `heater_model.json`：名义离散状态空间模型、有限时域跟踪器参数和加热功率上限。
- `thermal_oven_env.py`：真实热仿真器与工况配置读取逻辑，真实对象包含环境散热偏差。
- `heater_controller_scaffold.py`：现成的名义控制器，以及把积分补偿接到加热功率通道上的评估入口。
- `oven_cases.json`：两个必须通过的工况。

你不需要重写预测控制器。本题只要求你为两路加热功率设计“泄漏积分 + 限幅”参数，并把结果写成工作目录根部的 `heater_integrator_config.json`。

必须覆盖的两个工况：

- `load_swap_recovery`：产品负载在仿真中途切换，两个温区都要重新消除静差。
- `ambient_bias_hold`：回风系统偏冷且后半程额外散热加重，需要在持续偏差下保持稳态跟踪。

结果文件名固定为 `heater_integrator_config.json`，JSON 结构必须满足。下面的数值只用于说明字段和数组形状，通常不能直接通过评测：

```json
{
  "integral_gain_by_zone": [0.05, 0.05],
  "leak_by_zone": [0.95, 0.95],
  "integral_limit_by_zone": [0.25, 0.25]
}
```

具体要求：

- 顶层 JSON 键必须且只能是 `integral_gain_by_zone`、`leak_by_zone`、`integral_limit_by_zone` 这 3 个字段，不能出现其他顶层字段。
- 这 3 个字段都必须是长度为 2 的数值数组，分别对应 1 区和 2 区。
- `integral_gain_by_zone` 的两个值都必须严格大于 0。
- `leak_by_zone` 的两个值都必须满足 `0 < leak <= 1`。
- `integral_limit_by_zone` 的两个值都必须严格大于 0。
- 评测时会使用 `heater_controller_scaffold.py` 中提供的名义跟踪器，把你的参数作为外层积分补偿：
  - 每一步先根据当前温度误差更新积分状态。
  - 积分状态按你提供的 `integral_limit_by_zone` 做对称裁剪。
  - 裁剪后的积分项会直接叠加到名义加热功率上，再按模型中的 `heater_power_limit_kw` 做功率饱和。

性能指标都由评测器根据仿真轨迹复算，定义如下：

- `tail_mean_abs_error`：轨迹最后 30 个采样点上，两区温度绝对误差的整体平均值。
- `tail_max_abs_error`：轨迹最后 30 个采样点上，两区温度绝对误差的最大值。
- `baseline_tail_mean_abs_error`：在同一工况上，不加外层积分补偿、只运行环境自带名义控制器时得到的 `tail_mean_abs_error`。
- `peak_temperature_c`：整个工况期间出现过的最高温度。
- `peak_heater_power_kw`：整个工况期间出现过的最大加热功率绝对值。

验收目标：

- 两个工况的 `tail_mean_abs_error` 都必须严格小于 `0.15`。
- 两个工况的 `tail_max_abs_error` 都必须严格小于 `0.23`。
- 两个工况都必须满足 `baseline_tail_mean_abs_error - tail_mean_abs_error >= 0.12`。
- 两个工况的 `peak_temperature_c` 都必须严格小于 `176.0`。
- 两个工况的 `peak_heater_power_kw` 都必须不超过 `heater_model.json` 中声明的最大加热功率上限。

你可以自由编写脚本。为了本地验证，环境里已经提供：

- `evaluate_config(config)`：一次性跑完两个工况并返回结果摘要。
- `run_baseline_case(case_id)`：返回指定工况下不加积分补偿的基线表现。

只要最终输出契约和可观察结果满足上述要求即可。
