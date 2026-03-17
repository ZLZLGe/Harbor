你需要在 `/root` 下创建 `escort_simulation.py`，并运行它生成 `/root/apron_escort_timeline.csv`。

可用输入只有：

- `/root/apron_escort_config.yaml`

任务要求如下。

1. 读取 `apron_escort_config.yaml` 中的仿真参数、护航控制参数和前车分段轨迹。
2. 从 `t=0.0` 按 `simulation.dt` 仿真到 `simulation.duration`，包含终点时刻。
3. 自车使用单自由度纵向离散模型，并严格按下面顺序更新：
   - 在当前时刻 `t` 先确定所在区段、前车状态、间距、`safe_gap`、`ttc`、模式和 `accel_cmd`
   - 记录当前时刻这一行输出
   - 再执行半隐式 Euler 更新：`v_next = max(0, v + accel_cmd * dt)`，`x_next = x + v_next * dt`
4. 前车轨迹必须由 `lead_vehicle.segments` 生成：
   - 每个采样时刻都恰好落在一个 active segment 内
   - `speed_profile` 之间的速度使用线性插值
   - 前车绝对位置不能由上一时刻间距递推，必须使用下面方式计算：
     - 从 `lead_vehicle.initial_gap` 作为 `t=0` 时前车绝对位置起点
     - 先累加所有已结束 segment 的路程
     - 再对当前 segment 从 `segment.start` 到当前时刻做梯形积分
5. 护航判定必须严格使用下面规则：
   - `safe_gap = min_gap + time_headway * ego_speed`
   - `relative_speed = ego_speed - lead_speed`
   - 只有在 `relative_speed > 0` 且 `gap > 0` 时才计算 `ttc = gap / relative_speed`，否则 `ttc` 留空
   - 如果 `gap < min_gap`，模式是 `emergency`
   - 否则如果 `ttc` 有值且 `ttc < ttc_threshold`，模式是 `emergency`
   - 否则如果 `gap <= safe_gap + release_gap`，模式是 `escort`
   - 其他情况使用 `approach`
6. 控制律必须严格使用下面公式，并做饱和裁剪：
   - `approach`: `target_speed = min(control.target_speed, active_segment.speed_limit)`
   - `approach`: `accel_cmd = clamp(approach_gain * (target_speed - ego_speed), max_decel, max_accel)`
   - `escort`: `accel_cmd = clamp(gap_gain * (gap - safe_gap) + relative_gain * (lead_speed - ego_speed), max_decel, max_accel)`
   - `emergency`: `accel_cmd = max_decel`
7. 输出文件必须严格命名为 `apron_escort_timeline.csv`，列顺序固定为：

```text
time,zone,speed_limit,lead_speed,lead_position,ego_speed,ego_position,gap,safe_gap,ttc,mode,accel_cmd
```

8. 输出格式必须严格遵守：
   - `time` 和所有数值列都保留 3 位小数
   - 只有 `ttc` 允许留空
   - `mode` 只能是 `approach`、`escort`、`emergency`
   - `zone` 必须直接写 active segment 的 `zone` 字符串
9. 不要修改输入文件内容。

你最终只需要交付：

- `/root/escort_simulation.py`
- `/root/apron_escort_timeline.csv`
