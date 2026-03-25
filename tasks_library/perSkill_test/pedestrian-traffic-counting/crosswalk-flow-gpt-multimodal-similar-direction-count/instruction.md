# 任务说明

在 `/app/crosswalk_sequences/` 下有 3 段路口监控短视频的离线抽帧结果。每个视频都对应一个目录，目录中的 PNG 文件已经按时间顺序命名；`/app/crosswalk_sequences/clip_index.json` 给出了视频 ID、帧目录和帧顺序。

你的目标是统计每个视频中 **完整通过斑马线** 的唯一行人数，并按两个方向分别汇总：

- `left_to_right`: 从画面左侧人行道出发，完整走到右侧人行道的人数。
- `right_to_left`: 从画面右侧人行道出发，完整走到左侧人行道的人数。

只统计真正完成整段穿越的人。下面这些情况都不要计入：

- 只在序列中途才出现、无法确认起点的人。
- 走到一半又返回原侧的人。
- 一直停留在同一侧或只是在边缘徘徊的人。
- 没有到达对侧人行道的人。

同一个人即使出现在多个帧里，也只能算 1 次。

请把结果写入 `/app/output/crosswalk_direction_counts.json`，并严格满足以下 JSON 结构：

```json
{
  "videos": [
    {
      "video_id": "canal_square",
      "left_to_right": 0,
      "right_to_left": 0
    },
    {
      "video_id": "market_turn",
      "left_to_right": 0,
      "right_to_left": 0
    },
    {
      "video_id": "station_lane",
      "left_to_right": 0,
      "right_to_left": 0
    }
  ]
}
```

额外要求：

- 顶层只能有 `videos` 这一个键。
- `videos` 必须是长度为 3 的数组，顺序固定为 `canal_square`、`market_turn`、`station_lane`。
- 每个对象只能包含 `video_id`、`left_to_right`、`right_to_left` 这 3 个键。
- 两个计数字段都必须是非负整数。
- 不要输出额外文件来替代这个 JSON。
