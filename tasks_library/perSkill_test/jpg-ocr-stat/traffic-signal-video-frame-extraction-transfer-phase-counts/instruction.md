## 任务

`/app/workspace/traffic_videos` 下面有 3 段合成路口监控视频，`/app/workspace/traffic_signal_config.json` 给出了：

- 固定抽帧间隔（单位：秒）
- 每个视频里需要统计的信号灯方向
- 每个方向信号灯在画面中的矩形区域坐标 `[x1, y1, x2, y2]`

请从每段视频的 `0` 秒开始，严格按配置中的固定时间间隔抽取代表帧，并完成以下两件事：

- 对每段视频，先读取该视频的实际 FPS，并计算 `interval_frame_count = round(FPS * sample_interval_seconds)`。
- 只保留原视频中序号为 `0`、`interval_frame_count`、`2 * interval_frame_count`、`3 * interval_frame_count` ... 且仍然存在的那些原始帧。
- 每张导出的 JPG 必须对应上述某一张被保留的原始视频帧内容，不能用占位图、重绘图或重新合成的画面代替。

1. 将每段视频抽到的帧按时间顺序保存到 `/app/workspace/sampled_frames/<video_stem>/frame_<index>.jpg`。
   - `<index>` 从 `000` 开始递增。
   - 每个视频目录里只能放该视频抽出的帧。
2. 统计这些抽样帧中，每个方向信号灯处于 `red`、`yellow`、`green` 三种状态的出现次数，并写入 `/app/workspace/traffic_phase_counts.json`。

输出 JSON 必须满足以下结构：

```json
{
  "sample_interval_seconds": 2,
  "videos": [
    {
      "video_file": "junction_cedar.avi",
      "sampled_frames_dir": "sampled_frames/junction_cedar",
      "sampled_frame_count": 6,
      "phase_counts": {
        "northbound": {
          "red": 3,
          "yellow": 1,
          "green": 2
        },
        "eastbound": {
          "red": 2,
          "yellow": 2,
          "green": 2
        }
      }
    }
  ]
}
```

要求：

- 顶层只能包含 `sample_interval_seconds` 和 `videos` 两个字段。
- `videos` 必须按 `video_file` 升序排列。
- 每个视频对象只能包含 `video_file`、`sampled_frames_dir`、`sampled_frame_count`、`phase_counts` 这 4 个字段。
- `sampled_frames_dir` 必须写相对路径，格式固定为 `sampled_frames/<video_stem>`。
- `sampled_frame_count` 必须等于该视频实际导出的抽样帧数量。
- `phase_counts` 中只保留配置里给出的方向；每个方向下只保留 `red`、`yellow`、`green` 三个键。
- 统计对象是“抽样后的帧”，不是视频里的全部原始帧。
- 不要输出额外字段。
