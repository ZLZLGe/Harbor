你需要在 `/root` 下创建 `tugger_convoy_sim.py`，并运行它生成 `/root/tugger_gap_log.csv`。

可用输入只有：

- `/root/warehouse_tugger_config.yaml`

任务要求如下。

1. 读取 `warehouse_tugger_config.yaml` 中的仿真参数、控制参数和前车分段速度轨迹。
2. 按 `simulation.dt` 从 `t=0.0` 仿真到 `simulation.duration`，包含终点时刻。
3. 自车牵引车使用单自由度纵向离散模型，并严格按下面顺序更新：
   - 先在当前时刻 `t` 计算前车状态、车距、目标间距、TTC、模式和 `accel_cmd`
   - 记录当前时刻这一行输出
   - 再执行半隐式 Euler 更新：`v_next = max(0, v + accel_cmd * dt)`，`x_next = x + v_next * dt`
4. 前车轨迹使用 `lead_segments` 定义：
   - 如果当前时刻不在任何 segment 内，则当前无前车
   - 如果某个 segment 在当前时刻开始，则该时刻前车绝对位置应被重置为 `ego_position + start_gap`
   - `speed_points` 之间的前车速度用线性插值
   - segment 内前车位置必须由 `speed_points` 的分段线性速度曲线做梯形积分得到，不要用旧车距直接递推
5. 模式判定必须严格使用下面规则：
   - `target_gap = ego_speed * time_headway + min_gap`
   - 若无前车，模式是 `cruise`
   - 若有前车且 `gap < min_gap`，模式是 `emergency`
   - 否则若 `relative_speed = ego_speed - lead_speed > 0` 且 `ttc = gap / relative_speed < ttc_threshold`，模式是 `emergency`
   - 其他有前车情况使用 `follow`
6. 控制律必须严格使用下面公式，并做饱和裁剪：
   - `cruise`: `accel_cmd = clamp(k_cruise * (target_speed - ego_speed), max_decel, max_accel)`
   - `follow`: `accel_cmd = clamp(k_gap * (gap - target_gap) + k_rel * (lead_speed - ego_speed), max_decel, max_accel)`
   - `emergency`: `accel_cmd = max_decel`
7. TTC 只在“有前车且 `relative_speed > 0` 且 `gap > 0`”时填写数值，否则留空。
8. 输出文件必须严格命名为 `tugger_gap_log.csv`，列顺序固定为：

```text
time,ego_speed,ego_position,lead_present,lead_speed,lead_position,gap,target_gap,ttc,mode,accel_cmd
```

9. 输出格式必须严格遵守：
   - `lead_present` 只能写 `0` 或 `1`
   - 所有其他数值列都保留 3 位小数
   - 无前车时，`lead_speed`、`lead_position`、`gap`、`ttc` 这 4 列写空字符串
   - `mode` 只能是 `cruise`、`follow`、`emergency`

你最终只需要交付：

- `/root/tugger_convoy_sim.py`
- `/root/tugger_gap_log.csv`
