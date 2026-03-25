你在 `/root/data/api_success_rates.jsonl` 得到了一段单个 API 网关的 5 分钟粒度可靠性观测。文件是 JSON Lines 格式，每行都包含：

- `timestamp_utc`
- `success_rate`
- `request_count`

其中 `success_rate` 已经是归一化后的成功率，正常时通常接近 `1.0`；重复维护窗口会表现为短时、接近箱形的明显下挫。你的任务是从整条序列中恢复维护窗口的重复间隔、窗口宽度，并给出下一次窗口开始时间的预测。

请按下面的固定规则分析：

1. 只使用 `success_rate` 序列进行重复短窗搜索。
2. 重复间隔搜索范围固定为 `12` 到 `30` 小时。
3. 试探窗口宽度固定为 `20` 到 `80` 分钟之间的等间隔网格，至少使用 `31` 个宽度样本。
4. 读取最高功率峰对应的重复间隔和窗口宽度。
5. 将该峰对应的窗口中心时刻减去半个窗口宽度，得到单个维护窗口的起始时刻。
6. `first_window_start_utc` 定义为观测区间内最早一个维护窗口起始时间。
7. `next_window_start_utc` 定义为 `first_window_start_utc` 加上 `recurrence_hours`。

将结果写入 `/root/output/maintenance_window_forecast.md`。为了便于自动读取，输出文件只包含下面 5 行（允许最后一行后面保留换行）：

```md
# API Maintenance Window Forecast
- recurrence_hours: <浮点数>
- window_minutes: <浮点数>
- first_window_start_utc: <UTC 时间戳>
- next_window_start_utc: <UTC 时间戳>
```

要求：

- `recurrence_hours` 和 `window_minutes` 都使用十进制数，并保留到小数点后 `5` 位。
- 两个时间戳都必须使用 UTC，格式固定为 `YYYY-MM-DDTHH:MM:SSZ`。
- `next_window_start_utc` 必须晚于 `first_window_start_utc`。
