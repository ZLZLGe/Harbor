你在 `/root/data/well_drawdowns.tsv` 得到了一份 4 口观测井的 15 分钟粒度地下水位异常序列。文件是制表符分隔文本，列如下：

- `well_id`
- `timestamp_utc`
- `head_anomaly_m`

其中 `head_anomaly_m` 以米为单位，负值表示地下水位回落。规则抽水会表现为重复出现、近似箱形的短时负向事件。你的任务是找出最明显存在规则抽水回落的那口井，并输出它的重复间隔、中位回落深度和事件数量。

请按下面的固定规则分析：

1. 4 口井必须彼此独立分析，但使用完全一致的搜索配置。
2. 对每口井，都把 `timestamp_utc` 转成“距该井首个样本的 elapsed hours”。
3. 回落周期搜索范围固定为 `10` 到 `30` 小时。
4. 试探回落窗口时长固定为 `45` 到 `180` 分钟之间的等间隔网格，至少使用 `19` 个时长样本。
5. 使用 signal-to-noise power 读取每口井的最高峰，并取该峰对应的周期、窗口时长和参考时刻。
6. 用这组最优周期、窗口时长和参考时刻，在该井整段序列上标记所有回落窗口；相邻被标记的采样点合并为 1 个事件。
7. 每个事件的回落深度定义为该事件内 `abs(min(head_anomaly_m))`。
8. `median_drawdown_meters` 定义为全部事件回落深度的中位数。
9. `event_count` 定义为第 6 步得到的事件个数。
10. 从 4 口井中选择最高峰 power 最大的那一口井，作为最终答案。

将结果写入 `/root/output/pumping_drawdown_report.txt`。输出文件只能包含下面 5 行（允许最后一行后保留换行）：

```text
Aquifer Pumping Drawdown Report
well_id: <well_id>
drawdown_period_hours: <浮点数>
median_drawdown_meters: <浮点数>
event_count: <整数>
```

要求：

- `drawdown_period_hours` 和 `median_drawdown_meters` 都保留到小数点后 `5` 位。
- `event_count` 必须是十进制正整数。
- 不要输出额外说明、空行或其他字段。
