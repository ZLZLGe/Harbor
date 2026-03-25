# 任务说明

`/app/input/clip_manifest.json` 描述了 2 段仓库监控片段。每段片段都已经按时间顺序离线抽帧到一个目录中，`fps` 固定为 `1`，也就是 **每张帧图代表原视频中的 1 秒**。

`/app/input/zone_reference.json` 给出了仓库里的警戒区域 `Z1`、`Z2`、`Z3` 的编号和位置说明；这些区域也直接画在帧图里。

你的任务是检查每段片段，找出 **叉车与行人同时进入同一警戒区域，并以肉眼可见的极小间距近距离交汇、但没有发生碰撞** 的近险事件，然后把结果写入 `/app/output/near_miss_timeline.json`。

判定和合并规则：

- 只有叉车和行人 **同时** 出现在同一个警戒区域里时，才可能构成事件。
- 只是同区但相距明显较远，不算近险事件。
- 同一段连续秒数里，如果近险对象没有脱离该警戒区，就要合并成 **一个** 事件时间段。
- 一旦人物和车辆拉开距离，或者离开该警戒区，之后再次接近时要记为新的事件。

输出 JSON 必须严格满足下面的结构。下面的示例只演示字段形状，不代表本题的正确答案：

```json
{
  "videos": [
    {
      "video_id": "dock_lane_a",
      "event_count": 1,
      "events": [
        {
          "event_index": 1,
          "zone_id": "Z2",
          "start_time": "00:02",
          "end_time": "00:03"
        }
      ]
    },
    {
      "video_id": "packing_hall_b",
      "event_count": 1,
      "events": [
        {
          "event_index": 1,
          "zone_id": "Z3",
          "start_time": "00:04",
          "end_time": "00:05"
        }
      ]
    }
  ]
}
```

输出要求：

- 顶层只能有 `videos` 这一个键。
- `videos` 必须是长度为 2 的数组，顺序必须与 `clip_manifest.json` 一致，也就是 `dock_lane_a` 在前，`packing_hall_b` 在后。
- 每个视频对象只能包含 `video_id`、`event_count`、`events` 这 3 个键。
- `event_count` 必须等于该视频 `events` 数组的长度。
- 每个事件对象只能包含 `event_index`、`zone_id`、`start_time`、`end_time` 这 4 个键。
- `event_index` 必须从 1 开始按顺序递增。
- `zone_id` 只能是 `Z1`、`Z2`、`Z3` 之一。
- `start_time` 和 `end_time` 都必须使用零填充的 `MM:SS` 格式；由于每张图代表 1 秒，所以时间应与帧序号对齐。
- 不要输出额外文件，也不要在 JSON 中加入额外字段。
