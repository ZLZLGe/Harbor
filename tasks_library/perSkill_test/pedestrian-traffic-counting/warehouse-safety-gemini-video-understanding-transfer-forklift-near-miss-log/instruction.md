## 任务说明

`/app/input/clips/` 下有两段俯视仓库监控片段，`/app/input/near_miss_policy.json` 给出了事件判定口径和允许使用的事件摘要文案。

请逐个阅读这些片段，只记录满足阈值的叉车-行人近距离险情事件，并将结果写入 `/app/output/near_miss_events.json`。

记录规则：
- 只记录“移动中的叉车”和“步行中的行人”之间的险情。
- 只有当双方在同一开放作业通道内以小于一个行人身宽的最近间距擦身而过，且画面能看出急停、犹豫或闪避时，才算一次险情。
- 如果同一次接近过程连续出现在多个相邻帧里，只记录一次。
- 不要记录安全间距明显更大的会车。
- 不要记录被固定隔离带、货架线或墙体分隔开的互动。
- `actors` 中必须先写叉车 ID，再写行人 ID。
- `summary` 必须直接使用 `/app/input/near_miss_policy.json` 里 `summary_codes` 提供的完整英文短句之一。
- `timestamp` 使用 `MM:SS` 零填充格式；对一次连续险情，取“最近间距已经清晰可见”的第一个整秒。

输出 JSON 必须满足以下要求：
- 顶层只能包含一个字段：`events`。
- `events` 必须是数组，并且按 `filename` 升序排列；同一视频内再按 `timestamp` 升序排列。
- 每个事件对象只能包含四个字段：`filename`、`timestamp`、`actors`、`summary`。
- `filename` 必须与 `/app/input/clips/` 中的源文件名完全一致。
- `timestamp` 必须是 `MM:SS` 格式的字符串。
- `actors` 必须是长度为 2 的字符串数组，顺序固定为 `[forklift_id, pedestrian_id]`。
- `summary` 必须是非空字符串，且必须逐字匹配策略文件中给出的某一条摘要短句。

期望输出示例：

```json
{
  "events": [
    {
      "filename": "example.avi",
      "timestamp": "00:07",
      "actors": ["F1", "P2"],
      "summary": "forklift cut across the pedestrian crossing path at close range"
    }
  ]
}
```

不要生成额外文件，也不要在最终 JSON 中添加额外字段。
