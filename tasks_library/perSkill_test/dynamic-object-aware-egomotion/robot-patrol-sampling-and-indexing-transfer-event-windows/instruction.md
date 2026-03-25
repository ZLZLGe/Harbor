你会拿到一段机器人巡检视频和一份毫秒级事件日志。任务重点不是识别画面内容，而是把连续时间段稳定投影到离散的采样索引上。

输入资产：
- 视频：`/root/robot_patrol.mp4`
- 采样说明：`/root/patrol_manifest.json`
- 事件日志：`/root/robot_event_log.csv`

请以 `patrol_manifest.json` 中的字段为准：
- 第 `i` 个采样点的时间戳是 `t_i = sample_origin_ms + i * sample_period_ms`
- `i` 的范围是 `0` 到 `sample_count - 1`
- 事件日志中的每一行都表示一个半开时间段 `[start_ms, end_ms)`

请生成 `/root/event_windows.json`，要求如下：

1. 文件必须是一个 JSON 对象。
2. 每个键都必须是半开区间字符串 `start->end`，其中 `start` 和 `end` 是整数 sample index。
3. 每个值都必须是字符串数组，表示该区间内每个 sample index 上生效的事件集合。
4. 某个事件在 sample index `i` 上生效，当且仅当 `start_ms <= t_i < end_ms`。
5. 事件名必须直接使用 CSV 里的 `event` 列原文。
6. 如果某个 sample index 上没有任何事件，写成 `["clear"]`。
7. 每个数组必须去重并按字典序排序；如果数组里出现 `clear`，它必须单独出现。
8. 所有区间必须严格按时间顺序、无重叠、无空洞地完整覆盖 `[0, sample_count)`。
9. 把所有相邻且事件数组完全相同的区间合并，不要把同一事件集合拆成多个连续片段。

评测会根据 `patrol_manifest.json` 和 `robot_event_log.csv` 重算采样后的事件集合，并检查你的事件窗口是否完全一致。
