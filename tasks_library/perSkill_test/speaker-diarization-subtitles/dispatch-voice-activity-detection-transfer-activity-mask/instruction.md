处理 `/root/dispatch_recording.wav`，输出固定时间分辨率的人声活动掩码 `/root/speech_activity_mask.csv`，并额外写出整体占用统计 `/root/activity_summary.json`。

所有计算规则以 `/root/mask_policy.json` 为准：

- `bucket_size_seconds`：时间桶宽度。必须从 `0.000` 秒开始，按这个宽度连续切满整个时间轴。
- `timeline_duration_seconds`：完整时间轴长度。
- `speech_seconds_to_activate_bucket`：某个时间桶内累计人声时长达到这个阈值时，该桶记为活动。

要求：

- 录音中有人声、底噪、提示音和静音；只有人声算作活动，提示音、底噪、电流声或纯静音都不能单独算作活动。
- 逐桶判断 `[start, end)` 区间内是否应记为活动。
- 对每个时间桶：
  - 如果桶内累计人声时长大于等于 `speech_seconds_to_activate_bucket`，则 `speech_active = 1`。
  - 否则 `speech_active = 0`。
- 不要跳桶、合并桶，也不要输出额外桶。

`/root/speech_activity_mask.csv` 必须使用这个表头：

```csv
bucket_id,start,end,speech_active
bucket_001,0.000,0.500,1
bucket_002,0.500,1.000,0
```

补充约束：

- `bucket_id` 必须从 `bucket_001` 开始连续编号。
- 行必须按时间升序排列，且相邻两行的 `end` 与下一行的 `start` 要首尾相接。
- `start`、`end` 保留到 3 位小数。
- `speech_active` 只能是 `0` 或 `1`。
- 最后一行的 `end` 必须等于 `timeline_duration_seconds`。
- 验证时会基于录音内容按相同的分桶规则推导标准掩码；除结构检查外，你的 `speech_active` 结果还必须同时满足：
  - 相对参考掩码的 bucket `precision >= 0.95`
  - 相对参考掩码的 bucket `recall >= 0.95`
  - 与参考掩码不一致的 bucket 数量 `<= 1`
  - `speech_active = 1` 的 bucket 总数与参考答案最多相差 `1`

`/root/activity_summary.json` 必须是一个 JSON 对象，格式如下：

```json
{
  "source_file": "/root/dispatch_recording.wav",
  "policy_file": "/root/mask_policy.json",
  "bucket_size_seconds": 0.5,
  "timeline_duration_seconds": 18.0,
  "total_buckets": 36,
  "active_buckets": 21,
  "inactive_buckets": 15,
  "active_duration_seconds": 10.5,
  "active_ratio": 0.583
}
```

其中：

- `total_buckets` 是 CSV 数据行数。
- `active_buckets` 是 `speech_active = 1` 的桶数。
- `inactive_buckets = total_buckets - active_buckets`。
- `active_duration_seconds = active_buckets * bucket_size_seconds`。
- `active_ratio = active_buckets / total_buckets`，四舍五入后保留 3 位小数。
