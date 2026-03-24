你需要在 `/root` 下创建 `tram_platform_sim.py`，并运行它生成：

- `/root/tram_block_trace.csv`
- `/root/tram_block_summary.yaml`

可用输入只有：

- `/root/tram_block_config.yaml`

任务要求如下。

1. 读取 `tram_block_config.yaml` 中的仿真参数、控制参数和前车占用区段。
2. 按 `simulation.dt` 从 `t=0.0` 仿真到 `simulation.duration`，包含终点时刻。
3. 自车列车使用单自由度纵向离散模型，并严格按下面顺序更新：
   - 先在当前时刻 `t` 计算前车状态、保护间距、TTC、模式和 `accel_cmd`
   - 记录当前时刻这一行输出
   - 再执行半隐式 Euler 更新：`v_next = max(0, v + accel_cmd * dt)`，`x_next = x + v_next * dt`
4. 前车占用轨迹使用 `lead_segments` 定义：
   - 如果当前时刻不在任何 segment 内，则当前无前车
   - 如果某个 segment 在当前时刻开始，则该时刻前车绝对位置应被重置为 `ego_position + start_gap`
   - `speed_points` 之间的前车速度使用线性插值
   - segment 内前车位置必须由 `speed_points` 的分段线性速度曲线做梯形积分得到，不要用旧间距直接递推
5. 模式判定必须严格使用下面规则：
   - `protect_gap = min_gap + time_headway * ego_speed`
   - 若无前车，模式是 `run`
   - 若有前车且 `gap < min_gap`，模式是 `emergency`
   - 否则若 `relative_speed = ego_speed - lead_speed > 0` 且 `ttc = gap / relative_speed < ttc_threshold`，模式是 `emergency`
   - 其他有前车情况使用 `spacing`
6. 控制律必须严格使用下面公式，并做饱和裁剪：
   - `run`: `accel_cmd = clamp(k_run * (target_speed - ego_speed), max_decel, max_accel)`
   - `spacing`: `accel_cmd = clamp(k_gap * (gap - protect_gap) + k_rel * (lead_speed - ego_speed), max_decel, max_accel)`
   - `emergency`: `accel_cmd = max_decel`
7. TTC 只在“有前车且 `relative_speed > 0` 且 `gap > 0`”时填写数值，否则留空。
8. 输出文件 `tram_block_trace.csv` 必须严格命名，列顺序固定为：

```text
time,segment,ego_speed,ego_position,lead_present,lead_speed,lead_position,gap,protect_gap,ttc,mode,accel_cmd
```

9. `tram_block_trace.csv` 的输出格式必须严格遵守：
   - `lead_present` 只能写 `0` 或 `1`
   - `time` 和所有数值列都保留 3 位小数
   - 无前车时，`segment`、`lead_speed`、`lead_position`、`gap`、`ttc` 这 5 列写空字符串
   - `mode` 只能是 `run`、`spacing`、`emergency`
10. 你还需要根据生成的轨迹汇总 `tram_block_summary.yaml`，结构必须严格为：

```yaml
scenario:
  duration: <float>
  dt: <float>
  target_speed: <float>
  lead_segments: <int>
events:
  first_spacing_time: <float or null>
  first_emergency_time: <float or null>
  return_to_run_time: <float or null>
metrics:
  min_gap: <float>
  min_ttc: <float or null>
  min_margin: <float>
  mode_samples:
    run: <int>
    spacing: <int>
    emergency: <int>
  final_speed: <float>
  final_position: <float>
checks:
  hard_floor_ok: <bool>
  emergency_observed: <bool>
  recovered_to_run: <bool>
  all_modes_observed: <bool>
  summary_ready: <bool>
```

11. `tram_block_summary.yaml` 中各字段按下面规则计算：
   - 所有浮点数值都写成数值并四舍五入到 3 位小数
   - `min_gap` 是所有有前车时刻里 `gap` 的最小值
   - `min_ttc` 是所有非空 `ttc` 的最小值；如果整段仿真都没有有效 `ttc`，则写 `null`
   - `min_margin` 是所有有前车时刻里 `gap - protect_gap` 的最小值
   - `first_spacing_time` 是第一次进入 `spacing` 的时刻，没有则写 `null`
   - `first_emergency_time` 是第一次进入 `emergency` 的时刻，没有则写 `null`
   - `return_to_run_time` 是第一次进入 `emergency` 之后再次回到 `run` 的时刻，没有则写 `null`
   - `mode_samples` 是 3 个模式在轨迹中的采样点个数
   - `hard_floor_ok` 的判定条件是 `min_gap >= summary_rules.hard_floor_gap`
   - `emergency_observed` 表示至少出现过一次 `emergency`
   - `recovered_to_run` 表示 `return_to_run_time` 非空
   - `all_modes_observed` 表示 `run`、`spacing`、`emergency` 三种模式都至少出现一次
   - `summary_ready` 表示前面 4 个检查项都为真
12. 不要修改输入文件内容。

你最终只需要交付：

- `/root/tram_platform_sim.py`
- `/root/tram_block_trace.csv`
- `/root/tram_block_summary.yaml`
